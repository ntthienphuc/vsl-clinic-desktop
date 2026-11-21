"""Read authenticated motion timing without loading geometry into the backend."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct


def motion_metadata(assets: Path, entry: dict) -> dict:
    relative = entry["path"]
    if not relative.startswith("/assets/motions/"):
        raise ValueError("Invalid motion asset path")
    path = (assets / relative.removeprefix("/assets/")).resolve()
    if not path.is_relative_to((assets / "motions").resolve()):
        raise ValueError("Motion asset escaped its directory")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(f"Motion checksum mismatch: {entry['id']}")
    if path.suffix == ".json":
        motion = json.loads(data)
        result = {"id": motion["id"], "duration_ms": motion["duration_ms"],
                  "frame_count": len(motion["frames"]), "original_sha256": digest}
    elif path.suffix == ".vslm":
        if len(data) < 16 or data[:8] != b"VSLM1\0\0\0":
            raise ValueError("Invalid packed motion signature")
        size = struct.unpack_from("<I", data, 8)[0]
        if not 2 <= size <= 64_000 or 12 + size > len(data):
            raise ValueError("Invalid packed motion header")
        result = json.loads(data[12:12 + size])
        scale = result["scale"]
        if (result.get("schema") != "clinic-motion-packed-v1" or result["joint_count"] != 75
                or not math.isfinite(scale) or not 0 < scale <= 100_000
                or 12 + size + result["frame_count"] * 75 * 3 * 2 != len(data)
                or result["original_sha256"] != entry["original_sha256"]):
            raise ValueError("Invalid packed motion contract")
    else:
        raise ValueError("Unsupported motion format")
    if (result["id"] != entry["id"] or result["duration_ms"] != entry["duration_ms"]
            or not math.isfinite(result["duration_ms"]) or not 0 < result["duration_ms"] <= 120_000
            or type(result["frame_count"]) is not int or not 2 <= result["frame_count"] <= 2048):
        raise ValueError("Invalid motion timing")
    return result
