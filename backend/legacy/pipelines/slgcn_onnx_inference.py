"""NumPy preprocessing and ONNX Runtime inference for the VISL-400 SL-GCN.

This mirrors the *training* transform order:
joint-wise distribution normalization -> 27-joint selection -> repeat padding
-> bone stream -> root normalization -> ``N,C,T,V,M``.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import onnxruntime as ort

from pipelines.spoter_onnx_inference import load_id2label


class SLGCNONNXInferer:
    POSE_IDXS = (0, 11, 12, 13, 14, 15, 16)
    HAND_IDXS = (0, 4, 5, 8, 9, 12, 13, 16, 17, 20)
    BONE_EDGES = (
        (0, 1), (0, 2), (1, 3), (3, 5), (2, 4), (4, 6),
        (7, 8), (7, 9), (7, 11), (7, 13), (7, 15),
        (9, 10), (11, 12), (13, 14), (15, 16),
        (17, 18), (17, 19), (17, 21), (17, 23), (17, 25),
        (19, 20), (21, 22), (23, 24), (25, 26),
        (5, 7), (6, 17),
    )

    def __init__(
        self,
        onnx_path: str,
        id2label: Dict[str, str],
        num_frames: int = 150,
        top_k: int = 3,
        device: str = "auto",
        num_cpu_threads: int = 4,
        min_sequence_frames: int = 30,
        motion_stream: bool = False,
        backend: str = "slgcn",
    ) -> None:
        self.id2label = id2label
        self.num_frames = num_frames
        self.top_k = top_k
        self.backend = backend
        self.min_sequence_frames = min_sequence_frames
        self.motion_stream = motion_stream

        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.enable_mem_pattern = True
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.intra_op_num_threads = 1 if device == "gpu" else num_cpu_threads
        options.inter_op_num_threads = 1

        providers = ["CPUExecutionProvider"]
        if device != "cpu" and "CUDAExecutionProvider" in ort.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.session = ort.InferenceSession(
            onnx_path,
            sess_options=options,
            providers=providers,
        )
        input_shape = self.session.get_inputs()[0].shape
        if input_shape[1:] != [3, num_frames, 27, 1]:
            raise ValueError(
                f"Unexpected SL-GCN input shape {input_shape}; expected [N,3,{num_frames},27,1]"
            )

    @staticmethod
    def _landmarks(component, indexes, confidence_from_visibility: bool) -> np.ndarray:
        output = np.zeros((len(indexes), 3), dtype=np.float32)
        if component is None:
            return output
        points = component.landmark
        for output_index, point_index in enumerate(indexes):
            point = points[point_index]
            confidence = float(point.visibility) if confidence_from_visibility else 1.0
            if confidence <= 0.0:
                continue
            output[output_index] = (float(point.x), float(point.y), confidence)
        return output

    def _select_joints(self, frames: list) -> np.ndarray:
        data = np.zeros((len(frames), 27, 3), dtype=np.float32)
        for frame_index, frame in enumerate(frames):
            data[frame_index] = np.concatenate(
                (
                    self._landmarks(frame.pose_landmarks, self.POSE_IDXS, True),
                    self._landmarks(frame.left_hand_landmarks, self.HAND_IDXS, False),
                    self._landmarks(frame.right_hand_landmarks, self.HAND_IDXS, False),
                ),
                axis=0,
            )
        return data

    @staticmethod
    def _normalize_joint_distribution(data: np.ndarray) -> np.ndarray:
        """Match ``Pose.normalize_distribution`` while preserving masked zeros."""
        normalized = data.copy()
        for joint_index in range(data.shape[1]):
            valid = data[:, joint_index, 2] > 0
            if not np.any(valid):
                continue
            for channel in (0, 1):
                values = data[valid, joint_index, channel]
                std = float(values.std())
                if std > 1e-7:
                    normalized[valid, joint_index, channel] = (
                        values - float(values.mean())
                    ) / std
                else:
                    normalized[valid, joint_index, channel] = 0.0
        return normalized

    def _resample_short_sequence(self, data: np.ndarray) -> np.ndarray:
        """Slow down very short realtime signs to the training time scale.

        VISL-400 clips are typically 60-90 frames at 30 FPS. Mobile realtime
        runs at 15 FPS and fast users can produce only 10-15 captured frames.
        Repeating the whole sequence during 150-frame padding changes its
        temporal frequency; linear interpolation preserves the motion path.
        Confidence uses nearest-neighbour sampling so hand visibility remains a
        discrete observation rather than being invented between detections.
        """
        length = data.shape[0]
        if length == 0 or length >= self.min_sequence_frames:
            return data

        source_times = np.linspace(0.0, 1.0, length)
        target_times = np.linspace(0.0, 1.0, self.min_sequence_frames)
        output = np.empty(
            (self.min_sequence_frames, data.shape[1], data.shape[2]),
            dtype=np.float32,
        )
        for joint_index in range(data.shape[1]):
            for channel in (0, 1):
                output[:, joint_index, channel] = np.interp(
                    target_times,
                    source_times,
                    data[:, joint_index, channel],
                )

        nearest = np.rint(
            np.linspace(0, length - 1, self.min_sequence_frames)
        ).astype(np.int64)
        output[:, :, 2] = data[nearest, :, 2]
        output[:, :, :2][output[:, :, 2] <= 0] = 0.0
        return output

    def _pad(self, data: np.ndarray) -> np.ndarray:
        length = data.shape[0]
        if length == 0:
            raise ValueError("At least one keypoint frame is required")
        if length >= self.num_frames:
            padded = data[: self.num_frames]
        else:
            repeat_count = int(np.ceil(self.num_frames / length))
            padded = np.concatenate([data] * repeat_count, axis=0)[: self.num_frames]
        # T,V,C -> C,T,V,M
        return padded.transpose(2, 0, 1)[:, :, :, np.newaxis].astype(np.float32)

    def _bone_stream(self, data: np.ndarray) -> np.ndarray:
        bone = np.zeros_like(data)
        for source, target in self.BONE_EDGES:
            bone[:2, :, target, :] = (
                data[:2, :, target, :] - data[:2, :, source, :]
            )
            bone[2, :, target, :] = np.minimum(
                data[2, :, target, :], data[2, :, source, :]
            )
        return bone

    @staticmethod
    def _motion_stream(data: np.ndarray) -> np.ndarray:
        """Match the training transform's forward temporal difference."""
        motion = np.zeros_like(data)
        motion[:, :-1, :, :] = data[:, 1:, :, :] - data[:, :-1, :, :]
        return motion

    def preprocess(self, frames: list) -> np.ndarray:
        selected = self._select_joints(frames)
        selected = self._resample_short_sequence(selected)
        selected = self._normalize_joint_distribution(selected)
        data = self._pad(selected)
        data = self._bone_stream(data)
        if self.motion_stream:
            data = self._motion_stream(data)
        data[0] -= data[0, :, 0, 0].mean()
        data[1] -= data[1, :, 0, 0].mean()
        return data[np.newaxis].astype(np.float32)

    def infer(self, mediapipe_list: list) -> List[Dict[str, float]]:
        model_input = self.preprocess(mediapipe_list)
        logits = self.session.run(["logits"], {"poses": model_input})[0]
        if not np.isfinite(logits).all():
            raise ValueError("Model returned non-finite logits")
        logits = logits - np.max(logits, axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= np.sum(probabilities, axis=1, keepdims=True)
        top_k = min(self.top_k, probabilities.shape[1])
        indexes = np.argsort(-probabilities[0])[:top_k]
        return [
            {
                "gloss": self.id2label.get(str(int(index)), f"unk_{int(index)}"),
                "score": float(probabilities[0, index]),
            }
            for index in indexes
        ]


class DSTAONNXInferer(SLGCNONNXInferer):
    """DSTA uses the SL-GCN joint contract with bone then motion transforms."""

    def __init__(
        self,
        onnx_path: str,
        id2label: Dict[str, str],
        num_frames: int = 150,
        top_k: int = 3,
        device: str = "auto",
        num_cpu_threads: int = 4,
        min_sequence_frames: int = 30,
    ) -> None:
        super().__init__(
            onnx_path,
            id2label,
            num_frames=num_frames,
            top_k=top_k,
            device=device,
            num_cpu_threads=num_cpu_threads,
            min_sequence_frames=min_sequence_frames,
            motion_stream=True,
            backend="dsta",
        )


__all__ = ["DSTAONNXInferer", "SLGCNONNXInferer", "load_id2label"]
