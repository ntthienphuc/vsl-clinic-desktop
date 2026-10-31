"""CPU Pose Lite + Hands detector; one timestamp, two independent task graphs.

The recognizer consumes image x/y/confidence, not world coordinates. Hand identity
is assigned against pose wrists in the unmirrored image, never a preview label.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class LandmarkDetector:
    def __init__(self, assets: Path):
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clinic-landmark")
        self.pose = None
        self.hands = None
        self.last_timestamp = -1
        try:
            self.pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(assets / "models/pose_landmarker_lite.task")),
                running_mode=vision.RunningMode.VIDEO,
                min_pose_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ))
            self.hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(assets / "models/hand_landmarker.task")),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=0.45,
                min_tracking_confidence=0.5,
            ))
        except Exception:
            self.close()
            raise

    def process(self, bgr: np.ndarray, timestamp_ms: float):
        timestamp = max(self.last_timestamp + 1, int(round(timestamp_ms)))
        self.last_timestamp = timestamp
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        pose_future = self.pool.submit(self.pose.detect_for_video, image, timestamp)
        hand_future = self.pool.submit(self.hands.detect_for_video, image, timestamp)
        pose = pose_future.result()
        hands = hand_future.result()
        result = SimpleNamespace(pose_landmarks=None, left_hand_landmarks=None, right_hand_landmarks=None)
        if not pose.pose_landmarks:
            return result
        points = pose.pose_landmarks[0]
        result.pose_landmarks = SimpleNamespace(landmark=points)
        height, width = bgr.shape[:2]
        candidates = []
        for hand_index, landmarks in enumerate(hands.hand_landmarks):
            wrist = landmarks[0]
            for side, pose_index in enumerate((15, 16)):
                target = points[pose_index]
                if target.visibility < 0.3:
                    continue
                distance = np.hypot(wrist.x - target.x, (wrist.y - target.y) * height / width)
                candidates.append((distance, side, hand_index))
        used_sides = set()
        used_hands = set()
        for distance, side, hand_index in sorted(candidates):
            if distance > 0.18 or side in used_sides or hand_index in used_hands:
                continue
            used_sides.add(side)
            used_hands.add(hand_index)
            component = SimpleNamespace(landmark=hands.hand_landmarks[hand_index])
            setattr(result, "left_hand_landmarks" if side == 0 else "right_hand_landmarks", component)
        return result

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        if self.hands is not None:
            self.hands.close()
        if self.pose is not None:
            self.pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
