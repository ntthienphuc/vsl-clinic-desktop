"""Isolated 400-gloss recognizer and in-memory port of the product segmenter."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import time

import numpy as np
import onnxruntime as ort

LEGACY = Path(__file__).resolve().parent / "legacy"
sys.path.insert(0, str(LEGACY))
from data.utils import Arm, is_arm_active, ok_to_get_frame
from pipelines.slgcn_onnx_inference import SLGCNONNXInferer
from pipelines.spoter_onnx_inference import load_id2label


MODEL_SHA256 = "582f3d8712f73f78c5fe7b7521609ea54a9257e5a3a877aa8c9346b8e28ebb21"
CAPTURE_PROFILE = "clinic-pc-tasks-lite-parallel-v2"


def sampling_quality(frames):
    times = [getattr(frame, "clinic_timestamp_ms", None) for frame in frames]
    if len(times) < 2 or any(t is None for t in times):
        return {"observed_fps": None, "maximum_observation_gap_ms": None, "quality_warning": None}
    elapsed = times[-1] - times[0]
    fps = (len(times) - 1) * 1000 / elapsed if elapsed > 0 else 0
    gap = max(b - a for a, b in zip(times, times[1:]))
    # Operational sampling guard, not an accuracy guarantee above this limit.
    warning = ("Hình ảnh bị thiếu nhịp. Vui lòng ký lại chậm hơn; kiểm tra các ứng dụng đang làm máy bận."
               if fps < 12 or gap > 250 else None)
    return {"observed_fps": fps, "maximum_observation_gap_ms": gap, "quality_warning": warning}


class Segmenter:
    """Same signing-space/debounce policy, scoped to one capture generation."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.left = Arm("left", 0.5)
        self.right = Arm("right", 0.5)
        self.frames = []
        self.candidate = []
        self.last_timestamp = None
        self.last_active_epoch_ms = None
        self.start_source_ms = None

    def consume(self, result, timestamp_ms: float, captured_epoch_ms: float):
        if not np.isfinite(timestamp_ms):
            raise ValueError("Invalid capture timestamp")
        if self.last_timestamp is not None and timestamp_ms <= self.last_timestamp:
            raise ValueError("Capture timestamps must increase")
        self.last_timestamp = timestamp_ms
        points = result.pose_landmarks.landmark if result.pose_landmarks else None
        self.left.set_pose(points)
        self.right.set_pose(points)
        states = []
        for arm, hand in ((self.left, result.left_hand_landmarks), (self.right, result.right_hand_landmarks)):
            if is_arm_active(arm, 140, hand is not None):
                self.last_active_epoch_ms = captured_epoch_ms
            states.append(ok_to_get_frame(
                arm, angle_threshold=140, min_num_up_frames=4, min_num_down_frames=4,
                current_time=timestamp_ms, delay=0, min_down_time_ms=300,
                hand_visible=hand is not None,
            ))
        if any(states):
            if not self.frames:
                self.frames.extend(self.candidate)
                self.candidate = []
                self.start_source_ms = timestamp_ms
            self.frames.append(result)
            if len(self.frames) > 900:
                self.reset()
                raise ValueError("Động tác quá dài. Hạ tay rồi thực hiện lại.")
            return None
        pending = self.left.num_up_frames > 0 or self.right.num_up_frames > 0
        if pending:
            self.candidate.append(result)
            self.candidate = self.candidate[-15:]
        elif self.frames:
            return self.flush()
        else:
            self.candidate = []
        return None

    def flush(self):
        result = None
        if len(self.frames) >= 6:
            result = {
                "frames": self.frames,
                "source_start_ms": self.start_source_ms,
                "source_end_ms": self.last_timestamp,
                "last_active_epoch_ms": self.last_active_epoch_ms,
                "segmented_at_epoch_ms": time.time() * 1000,
            }
        last_timestamp = self.last_timestamp
        self.reset()
        self.last_timestamp = last_timestamp
        return result


class Recognizer:
    def __init__(self, assets: Path):
        self.assets = assets
        path = assets / "models/slgcn_bone_all_cams.onnx"
        with path.open("rb") as handle:
            self.sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
        if self.sha256 != MODEL_SHA256:
            raise ValueError("Unexpected recognition model checksum")
        labels = load_id2label(str(assets / "gloss.csv"))
        if len(labels) != 400 or set(labels) != {str(index) for index in range(400)}:
            raise ValueError("Expected exactly 400 contiguous gloss IDs")
        self.model = SLGCNONNXInferer(str(path), labels, device="cpu", num_cpu_threads=2, top_k=3)
        # Keep the inherited preprocessing byte-for-byte. Disable idle spinning
        # in the desktop session so the two landmark graphs and UI keep CPU time.
        options = self.model.session.get_session_options()
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        options.add_session_config_entry("session.inter_op.allow_spinning", "0")
        self.model.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.label_to_id = {label: key for key, label in labels.items()}

    def predict(self, segment: dict) -> dict:
        started = time.time() * 1000
        frames = segment["frames"]
        predictions = self.model.infer(frames)
        coverage = sum(frame.left_hand_landmarks is not None or frame.right_hand_landmarks is not None for frame in frames) / len(frames)
        both = 0
        for frame in frames:
            points = frame.pose_landmarks.landmark if frame.pose_landmarks else None
            arms = [Arm("left", 0.5), Arm("right", 0.5)]
            for arm in arms:
                arm.set_pose(points)
            if is_arm_active(arms[0], 140, frame.left_hand_landmarks is not None) and is_arm_active(arms[1], 140, frame.right_hand_landmarks is not None):
                both += 1
        for prediction in predictions:
            prediction["model_id"] = int(self.label_to_id[prediction["gloss"]])
            prediction["score"] *= min(1.0, coverage / 0.25)
            if prediction["gloss"] == "Con trâu":
                prediction["score"] *= min(1.0, both / len(frames) / 0.30)
        predictions.sort(key=lambda item: item["score"], reverse=True)
        ended = time.time() * 1000
        return {
            "predictions": predictions,
            **sampling_quality(frames),
            "frame_count": len(frames),
            "hand_coverage": coverage,
            "inference_ms": ended - started,
            "queue_ms": started - segment["segmented_at_epoch_ms"],
            "last_active_epoch_ms": segment["last_active_epoch_ms"],
            "server_result_epoch_ms": ended,
            "source_start_ms": segment["source_start_ms"],
            "source_end_ms": segment["source_end_ms"],
            "model": "SL-GCN / 400 gloss",
            "profile": CAPTURE_PROFILE,
        }
