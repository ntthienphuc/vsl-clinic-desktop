"""Inventory and incrementally build a compact All_cam1 keypoint bank.

The default command is metadata-only.  Extraction requires an explicit label or
limit so a portable demo is never filled with thousands of unreviewed motions.
This source is the local All_cam1 recognizer collection, not the official QIPEDC
dictionary export.  Raw MP4 files remain untouched; patched arrays are a
separate research artifact.  Use ``build_qipedc_dictionary_index.py`` for the
official QIPEDC dictionary records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "not-loaded; metadata-only"
extract_clip = None


METADATA = ROOT.parent / "All_cam1" / "All_cam1_metadata.json"
VIDEO_ROOT = ROOT.parent / "All_cam1" / "All_cam1"
OUTPUT = ROOT / "research" / "allcam1-bank"


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_metadata() -> list[dict]:
    if not METADATA.is_file():
        raise FileNotFoundError(f"Missing metadata: {METADATA}")
    return json.loads(METADATA.read_text(encoding="utf-8"))


def inventory(rows: list[dict]) -> dict:
    groups: dict[str, dict] = {}
    for row in rows:
        label = row["gloss"]
        group = groups.setdefault(label, {"video_count": 0, "signer_ids": [], "video_ids": []})
        group["video_count"] += 1
        if row["signer_id"] not in group["signer_ids"]:
            group["signer_ids"].append(row["signer_id"])
        if len(group["video_ids"]) < 8:
            group["video_ids"].append(row["video_id"])
    for group in groups.values():
        group["signer_ids"].sort()
    return groups


def patch_short_gaps(values: np.ndarray, max_gap: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Patch short internal NaN runs and retain observed/imputed provenance."""
    import numpy as np

    output = values.astype(np.float32, copy=True)
    observed = np.isfinite(output).all(axis=tuple(range(2, output.ndim))) if output.ndim > 2 else np.isfinite(output)
    if values.ndim == 3:
        observed = np.isfinite(values).all(axis=2)
        imputed = np.zeros(observed.shape, dtype=np.uint8)
        for joint in range(values.shape[1]):
            good = observed[:, joint]
            indexes = np.flatnonzero(good)
            if len(indexes) < 2:
                continue
            for left, right in zip(indexes[:-1], indexes[1:]):
                gap = int(right - left - 1)
                if gap <= 0 or gap > max_gap:
                    continue
                for frame in range(left + 1, right):
                    alpha = (frame - left) / (right - left)
                    output[frame, joint] = output[left, joint] * (1 - alpha) + output[right, joint] * alpha
                    imputed[frame, joint] = 1
        return output, observed.astype(np.uint8), imputed
    raise ValueError("Expected a time x joint x coordinate array")


def compact_keypoints(row: dict, cache: Path, output: Path, max_gap: int) -> dict:
    import numpy as np

    with np.load(cache, allow_pickle=False) as data:
        xyz = data["xyz"].copy()
        xy = data["xy"].copy()
        confidence = data["confidence"].copy()
        times = data["time_ms"].copy()
        source_hash = str(data["source_sha256"])
        profile = str(data["profile"])
    xyz, observed, imputed = patch_short_gaps(xyz, max_gap)
    xy, xy_observed, xy_imputed = patch_short_gaps(xy, max_gap)
    imputed = np.maximum(imputed, xy_imputed)
    target = output / f"{row['video_id']}.npz"
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        target,
        xyz=xyz.astype(np.float16),
        xy=xy.astype(np.float16),
        confidence=confidence.astype(np.float16),
        observed=observed,
        imputed=imputed,
        time_ms=times.astype(np.float32),
        source_sha256=source_hash,
        extractor_profile=profile,
        patch_profile=f"linear-internal-gaps-v1;max_gap={max_gap};observed-preserved",
    )
    return {
        "video_id": row["video_id"],
        "gloss": row["gloss"],
        "signer_id": row["signer_id"],
        "source_sha256": source_hash,
        "path": str(target),
        "frame_count": int(len(times)),
        "observed_fraction": float(observed.mean()),
        "imputed_fraction": float(imputed.mean()),
        "extractor_profile": profile,
        "patch_profile": f"linear-internal-gaps-v1;max_gap={max_gap}",
        "review_status": "technical-candidate; signer review required",
    }


def select(rows: list[dict], labels: set[str], limit: int) -> list[dict]:
    selected = [row for row in rows if not labels or row["gloss"].casefold() in labels]
    selected.sort(key=lambda row: (row["gloss"].casefold(), row["signer_id"], row["video_id"]))
    if limit > 0:
        selected = selected[:limit]
    return selected


def main() -> None:
    global PROFILE, extract_clip
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", default="", help="Comma-separated gloss labels to select")
    parser.add_argument("--limit", type=int, default=0, help="Maximum selected videos; 0 means all matching")
    parser.add_argument("--extract", action="store_true", help="Extract selected videos into compact NPZ files")
    parser.add_argument("--patch-gap", type=int, default=2, choices=range(0, 6), help="Maximum internal gap to interpolate")
    args = parser.parse_args()
    rows = read_metadata()
    labels = {item.strip().casefold() for item in args.labels.split(",") if item.strip()}
    selected = select(rows, labels, args.limit)
    if args.extract and not selected:
        raise ValueError("--extract requires a non-empty selection")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bank = {
        "schema": "clinic-allcam1-keypoint-bank-v2",
        "source": {
            "name": "All_cam1",
            "kind": "local-recognizer-collection",
            "metadata": str(METADATA),
            "metadata_sha256": digest(METADATA),
            "video_root": str(VIDEO_ROOT),
            "video_count": len(rows),
            "label_count": len(inventory(rows)),
        },
        "crosswalk_policy": "All_cam1 video IDs and 400-class model IDs must not be reused as QIPEDC source IDs",
        "runtime_policy": "inventory and candidate keypoints only; explicit signer and motion review required before avatar promotion",
        "inventory": inventory(rows),
        "selection": [],
        "extraction": {
            "requested": bool(args.extract),
            "profile": PROFILE,
            "patch_profile": f"linear-internal-gaps-v1;max_gap={args.patch_gap}",
        },
    }
    if args.extract:
        from motion_extract import PROFILE as extractor_profile, extract_clip as extract

        PROFILE = extractor_profile
        extract_clip = extract
        for index, source in enumerate(selected, 1):
            video = VIDEO_ROOT / f"{source['video_id']}.mp4"
            if not video.is_file():
                bank["selection"].append({**source, "status": "missing_video", "path": str(video)})
                continue
            row = {**source, "path": str(video), "sha256": digest(video)}
            cache = extract_clip(row)
            try:
                result = compact_keypoints(row, cache, OUTPUT / "keypoints", args.patch_gap)
                result["status"] = "ready_for_review"
                bank["selection"].append(result)
                print(f"{index}/{len(selected)} READY {source['gloss']} {source['video_id']}", flush=True)
            except Exception as error:
                bank["selection"].append({**source, "status": "extraction_error", "error": str(error)})
                print(f"{index}/{len(selected)} SKIP {source['gloss']} {source['video_id']}: {error}", flush=True)
    else:
        bank["selection"] = [{**row, "status": "selected_metadata_only"} for row in selected]
    target = OUTPUT / "index.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(bank, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({"videos": len(rows), "labels": len(bank["inventory"]), "selected": len(selected), "output": str(target)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
