from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import types
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data_ouput"
REPORT_DIR = ROOT / "label_reports"
GLOSS_CSV = ROOT / "sign" / "gloss.csv"
TARGET_COUNT = 60


BODY_LANDMARKS = [
    "nose",
    "neck",
    "rightEye",
    "leftEye",
    "rightEar",
    "leftEar",
    "rightShoulder",
    "leftShoulder",
    "rightElbow",
    "leftElbow",
    "rightWrist",
    "leftWrist",
]

HAND_LANDMARKS = [
    "wrist",
    "indexTip",
    "indexDIP",
    "indexPIP",
    "indexMCP",
    "middleTip",
    "middleDIP",
    "middlePIP",
    "middleMCP",
    "ringTip",
    "ringDIP",
    "ringPIP",
    "ringMCP",
    "littleTip",
    "littleDIP",
    "littlePIP",
    "littleMCP",
    "thumbTip",
    "thumbIP",
    "thumbMP",
    "thumbCMC",
]

LANDMARKS = BODY_LANDMARKS + [
    f"{name}_{hand_idx}" for name in HAND_LANDMARKS for hand_idx in (0, 1)
]

POSE_INDEX = {
    "NOSE": 0,
    "LEFT_EYE": 2,
    "RIGHT_EYE": 5,
    "LEFT_EAR": 7,
    "RIGHT_EAR": 8,
    "LEFT_SHOULDER": 11,
    "RIGHT_SHOULDER": 12,
    "LEFT_ELBOW": 13,
    "RIGHT_ELBOW": 14,
    "LEFT_WRIST": 15,
    "RIGHT_WRIST": 16,
}

HAND_INDEX = {
    "WRIST": 0,
    "THUMB_CMC": 1,
    "THUMB_MCP": 2,
    "THUMB_IP": 3,
    "THUMB_TIP": 4,
    "INDEX_FINGER_MCP": 5,
    "INDEX_FINGER_PIP": 6,
    "INDEX_FINGER_DIP": 7,
    "INDEX_FINGER_TIP": 8,
    "MIDDLE_FINGER_MCP": 9,
    "MIDDLE_FINGER_PIP": 10,
    "MIDDLE_FINGER_DIP": 11,
    "MIDDLE_FINGER_TIP": 12,
    "RING_FINGER_MCP": 13,
    "RING_FINGER_PIP": 14,
    "RING_FINGER_DIP": 15,
    "RING_FINGER_TIP": 16,
    "PINKY_MCP": 17,
    "PINKY_PIP": 18,
    "PINKY_DIP": 19,
    "PINKY_TIP": 20,
}

SPOTER_BODY_POINTS = [
    "NOSE",
    "NECK",
    "RIGHT_EYE",
    "LEFT_EYE",
    "RIGHT_EAR",
    "LEFT_EAR",
    "RIGHT_SHOULDER",
    "LEFT_SHOULDER",
    "RIGHT_ELBOW",
    "LEFT_ELBOW",
    "RIGHT_WRIST",
    "LEFT_WRIST",
]

SPOTER_HAND_POINTS = [
    "WRIST",
    "INDEX_FINGER_TIP",
    "INDEX_FINGER_DIP",
    "INDEX_FINGER_PIP",
    "INDEX_FINGER_MCP",
    "MIDDLE_FINGER_TIP",
    "MIDDLE_FINGER_DIP",
    "MIDDLE_FINGER_PIP",
    "MIDDLE_FINGER_MCP",
    "RING_FINGER_TIP",
    "RING_FINGER_DIP",
    "RING_FINGER_PIP",
    "RING_FINGER_MCP",
    "PINKY_DIP",
    "PINKY_TIP",
    "PINKY_PIP",
    "PINKY_MCP",
    "THUMB_TIP",
    "THUMB_IP",
    "THUMB_MCP",
    "THUMB_CMC",
]

SLGCN_JOINTS_27 = [
    0,
    5,
    6,
    7,
    8,
    9,
    10,
    91,
    95,
    96,
    99,
    100,
    103,
    104,
    107,
    108,
    111,
    112,
    116,
    117,
    120,
    121,
    124,
    125,
    128,
    129,
    132,
]

COCO_TO_NPZ = {
    0: 0,
    5: 11,
    6: 12,
    7: 13,
    8: 14,
    9: 15,
    10: 16,
    91: 33 + 0,
    95: 33 + 4,
    96: 33 + 5,
    99: 33 + 8,
    100: 33 + 9,
    103: 33 + 12,
    104: 33 + 13,
    107: 33 + 16,
    108: 33 + 17,
    111: 33 + 20,
    112: 54 + 0,
    116: 54 + 4,
    117: 54 + 5,
    120: 54 + 8,
    121: 54 + 9,
    124: 54 + 12,
    125: 54 + 13,
    128: 54 + 16,
    129: 54 + 17,
    132: 54 + 20,
}

SLGCN_BONE_IDXS = (
    (5, 6),
    (5, 7),
    (6, 8),
    (8, 10),
    (7, 9),
    (9, 11),
    (12, 13),
    (12, 14),
    (12, 16),
    (12, 18),
    (12, 20),
    (14, 15),
    (16, 17),
    (18, 19),
    (20, 21),
    (22, 23),
    (22, 24),
    (22, 26),
    (22, 28),
    (22, 30),
    (24, 25),
    (26, 27),
    (28, 29),
    (30, 31),
    (10, 12),
    (11, 22),
)


@dataclass(frozen=True)
class ClipItem:
    cam: str
    folder: str
    index: int
    video: Path
    keypoints: Path


def natural_key(path_or_name: Path | str) -> list[object]:
    name = path_or_name.name if isinstance(path_or_name, Path) else str(path_or_name)
    stem = Path(name).stem
    parts = re.split(r"(\d+)", stem)
    return [int(part) if part.isdigit() else part.lower() for part in parts if part]


def load_gloss(path: Path) -> tuple[dict[int, str], dict[str, int]]:
    explicit_labels: dict[int, str] = {}
    sequential_labels: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            cells = [cell.strip() for cell in row]
            if not cells[0] or cells[0].lower() in {"id", "gloss", "label", "word"}:
                continue
            if len(cells) >= 2 and cells[0].isdigit():
                explicit_labels[int(cells[0])] = cells[1]
            else:
                sequential_labels.append(cells[-1] if len(cells) > 1 else cells[0])
    if explicit_labels:
        id2label = dict(sorted(explicit_labels.items()))
    else:
        id2label = {idx: label for idx, label in enumerate(sequential_labels)}
    label2id = {label: idx for idx, label in id2label.items()}
    return id2label, label2id


def discover_clips(minh_only: bool = False, folders: list[str] | None = None) -> list[ClipItem]:
    wanted_folders = {f.lower() for f in folders or []}
    items: list[ClipItem] = []
    for cam_dir in sorted(DATA_ROOT.glob("cam*"), key=lambda p: p.name):
        if not cam_dir.is_dir():
            continue
        for folder_dir in sorted(cam_dir.iterdir(), key=lambda p: natural_key(p.name)):
            if not folder_dir.is_dir() or folder_dir.name.startswith("_"):
                continue
            if wanted_folders and folder_dir.name.lower() not in wanted_folders:
                continue
            if minh_only and not folder_dir.name.lower().startswith("minh"):
                continue
            clips_dir = folder_dir / "clips"
            if not clips_dir.exists():
                continue
            for video in sorted(clips_dir.glob("*.mp4"), key=natural_key):
                match = re.match(r"^(\d+)", video.stem)
                keypoints = video.with_suffix(".keypoints.npz")
                items.append(
                    ClipItem(
                        cam=cam_dir.name,
                        folder=folder_dir.name,
                        index=int(match.group(1)) if match else -1,
                        video=video,
                        keypoints=keypoints,
                    )
                )
    return items


def load_keypoints(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    with np.load(path) as data:
        keypoints = data["keypoints"].astype(np.float32)
    if keypoints.ndim != 3 or keypoints.shape[1:] != (75, 4):
        raise ValueError(f"Expected keypoints shape (T,75,4), got {keypoints.shape} at {path}")
    return keypoints


def npz_point(keypoints: np.ndarray, global_idx: int, xy_only: bool = True) -> np.ndarray:
    cols = 2 if xy_only else 3
    return keypoints[:, global_idx, :cols]


def spoter_joint_select(keypoints: np.ndarray) -> torch.Tensor:
    selected: list[np.ndarray] = []
    for point in SPOTER_BODY_POINTS:
        if point == "NECK":
            selected.append(np.zeros((keypoints.shape[0], 2), dtype=np.float32))
        else:
            selected.append(npz_point(keypoints, POSE_INDEX[point]))
    for hand_offset in (33, 54):
        for point in SPOTER_HAND_POINTS:
            selected.append(npz_point(keypoints, hand_offset + HAND_INDEX[point]))
    data = np.stack(selected, axis=1)
    return torch.from_numpy(data.astype(np.float32))


def spoter_tensor_to_dict(data: torch.Tensor) -> dict[str, np.ndarray]:
    array = data.numpy()
    return {landmark: array[:, idx].copy() for idx, landmark in enumerate(LANDMARKS)}


def spoter_dict_to_tensor(row: dict[str, np.ndarray]) -> torch.Tensor:
    output = np.empty((len(row["leftEar"]), len(LANDMARKS), 2), dtype=np.float32)
    for idx, landmark in enumerate(LANDMARKS):
        output[:, idx, :] = row[landmark]
    return torch.from_numpy(output)


def spoter_body_normalize(row: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    original = {k: v.copy() for k, v in row.items()}
    valid_sequence = True
    last_starting_point = None
    last_ending_point = None

    for sequence_index in range(len(row["leftEar"])):
        missing_shoulders = (
            row["leftShoulder"][sequence_index][0] == 0
            or row["rightShoulder"][sequence_index][0] == 0
        )
        missing_neck_nose = (
            row["neck"][sequence_index][0] == 0 or row["nose"][sequence_index][0] == 0
        )
        if missing_shoulders and missing_neck_nose:
            if last_starting_point is None:
                valid_sequence = False
                continue
            starting_point = list(last_starting_point)
            ending_point = list(last_ending_point)
        else:
            if (
                row["leftShoulder"][sequence_index][0] != 0
                and row["rightShoulder"][sequence_index][0] != 0
            ):
                left = row["leftShoulder"][sequence_index]
                right = row["rightShoulder"][sequence_index]
                head_metric = float(np.linalg.norm(left - right))
            else:
                neck = row["neck"][sequence_index]
                nose = row["nose"][sequence_index]
                head_metric = float(np.linalg.norm(neck - nose))

            starting_point = [
                row["neck"][sequence_index][0] - 3 * head_metric,
                row["leftEye"][sequence_index][1] + head_metric,
            ]
            ending_point = [
                row["neck"][sequence_index][0] + 3 * head_metric,
                starting_point[1] - 6 * head_metric,
            ]
            last_starting_point = list(starting_point)
            last_ending_point = list(ending_point)

        starting_point[0] = max(starting_point[0], 0)
        starting_point[1] = max(starting_point[1], 0)
        ending_point[0] = max(ending_point[0], 0)
        ending_point[1] = max(ending_point[1], 0)

        width = ending_point[0] - starting_point[0]
        height = starting_point[1] - ending_point[1]
        if width == 0 or height == 0:
            valid_sequence = False
            continue

        for key in BODY_LANDMARKS:
            if row[key][sequence_index][0] == 0:
                continue
            row[key][sequence_index][0] = (row[key][sequence_index][0] - starting_point[0]) / width
            row[key][sequence_index][1] = (row[key][sequence_index][1] - ending_point[1]) / height

    return row if valid_sequence else original


def spoter_hand_normalize(row: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    hand_keys = {
        hand_idx: [f"{identifier}_{hand_idx}" for identifier in HAND_LANDMARKS]
        for hand_idx in (0, 1)
    }
    for hand_idx in (0, 1):
        for sequence_index in range(len(row[f"wrist_{hand_idx}"])):
            xs = [
                row[key][sequence_index][0]
                for key in hand_keys[hand_idx]
                if row[key][sequence_index][0] != 0
            ]
            ys = [
                row[key][sequence_index][1]
                for key in hand_keys[hand_idx]
                if row[key][sequence_index][1] != 0
            ]
            if not xs or not ys:
                continue
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            if width > height:
                delta_x = 0.1 * width
                delta_y = delta_x + ((width - height) / 2)
            else:
                delta_y = 0.1 * height
                delta_x = delta_y + ((height - width) / 2)
            starting_point = (min(xs) - delta_x, min(ys) - delta_y)
            ending_point = (max(xs) + delta_x, max(ys) + delta_y)
            denom_x = ending_point[0] - starting_point[0]
            denom_y = ending_point[1] - starting_point[1]
            if denom_x == 0 or denom_y == 0:
                continue
            for identifier in HAND_LANDMARKS:
                key = f"{identifier}_{hand_idx}"
                if row[key][sequence_index][0] == 0:
                    continue
                row[key][sequence_index][0] = (row[key][sequence_index][0] - starting_point[0]) / denom_x
                row[key][sequence_index][1] = (row[key][sequence_index][1] - starting_point[1]) / denom_y
    return row


def pad_repeat_torch(data: torch.Tensor, num_frames: int) -> torch.Tensor:
    padded = torch.zeros((num_frames, data.shape[1], data.shape[2]), dtype=torch.float32)
    length = data.shape[0]
    if length == 0:
        return padded
    if length < num_frames:
        padded[:length] = data
        rest = num_frames - length
        repeats = int(np.ceil(rest / length))
        padded[length:] = torch.cat([data for _ in range(repeats)], dim=0)[:rest]
    else:
        padded[:] = data[:num_frames]
    return padded


def make_spoter_input(keypoints: np.ndarray, num_frames: int = 70) -> torch.Tensor:
    data = spoter_joint_select(keypoints)
    row = spoter_tensor_to_dict(data)
    row = spoter_body_normalize(row)
    row = spoter_hand_normalize(row)
    data = spoter_dict_to_tensor(row)
    data = pad_repeat_torch(data, num_frames)
    return data - 0.5


def slgcn_joint_select(keypoints: np.ndarray) -> np.ndarray:
    coords = keypoints[:, :, :2].copy()
    mu = coords.mean(axis=0, keepdims=True)
    std = coords.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    coords = (coords - mu) / std

    data = np.zeros((keypoints.shape[0], len(SLGCN_JOINTS_27), 3), dtype=np.float32)
    for out_idx, joint in enumerate(SLGCN_JOINTS_27):
        src = COCO_TO_NPZ[joint]
        data[:, out_idx, :2] = coords[:, src, :]
        data[:, out_idx, 2] = keypoints[:, src, 3]
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    return data


def slgcn_pad(data: np.ndarray, num_frames: int = 150) -> np.ndarray:
    padded = np.zeros((num_frames, data.shape[1], data.shape[2], 1), dtype=np.float32)
    length = data.shape[0]
    if length == 0:
        return np.transpose(padded, [2, 0, 1, 3])
    if length < num_frames:
        padded[:length, :, :, 0] = data
        rest = num_frames - length
        repeats = int(np.ceil(rest / length))
        padded[length:, :, :, 0] = np.concatenate([data for _ in range(repeats)], axis=0)[:rest]
    else:
        padded[:, :, :, 0] = data[:num_frames]
    return np.transpose(padded, [2, 0, 1, 3])


def slgcn_bone_stream(data: np.ndarray) -> np.ndarray:
    ori_data = data.copy()
    bone_data = np.zeros_like(data)
    for v1, v2 in SLGCN_BONE_IDXS:
        source_idx = v1 - 5
        target_idx = v2 - 5
        bone_data[:2, :, target_idx, :] = (
            ori_data[:2, :, target_idx, :] - ori_data[:2, :, source_idx, :]
        )
        bone_data[2, :, target_idx, :] = np.minimum(
            ori_data[2, :, target_idx, :],
            ori_data[2, :, source_idx, :],
        )
    return bone_data


def slgcn_normalize(data: np.ndarray, is_vector: bool = False) -> np.ndarray:
    if is_vector:
        data[0, :, 0, :] = data[0, :, 0, :] - data[0, :, 0, 0].mean(axis=0)
        data[1, :, 0, :] = data[1, :, 0, :] - data[1, :, 0, 0].mean(axis=0)
    else:
        data[0, :, :, :] = data[0, :, :, :] - data[0, :, 0, 0].mean(axis=0)
        data[1, :, :, :] = data[1, :, :, :] - data[1, :, 0, 0].mean(axis=0)
    return data


def make_slgcn_input(keypoints: np.ndarray, num_frames: int = 150, bone_stream: bool = True) -> torch.Tensor:
    data = slgcn_joint_select(keypoints)
    data = slgcn_pad(data, num_frames)
    if bone_stream:
        data = slgcn_bone_stream(data)
    data = slgcn_normalize(data, is_vector=False)
    return torch.from_numpy(data.astype(np.float32))


def load_models(id2label: dict[int, str], label2id: dict[str, int], device: torch.device):
    sys.path.insert(0, str(ROOT))
    from spoter_checkpoint.configuration import SPOTERConfig
    from spoter_checkpoint.modelling import SPOTERForGraphClassification
    from sl_gcn_checkpoint.configuration import SLGCNConfig
    from sl_gcn_checkpoint.modelling import SLGCNForGraphClassification

    spoter_dir = ROOT / "spoter_checkpoint"
    slgcn_dir = ROOT / "sl_gcn_checkpoint"

    spoter_cfg = SPOTERConfig.from_pretrained(str(spoter_dir))
    spoter_cfg.pretrained = str(spoter_dir)
    spoter_cfg.id2label = {str(k): v for k, v in id2label.items()}
    spoter_cfg.label2id = label2id
    spoter_model = SPOTERForGraphClassification(spoter_cfg, label2id=label2id, id2label=spoter_cfg.id2label)
    spoter_model.to(device).eval()

    slgcn_cfg = SLGCNConfig.from_pretrained(str(slgcn_dir))
    slgcn_cfg.pretrained = str(slgcn_dir)
    slgcn_cfg.id2label = {str(k): v for k, v in id2label.items()}
    slgcn_cfg.label2id = label2id
    slgcn_model = SLGCNForGraphClassification(slgcn_cfg, label2id=label2id, id2label=slgcn_cfg.id2label)
    slgcn_model.to(device).eval()

    return spoter_model, slgcn_model, spoter_cfg, slgcn_cfg


def load_pose_transform_modules():
    import importlib.util

    stub = types.ModuleType("utils")
    stub.BODY_LANDMARKS = BODY_LANDMARKS
    stub.HAND_LANDMARKS = HAND_LANDMARKS
    stub.LANDMARKS = LANDMARKS
    stub.SLGCN_JOINTS = {27: np.array(SLGCN_JOINTS_27)}
    stub.COCO_TO_POSE_FORMAT = {
        0: ("POSE_LANDMARKS", "NOSE"),
        5: ("POSE_LANDMARKS", "LEFT_SHOULDER"),
        6: ("POSE_LANDMARKS", "RIGHT_SHOULDER"),
        7: ("POSE_LANDMARKS", "LEFT_ELBOW"),
        8: ("POSE_LANDMARKS", "RIGHT_ELBOW"),
        9: ("POSE_LANDMARKS", "LEFT_WRIST"),
        10: ("POSE_LANDMARKS", "RIGHT_WRIST"),
        91: ("LEFT_HAND_LANDMARKS", "WRIST"),
        95: ("LEFT_HAND_LANDMARKS", "THUMB_TIP"),
        96: ("LEFT_HAND_LANDMARKS", "INDEX_FINGER_MCP"),
        99: ("LEFT_HAND_LANDMARKS", "INDEX_FINGER_TIP"),
        100: ("LEFT_HAND_LANDMARKS", "MIDDLE_FINGER_MCP"),
        103: ("LEFT_HAND_LANDMARKS", "MIDDLE_FINGER_TIP"),
        104: ("LEFT_HAND_LANDMARKS", "RING_FINGER_MCP"),
        107: ("LEFT_HAND_LANDMARKS", "RING_FINGER_TIP"),
        108: ("LEFT_HAND_LANDMARKS", "PINKY_MCP"),
        111: ("LEFT_HAND_LANDMARKS", "PINKY_TIP"),
        112: ("RIGHT_HAND_LANDMARKS", "WRIST"),
        116: ("RIGHT_HAND_LANDMARKS", "THUMB_TIP"),
        117: ("RIGHT_HAND_LANDMARKS", "INDEX_FINGER_MCP"),
        120: ("RIGHT_HAND_LANDMARKS", "INDEX_FINGER_TIP"),
        121: ("RIGHT_HAND_LANDMARKS", "MIDDLE_FINGER_MCP"),
        124: ("RIGHT_HAND_LANDMARKS", "MIDDLE_FINGER_TIP"),
        125: ("RIGHT_HAND_LANDMARKS", "RING_FINGER_MCP"),
        128: ("RIGHT_HAND_LANDMARKS", "RING_FINGER_TIP"),
        129: ("RIGHT_HAND_LANDMARKS", "PINKY_MCP"),
        132: ("RIGHT_HAND_LANDMARKS", "PINKY_TIP"),
    }
    sys.modules["utils"] = stub

    def load_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    spoter_transforms = load_module("codex_spoter_transforms", ROOT / "sign" / "features" / "transforms" / "spoter.py")
    slgcn_transforms = load_module("codex_slgcn_transforms", ROOT / "sign" / "features" / "transforms" / "sl_gcn.py")
    return spoter_transforms, slgcn_transforms


def pose_exe() -> str:
    for venv_name in (".venv_auslan", ".venv"):
        exe = ROOT / venv_name / "Scripts" / "video_to_pose.exe"
        if exe.exists():
            return str(exe)
    return "video_to_pose"


def ensure_pose(video: Path, workers: int, overwrite: bool = False) -> Path:
    pose = video.with_suffix(".pose")
    if pose.exists() and not overwrite:
        return pose
    cmd = [
        pose_exe(),
        "--format",
        "mediapipe",
        "--workers",
        str(workers),
        "-i",
        str(video),
        "-o",
        str(pose),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pose


def make_pose_inputs(pose_path: Path, spoter_cfg, slgcn_cfg, pose_modules) -> tuple[torch.Tensor, torch.Tensor]:
    from pose_format import Pose
    from torchvision.transforms.v2 import Compose

    spoter_transforms, slgcn_transforms = pose_modules
    with pose_path.open("rb") as f:
        spoter_pose = Pose.read(f.read())
    spoter_tensor = Compose(
        [
            spoter_transforms.SPOTERJointSelect(),
            spoter_transforms.SPOTERTensorToDict(),
            spoter_transforms.SPOTERSingleBodyDictNormalize(),
            spoter_transforms.SPOTERSingleHandDictNormalize(),
            spoter_transforms.SPOTERDictToTensor(),
            spoter_transforms.SPOTERPad(spoter_cfg.num_frames),
            spoter_transforms.SPOTERShift(),
        ]
    )(spoter_pose)

    with pose_path.open("rb") as f:
        slgcn_pose = Pose.read(f.read())
    slgcn_steps = [
        slgcn_transforms.SLGCNJointSelect(slgcn_cfg.num_points),
        slgcn_transforms.SLGCNPad(slgcn_cfg.num_frames),
    ]
    if slgcn_cfg.bone_stream:
        slgcn_steps.append(slgcn_transforms.SLGCNBoneStream())
    if slgcn_cfg.motion_stream:
        slgcn_steps.append(slgcn_transforms.SLGCNMotionStream())
    slgcn_steps.extend(
        [
            slgcn_transforms.SLGCNNormalize(slgcn_cfg.is_vector),
            slgcn_transforms.NumPyToTensor(),
        ]
    )
    slgcn_tensor = Compose(slgcn_steps)(slgcn_pose)
    return spoter_tensor.float(), slgcn_tensor.float()


def format_topk(ids: np.ndarray, probs: np.ndarray, id2label: dict[int, str]) -> str:
    parts = []
    for idx, prob in zip(ids.tolist(), probs.tolist()):
        parts.append(f"{idx}:{id2label.get(int(idx), '')}:{prob:.4f}")
    return "|".join(parts)


def predict_batch(model, batch: torch.Tensor, device: torch.device, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    with torch.inference_mode():
        logits = model(batch.to(device)).logits
        probs = torch.softmax(logits, dim=1)
        top_probs, top_ids = torch.topk(probs, k=top_k, dim=1)
    return top_ids.cpu().numpy(), top_probs.cpu().numpy()


def chunked(items: list[ClipItem], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def run_inference(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    id2label, label2id = load_gloss(GLOSS_CSV)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    torch.set_num_threads(max(1, args.threads))
    spoter_model, slgcn_model, spoter_cfg, slgcn_cfg = load_models(id2label, label2id, device)
    pose_modules = load_pose_transform_modules() if args.source == "pose" else None

    clips = discover_clips(minh_only=args.minh_only, folders=args.folder)
    clips = sorted(clips, key=lambda x: (x.cam, natural_key(x.folder), x.index))
    if args.limit is not None:
        clips = clips[: args.limit]
    if not clips:
        raise RuntimeError("No clips found")

    stem = args.output_stem or ("minh" if args.minh_only else "full")
    predictions_path = REPORT_DIR / f"inference_{stem}_predictions.csv"
    summary_path = REPORT_DIR / f"inference_{stem}_summary.json"
    suspects_path = REPORT_DIR / f"inference_{stem}_suspects.csv"
    reference_path = REPORT_DIR / f"inference_{stem}_minh_reference.csv"

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []

    for batch_items in tqdm(list(chunked(clips, args.batch_size)), desc="inference"):
        ready_items: list[ClipItem] = []
        spoter_inputs: list[torch.Tensor] = []
        slgcn_inputs: list[torch.Tensor] = []
        for item in batch_items:
            try:
                if args.source == "pose":
                    pose = item.video.with_suffix(".pose")
                    if args.extract_pose or args.overwrite_pose or not pose.exists():
                        pose = ensure_pose(
                            item.video,
                            workers=args.pose_workers,
                            overwrite=args.overwrite_pose,
                        )
                    if not pose.exists():
                        raise FileNotFoundError(pose)
                    spoter_tensor, slgcn_tensor = make_pose_inputs(
                        pose,
                        spoter_cfg=spoter_cfg,
                        slgcn_cfg=slgcn_cfg,
                        pose_modules=pose_modules,
                    )
                else:
                    keypoints = load_keypoints(item.keypoints)
                    spoter_tensor = make_spoter_input(keypoints, num_frames=spoter_cfg.num_frames)
                    slgcn_tensor = make_slgcn_input(
                        keypoints,
                        num_frames=slgcn_cfg.num_frames,
                        bone_stream=bool(slgcn_cfg.bone_stream),
                    )
                spoter_inputs.append(spoter_tensor)
                slgcn_inputs.append(slgcn_tensor)
                ready_items.append(item)
            except Exception as exc:
                errors.append(
                    {
                        "cam": item.cam,
                        "folder": item.folder,
                        "index": str(item.index),
                        "video": str(item.video.relative_to(DATA_ROOT)),
                        "error": repr(exc),
                    }
                )
        if not ready_items:
            continue

        spoter_batch = torch.stack(spoter_inputs, dim=0).float()
        slgcn_batch = torch.stack(slgcn_inputs, dim=0).float()
        spoter_ids, spoter_probs = predict_batch(spoter_model, spoter_batch, device, args.top_k)
        slgcn_ids, slgcn_probs = predict_batch(slgcn_model, slgcn_batch, device, args.top_k)

        for offset, item in enumerate(ready_items):
            expected_id = item.index if 0 <= item.index < TARGET_COUNT else -1
            expected_gloss = id2label.get(expected_id, "")
            spoter_top1 = int(spoter_ids[offset, 0])
            slgcn_top1 = int(slgcn_ids[offset, 0])
            rows.append(
                {
                    "cam": item.cam,
                    "folder": item.folder,
                    "index": item.index,
                    "video": str(item.video.relative_to(DATA_ROOT)),
                    "expected_id": expected_id,
                    "expected_gloss": expected_gloss,
                    "spoter_top1_id": spoter_top1,
                    "spoter_top1_gloss": id2label.get(spoter_top1, ""),
                    "spoter_top1_prob": f"{float(spoter_probs[offset, 0]):.6f}",
                    "spoter_topk": format_topk(spoter_ids[offset], spoter_probs[offset], id2label),
                    "sl_gcn_top1_id": slgcn_top1,
                    "sl_gcn_top1_gloss": id2label.get(slgcn_top1, ""),
                    "sl_gcn_top1_prob": f"{float(slgcn_probs[offset, 0]):.6f}",
                    "sl_gcn_topk": format_topk(slgcn_ids[offset], slgcn_probs[offset], id2label),
                    "models_agree": spoter_top1 == slgcn_top1,
                    "spoter_matches_expected": spoter_top1 == expected_id,
                    "sl_gcn_matches_expected": slgcn_top1 == expected_id,
                }
            )

    fieldnames = [
        "cam",
        "folder",
        "index",
        "video",
        "expected_id",
        "expected_gloss",
        "spoter_top1_id",
        "spoter_top1_gloss",
        "spoter_top1_prob",
        "spoter_topk",
        "sl_gcn_top1_id",
        "sl_gcn_top1_gloss",
        "sl_gcn_top1_prob",
        "sl_gcn_topk",
        "models_agree",
        "spoter_matches_expected",
        "sl_gcn_matches_expected",
    ]
    with predictions_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = build_summary(rows, errors, id2label)
    summary["device"] = str(device)
    summary["source"] = args.source
    summary["num_labels"] = len(id2label)
    summary["gloss_csv"] = str(GLOSS_CSV)
    summary["prediction_csv"] = str(predictions_path)
    summary["minh_reference_csv"] = str(reference_path)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with reference_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "cam",
                "index",
                "spoter_ref_id",
                "spoter_ref_gloss",
                "spoter_votes",
                "sl_gcn_ref_id",
                "sl_gcn_ref_gloss",
                "sl_gcn_votes",
            ],
        )
        writer.writeheader()
        for key, ref in sorted(
            summary["minh_reference_by_cam_index"].items(),
            key=lambda item: (item[0].split("/")[0], int(item[0].split("/")[1])),
        ):
            cam, index = key.split("/")
            writer.writerow(
                {
                    "cam": cam,
                    "index": index,
                    "spoter_ref_id": ref["spoter_id"],
                    "spoter_ref_gloss": ref["spoter_gloss"],
                    "spoter_votes": ref["spoter_votes"],
                    "sl_gcn_ref_id": ref["sl_gcn_id"],
                    "sl_gcn_ref_gloss": ref["sl_gcn_gloss"],
                    "sl_gcn_votes": ref["sl_gcn_votes"],
                }
            )

    suspects = build_suspects(rows)
    with suspects_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "cam",
                "folder",
                "index",
                "expected_gloss",
                "reason",
                "spoter_top1_id",
                "spoter_top1_gloss",
                "spoter_top1_prob",
                "spoter_ref_id",
                "spoter_ref_gloss",
                "sl_gcn_top1_id",
                "sl_gcn_top1_gloss",
                "sl_gcn_top1_prob",
                "sl_gcn_ref_id",
                "sl_gcn_ref_gloss",
                "video",
            ],
        )
        writer.writeheader()
        writer.writerows(suspects)

    print(f"clips={len(clips)} rows={len(rows)} errors={len(errors)}")
    print(f"predictions={predictions_path}")
    print(f"summary={summary_path}")
    print(f"minh_reference={reference_path}")
    print(f"suspects={suspects_path}")
    return predictions_path, summary_path, suspects_path


def build_summary(rows: list[dict[str, object]], errors: list[dict[str, str]], id2label: dict[int, str]) -> dict:
    by_folder: dict[str, dict[str, object]] = {}
    for row in rows:
        key = f"{row['cam']}/{row['folder']}"
        item = by_folder.setdefault(
            key,
            {
                "count": 0,
                "spoter_matches_expected": 0,
                "sl_gcn_matches_expected": 0,
                "models_agree": 0,
            },
        )
        item["count"] += 1
        item["spoter_matches_expected"] += int(bool(row["spoter_matches_expected"]))
        item["sl_gcn_matches_expected"] += int(bool(row["sl_gcn_matches_expected"]))
        item["models_agree"] += int(bool(row["models_agree"]))

    for item in by_folder.values():
        count = max(1, int(item["count"]))
        item["spoter_accuracy"] = round(int(item["spoter_matches_expected"]) / count, 4)
        item["sl_gcn_accuracy"] = round(int(item["sl_gcn_matches_expected"]) / count, 4)
        item["model_agreement_rate"] = round(int(item["models_agree"]) / count, 4)

    minh_votes: dict[str, dict[str, dict[int, int]]] = defaultdict(
        lambda: {"spoter": Counter(), "sl_gcn": Counter()}
    )
    for row in rows:
        if str(row["folder"]).lower().startswith("minh"):
            key = f"{row['cam']}/{row['index']}"
            minh_votes[key]["spoter"][int(row["spoter_top1_id"])] += 1
            minh_votes[key]["sl_gcn"][int(row["sl_gcn_top1_id"])] += 1

    minh_reference = {}
    for key, model_votes in minh_votes.items():
        spoter_id, spoter_count = model_votes["spoter"].most_common(1)[0]
        slgcn_id, slgcn_count = model_votes["sl_gcn"].most_common(1)[0]
        minh_reference[key] = {
            "spoter_id": spoter_id,
            "spoter_gloss": id2label.get(spoter_id, ""),
            "spoter_votes": spoter_count,
            "sl_gcn_id": slgcn_id,
            "sl_gcn_gloss": id2label.get(slgcn_id, ""),
            "sl_gcn_votes": slgcn_count,
        }

    return {
        "rows": len(rows),
        "errors": errors,
        "by_folder": by_folder,
        "minh_reference_by_cam_index": minh_reference,
    }


def build_suspects(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    refs: dict[tuple[str, int], dict[str, tuple[int, str]]] = {}
    votes: dict[tuple[str, int], dict[str, Counter]] = defaultdict(
        lambda: {"spoter": Counter(), "sl_gcn": Counter()}
    )
    for row in rows:
        if not str(row["folder"]).lower().startswith("minh"):
            continue
        key = (str(row["cam"]), int(row["index"]))
        votes[key]["spoter"][(int(row["spoter_top1_id"]), str(row["spoter_top1_gloss"]))] += 1
        votes[key]["sl_gcn"][(int(row["sl_gcn_top1_id"]), str(row["sl_gcn_top1_gloss"]))] += 1
    for key, model_votes in votes.items():
        refs[key] = {
            "spoter": model_votes["spoter"].most_common(1)[0][0],
            "sl_gcn": model_votes["sl_gcn"].most_common(1)[0][0],
        }

    suspects = []
    for row in rows:
        reasons = []
        key = (str(row["cam"]), int(row["index"]))
        ref = refs.get(key)
        spoter_ref = ("", "")
        slgcn_ref = ("", "")
        if ref and not str(row["folder"]).lower().startswith("minh"):
            spoter_ref = ref["spoter"]
            slgcn_ref = ref["sl_gcn"]
            if int(row["spoter_top1_id"]) != int(spoter_ref[0]):
                reasons.append("spoter_not_minh_ref")
            if int(row["sl_gcn_top1_id"]) != int(slgcn_ref[0]):
                reasons.append("sl_gcn_not_minh_ref")
            if row["models_agree"] and (
                int(row["spoter_top1_id"]) != int(spoter_ref[0])
                and int(row["sl_gcn_top1_id"]) != int(slgcn_ref[0])
            ):
                reasons.append("both_models_agree_off_minh_ref")
        elif not str(row["folder"]).lower().startswith("minh"):
            if not row["spoter_matches_expected"]:
                reasons.append("spoter_not_expected")
            if not row["sl_gcn_matches_expected"]:
                reasons.append("sl_gcn_not_expected")
            if row["models_agree"] and not (
                row["spoter_matches_expected"] or row["sl_gcn_matches_expected"]
            ):
                reasons.append("both_models_agree_off_expected")
        if not reasons:
            continue
        suspects.append(
            {
                "cam": row["cam"],
                "folder": row["folder"],
                "index": row["index"],
                "expected_gloss": row["expected_gloss"],
                "reason": ";".join(reasons),
                "spoter_top1_id": row["spoter_top1_id"],
                "spoter_top1_gloss": row["spoter_top1_gloss"],
                "spoter_top1_prob": row["spoter_top1_prob"],
                "spoter_ref_id": spoter_ref[0],
                "spoter_ref_gloss": spoter_ref[1],
                "sl_gcn_top1_id": row["sl_gcn_top1_id"],
                "sl_gcn_top1_gloss": row["sl_gcn_top1_gloss"],
                "sl_gcn_top1_prob": row["sl_gcn_top1_prob"],
                "sl_gcn_ref_id": slgcn_ref[0],
                "sl_gcn_ref_gloss": slgcn_ref[1],
                "video": row["video"],
            }
        )
    return suspects


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minh-only", action="store_true")
    parser.add_argument("--folder", action="append", help="Folder name filter, can be repeated")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--output-stem")
    parser.add_argument("--source", choices=["npz", "pose"], default="npz")
    parser.add_argument("--extract-pose", action="store_true")
    parser.add_argument("--overwrite-pose", action="store_true")
    parser.add_argument("--pose-workers", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_inference(args)


if __name__ == "__main__":
    main()
