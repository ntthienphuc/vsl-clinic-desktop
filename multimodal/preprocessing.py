"""RAM-only streaming implementation of the pinned source Processor contract.

The original math functions and boundary module are imported byte-for-byte.
Frames are BGR from one OpenCV owner, never mirrored or JPEG preview images.
Snapshots share immutable gray frames; pruning does not invalidate inference.
"""
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

import cv2
import mediapipe as mp
import numpy as np

# runtime.load_contract must install the verified asset path first.
from server.preprocess import canonical_square, crops_from_gray
from server.vendor.crop_geometry import filter_points
from .landmarks import PoseHands, FacePoints

MAX_RETAINED_FRAMES = 270
RETENTION_MS = 10400


@dataclass(frozen=True)
class Frame:
    frame_id: int
    capture_ms: float
    captured_monotonic_ms: float
    pose: np.ndarray
    points: np.ndarray | None
    gray: np.ndarray
    faces: int
    preprocess_ms: float
    source_width: int
    source_height: int
    face_ms: float = 0.
    pose_hands_ms: float = 0.

    def meta(self):
        return dict(frame_id=self.frame_id, capture_ms=self.capture_ms,
                    captured_monotonic_ms=self.captured_monotonic_ms,
                    faces=self.faces, preprocess_ms=self.preprocess_ms)


class MemoryProcessor:
    def __init__(self, root):
        cv2.setNumThreads(1)
        self.reference = np.load(root / "models/assets/mean_face.npy")
        self.face = FacePoints()
        self.holistic = PoseHands()
        self.face_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clinic-face")
        self.frames = []
        self.closed = False

    def append(self, bgr, frame_id, capture_ms, captured_monotonic_ms=None):
        if self.closed:
            raise ValueError("processor_closed")
        if self.frames and (frame_id <= self.frames[-1].frame_id or capture_ms <= self.frames[-1].capture_ms):
            raise ValueError("out_of_order_frame")
        if not np.isfinite(capture_ms):
            raise ValueError("invalid_capture_time")
        started = time.perf_counter()
        h, w = bgr.shape[:2]
        rgb = canonical_square(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        # Independent graphs see exactly the same immutable RGB frame. Join
        # both before advancing either tracker to the next timestamp.
        face_pending = self.face_executor.submit(self._face, rgb)
        pose_started = time.perf_counter()
        try:
            result = self.holistic.process(rgb)
        except BaseException:
            face_pending.result()
            raise
        pose_ms = (time.perf_counter() - pose_started) * 1000
        detections, face_ms = face_pending.result()
        points = (np.array([[p.x * 1080, p.y * 1080]
                           for p in detections[0].location_data.relative_keypoints[:4]], np.float32)
                  if len(detections) == 1 else None)
        pose = np.zeros((75, 4), np.float32)
        for field, a, b in [("pose_landmarks", 0, 33), ("left_hand_landmarks", 33, 54),
                            ("right_hand_landmarks", 54, 75)]:
            group = getattr(result, field)
            if group:
                pose[a:b] = [[v.x, v.y, v.z, v.visibility if field == "pose_landmarks" else 1.]
                             for v in group.landmark]
        frame = Frame(frame_id, float(capture_ms),
                      captured_monotonic_ms if captured_monotonic_ms is not None else started * 1000,
                      pose, points, gray, len(detections), (time.perf_counter() - started) * 1000, w, h, face_ms, pose_ms)
        self.frames.append(frame)
        return frame

    def _face(self, rgb):
        started = time.perf_counter()
        detections = self.face.process(rgb).detections or []
        return detections, (time.perf_counter() - started) * 1000

    def prune(self, capture_ms):
        # No stream duration limit, while the active word fits the original 8s gate.
        self.frames = [f for f in self.frames if f.capture_ms >= capture_ms - RETENTION_MS][-MAX_RETAINED_FRAMES:]

    def snapshot(self, selected_frame_ids):
        selected = set(selected_frame_ids)
        return PreparedSegment(tuple(f for f in self.frames if f.frame_id in selected), self.reference)

    def close(self):
        if not self.closed:
            self.closed = True
            self.face_executor.shutdown(wait=True)
            self.face.close()
            self.holistic.close()
            self.frames.clear()


@dataclass(frozen=True)
class PreparedSegment:
    frames: tuple[Frame, ...]
    reference: np.ndarray

    def finish(self, resample=True):
        if len(self.frames) < 6:
            raise ValueError("insufficient_frames")
        start = time.perf_counter()
        times = np.array([f.capture_ms for f in self.frames])
        targets = np.arange(times[0], times[-1] + .01, 40.)
        indices = np.abs(times[:, None] - targets[None]).argmin(0) if resample else np.arange(len(times))
        pose = np.stack([f.pose for f in self.frames])[indices]
        points = [self.frames[i].points for i in indices]
        sign_valid = bool((pose[:, :33, 3] >= .5).any() and (pose[:, 33:, 3] > 0).any())
        mouth, geometry = None, {}
        try:
            filtered, geometry = filter_points(points, pose)
            mouth = crops_from_gray([self.frames[i].gray for i in indices], filtered, self.reference)
        except ValueError as exc:
            geometry["unavailable_reason"] = str(exc)
        info = dict(frame_count=len(times), sampled_frames=len(indices),
                    capture_span_ms=float(times[-1] - times[0]),
                    input_fps=float((len(times) - 1) * 1000 / (times[-1] - times[0])),
                    max_capture_gap_ms=float(np.diff(times).max()),
                    frame_ids=[self.frames[i].frame_id for i in indices],
                    geometry=geometry, sign_valid=sign_valid, mouth_valid=mouth is not None,
                    hand_coverage=float(np.any(pose[:, 33:, 3] > 0, axis=1).mean()),
                    single_face_fraction=float(np.mean([f.faces == 1 for f in self.frames])),
                    preprocess_ms=sum(f.preprocess_ms for f in self.frames),
                    roi_ms=(time.perf_counter() - start) * 1000,
                    sampling="nearest capture timestamp at 25fps" if resample else "ffmpeg fps=25",
                    source_resolution=[self.frames[0].source_width, self.frames[0].source_height])
        return pose if sign_valid else None, mouth, info
