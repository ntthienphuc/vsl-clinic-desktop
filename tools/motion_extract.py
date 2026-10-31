"""Versioned 3D motion extraction, distinct from SL-GCN's 2D/confidence input."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "clinic-tasks-world-v1"
BODY_COUNT = 33
LEFT = slice(33, 54)
RIGHT = slice(54, 75)


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def extract_clip(row: dict, target_fps: float = 15) -> Path:
    source = Path(row["path"])
    source_hash = digest(source)
    if source_hash != row["sha256"]:
        raise ValueError(f"Source changed: {source}")
    cache = ROOT / "research/cache" / f"{row['video_id']}-{PROFILE}.npz"
    if cache.exists():
        with np.load(cache, allow_pickle=False) as old:
            if str(old["source_sha256"]) == source_hash:
                return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f"Cannot decode {source}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        cap.release()
        raise ValueError(f"Invalid FPS: {source}")
    pose_options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(ROOT / "assets/models/pose_landmarker_lite.task")),
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    hand_options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(ROOT / "assets/models/hand_landmarker.task")),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.45,
        min_tracking_confidence=0.5,
    )
    worlds = []
    images = []
    masks = []
    times = []
    hand_locals = []
    frame_index = 0
    next_sample = 0.0
    with vision.PoseLandmarker.create_from_options(pose_options) as pose, vision.HandLandmarker.create_from_options(hand_options) as hands:
        try:
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break
                time_ms = frame_index * 1000.0 / fps
                frame_index += 1
                if time_ms + 0.001 < next_sample:
                    continue
                next_sample += 1000.0 / target_fps
                scale = min(1.0, 960 / max(bgr.shape[:2]))
                if scale < 1:
                    bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                height, width = bgr.shape[:2]
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                stamp = int(round(time_ms))
                result_pose = pose.detect_for_video(image, stamp)
                result_hands = hands.detect_for_video(image, stamp)
                world = np.full((75, 3), np.nan, np.float32)
                xy = np.full((75, 2), np.nan, np.float32)
                mask = np.zeros(75, np.float32)
                local = np.full((2, 21, 3), np.nan, np.float32)
                if result_pose.pose_landmarks:
                    world[:33] = [[p.x, p.y, p.z] for p in result_pose.pose_world_landmarks[0]]
                    xy[:33] = [[p.x * width, p.y * height] for p in result_pose.pose_landmarks[0]]
                    mask[:33] = [p.visibility for p in result_pose.pose_landmarks[0]]
                    candidates = []
                    for hand_index, landmarks in enumerate(result_hands.hand_landmarks):
                        wrist = np.array([landmarks[0].x * width, landmarks[0].y * height])
                        for side, pose_index in enumerate((15, 16)):
                            distance = np.linalg.norm(wrist - xy[pose_index]) / width
                            candidates.append((distance, side, hand_index))
                    used_sides = set()
                    used_hands = set()
                    for distance, side, hand_index in sorted(candidates):
                        if distance > 0.18 or side in used_sides or hand_index in used_hands:
                            continue
                        used_sides.add(side)
                        used_hands.add(hand_index)
                        start = 33 + side * 21
                        hand_world = np.array([[p.x, p.y, p.z] for p in result_hands.hand_world_landmarks[hand_index]], np.float32)
                        hand_world -= hand_world[0].copy()
                        local[side] = hand_world
                        world[start:start + 21] = hand_world + world[15 + side]
                        xy[start:start + 21] = [[p.x * width, p.y * height] for p in result_hands.hand_landmarks[hand_index]]
                        mask[start:start + 21] = 1
                worlds.append(world)
                images.append(xy)
                masks.append(mask)
                times.append(time_ms)
                hand_locals.append(local)
        finally:
            cap.release()
    if len(times) < 8:
        raise ValueError(f"Too few decoded frames: {source}")
    world = np.stack(worlds)
    xy = np.stack(images)
    mask = np.stack(masks)
    valid_anchor = (mask[:, 11] > 0.5) & (mask[:, 12] > 0.5)
    widths = np.linalg.norm(world[:, 11] - world[:, 12], axis=1)
    scale = np.nanmedian(widths[valid_anchor])
    if not np.isfinite(scale) or scale < 0.08:
        raise ValueError(f"Degenerate body anchors: {source}")
    center = (world[:, 11] + world[:, 12]) / 2
    world = (world - center[:, None]) / scale
    # Camera x-right, y-down, z-away -> viewer x-right, y-up, z-toward.
    world *= np.array([1, -1, -1], np.float32)
    image_width = np.nanmedian(np.linalg.norm(xy[valid_anchor, 11] - xy[valid_anchor, 12], axis=1))
    xy = (xy - ((xy[:, 11] + xy[:, 12]) / 2)[:, None]) / image_width
    np.savez_compressed(
        cache,
        xyz=world,
        xy=xy,
        confidence=mask,
        time_ms=np.asarray(times),
        source_sha256=source_hash,
        profile=PROFILE,
        source_fps=fps,
        sampled_fps=1000 / np.median(np.diff(times)),
        shoulder_scale_m=float(scale),
    )
    return cache


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "research/source-manifest.json").read_text(encoding="utf-8"))
    row = next(row for word in manifest["words"] for row in word["references"] if row["video_id"] == args.video_id)
    print(extract_clip(row))
