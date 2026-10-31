"""Build a DTW-aligned, provenance-bearing consensus motion bank from local videos."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import warnings

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation

from motion_extract import PROFILE, ROOT, extract_clip


LENGTH = 72
FEATURES = [0, 11, 12, 13, 14, 15, 16, 33, 37, 41, 45, 49, 53, 54, 58, 62, 66, 70, 74]
PARENTS = [0, 0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19]


def resample(values: np.ndarray, times: np.ndarray, target: np.ndarray) -> np.ndarray:
    flat = values.reshape(len(values), -1)
    output = np.full((len(target), flat.shape[1]), np.nan, np.float32)
    for column in range(flat.shape[1]):
        good = np.isfinite(flat[:, column])
        if good.sum() >= 2:
            output[:, column] = np.interp(target, times[good], flat[good, column])
    return output.reshape((len(target),) + values.shape[1:])


def load_sequence(row: dict) -> dict:
    path = ROOT / "research/cache" / f"{row['video_id']}-{PROFILE}.npz"
    with np.load(path, allow_pickle=False) as data:
        xyz = data["xyz"].copy()
        xy = data["xy"].copy()
        confidence = data["confidence"].copy()
        times = data["time_ms"].copy()
    if "source_window_ms" in row:
        start, end = row["source_window_ms"]
        keep = (times >= start) & (times <= end)
        xyz, xy, confidence, times = xyz[keep], xy[keep], confidence[keep], times[keep]
    if len(times) < 8 or not np.all(np.diff(times) > 0):
        raise ValueError("Invalid source clock")
    body_coverage = float(np.mean(confidence[:, [11, 12, 13, 14, 15, 16]] >= 0.5))
    hand_coverages = [float(np.mean(confidence[:, index] > 0.5)) for index in (33, 54)]
    if body_coverage < 0.75 or max(hand_coverages) < 0.40:
        raise ValueError(f"Insufficient tracking body={body_coverage:.2f}, hands={hand_coverages}")
    xyz[confidence < 0.4] = np.nan
    xy[confidence < 0.4] = np.nan
    target = np.linspace(times[0], times[-1], LENGTH)
    # Interpolated geometry and observation support remain separate.
    geometry = resample(xyz, times, target)
    features = resample(xy, times, target)
    nearest = np.abs(times[:, None] - target[None]).argmin(axis=0)
    support = confidence[nearest]
    quality = 0.45 * body_coverage + 0.55 * max(hand_coverages)
    return {"row": row, "xyz": geometry, "xy": features, "support": support,
            "duration_ms": float(times[-1] - times[0]), "quality": quality,
            "body_coverage": body_coverage, "hand_coverage": hand_coverages}


def align_path(a: np.ndarray, b: np.ndarray, band: int = 15) -> tuple[float, list[tuple[int, int]]]:
    """One monotone path shared by all joints, never a per-finger alignment."""
    a = a[:, FEATURES]
    b = b[:, FEATURES]
    n, m = len(a), len(b)
    cost = np.full((n + 1, m + 1), np.inf)
    previous = np.zeros((n, m), np.int8)
    cost[0, 0] = 0
    for i in range(n):
        for j in range(max(0, i - band), min(m, i + band + 1)):
            valid = np.isfinite(a[i]).all(axis=1) & np.isfinite(b[j]).all(axis=1)
            distance = float(np.mean(np.minimum(np.linalg.norm(a[i, valid] - b[j, valid], axis=1), 2.0))) if valid.any() else 2.0
            choices = (cost[i, j], cost[i, j + 1] + 0.015, cost[i + 1, j] + 0.015)
            direction = int(np.argmin(choices))
            previous[i, j] = direction
            cost[i + 1, j + 1] = distance + choices[direction]
    i, j = n - 1, m - 1
    path = []
    while i >= 0 and j >= 0:
        path.append((i, j))
        direction = previous[i, j]
        if direction == 0:
            i -= 1
            j -= 1
        elif direction == 1:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return float(cost[n, m] / len(path)), path


def warp(sequence: dict, path: list[tuple[int, int]], key: str) -> np.ndarray:
    values = sequence[key]
    result = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for index in range(LENGTH):
            indexes = [j for i, j in path if i == index]
            result.append(np.nanmean(values[indexes], axis=0))
    return np.stack(result)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    valid = np.isfinite(values)
    w = weights.reshape((-1,) + (1,) * (values.ndim - 1)) * valid
    total = w.sum(axis=0)
    return np.divide(np.nansum(values * w, axis=0), total, out=np.full(values.shape[1:], np.nan), where=total > 1e-8)


def canonical_hands(average: np.ndarray, aligned: np.ndarray, weights: np.ndarray) -> np.ndarray:
    result = average.copy()
    for start, wrist in ((33, 15), (54, 16)):
        result[:, start] = result[:, wrist]
        # Average hand shape in the palm's own frame. Averaging directions in
        # world space mixes palm rotation with finger articulation, especially
        # when different signers rotate their wrists at slightly different times.
        hands = aligned[:, :, start:start + 21]
        along = hands[:, :, 9] - hands[:, :, 0]
        across = hands[:, :, 5] - hands[:, :, 17]
        along /= np.maximum(np.linalg.norm(along, axis=-1, keepdims=True), 1e-8)
        across -= along * np.sum(across * along, axis=-1, keepdims=True)
        across /= np.maximum(np.linalg.norm(across, axis=-1, keepdims=True), 1e-8)
        normal = np.cross(across, along)
        frames = np.stack([across, along, normal], axis=-1)
        valid = np.isfinite(frames).all(axis=(-2, -1)) & (np.linalg.norm(normal, axis=-1) > .9)
        # Quaternion chordal mean is invariant to the q / -q representation.
        palm_frames = []
        for phase in range(LENGTH):
            available = valid[:, phase]
            if available.any():
                palm_frames.append(Rotation.from_matrix(frames[available, phase]).mean(weights[available]).as_matrix())
            else:
                palm_frames.append(np.full((3, 3), np.nan))
        palm_frames = np.stack(palm_frames)
        grid = np.arange(LENGTH, dtype=float)
        palm_frames = resample(palm_frames, grid, grid)
        # Project interpolated matrices back to SO(3), never use a scaled basis.
        for phase in range(LENGTH):
            if np.isfinite(palm_frames[phase]).all():
                u, _, vh = np.linalg.svd(palm_frames[phase])
                correction = np.eye(3)
                correction[2, 2] = np.linalg.det(u @ vh)
                palm_frames[phase] = u @ correction @ vh
        for child in range(1, 21):
            parent = PARENTS[child]
            directions = aligned[:, :, start + child] - aligned[:, :, start + parent]
            lengths = np.linalg.norm(directions, axis=-1)
            unit = directions / np.maximum(lengths[..., None], 1e-6)
            local = np.einsum('ntji,ntj->nti', frames, unit)
            local[~valid] = np.nan
            average_direction = weighted_mean(local, weights)
            average_direction = resample(average_direction, grid, grid)
            average_direction = gaussian_filter1d(average_direction, sigma=0.65, axis=0, mode="nearest")
            average_direction = np.einsum('tij,tj->ti', palm_frames, average_direction)
            norms = np.linalg.norm(average_direction, axis=-1, keepdims=True)
            length = float(np.nanmedian(lengths))
            if not np.isfinite(length):
                continue
            result[:, start + child] = result[:, start + parent] + average_direction / np.maximum(norms, 1e-6) * length
    return result


def build_word(word: dict, output: Path) -> dict:
    accepted = []
    excluded = []
    for row in word["references"]:
        try:
            accepted.append(load_sequence(row))
        except (ValueError, FileNotFoundError) as error:
            excluded.append({"video_id": row["video_id"], "reason": str(error)})
    # Prefer one well-tracked recording per declared signer to avoid overweighting repeats.
    selected = []
    for signer in sorted({item["row"]["signer_id"] for item in accepted}):
        selected.append(max((item for item in accepted if item["row"]["signer_id"] == signer), key=lambda item: item["quality"]))
    single_reference = word.get("source_kind") == "qipedc-single"
    minimum = 1 if single_reference else 3
    if len(selected) < minimum or (single_reference and len(selected) != 1):
        raise ValueError(f"{word['label']}: only {len(selected)} usable source groups")
    distances = np.zeros((len(selected), len(selected)))
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            distance, _ = align_path(selected[i]["xy"], selected[j]["xy"])
            distances[i, j] = distance
            distances[j, i] = distance
    medoid = int(np.argmin(distances.mean(axis=1)))
    template = selected[medoid]
    paths = [align_path(template["xy"], item["xy"])[1] for item in selected]
    aligned = np.stack([warp(item, path, "xyz") for item, path in zip(selected, paths)])
    support = np.stack([warp(item, path, "support") for item, path in zip(selected, paths)])
    # Geometry interpolated across tracking gaps must not count as an observation
    # when combining independent references.
    aligned[support < 0.4] = np.nan
    widths = max(float(np.median(distances[medoid])), 0.05)
    weights = np.exp(-distances[medoid] / (2 * widths)) * np.asarray([item["quality"] for item in selected])
    weights /= weights.sum()
    geometry = weighted_mean(aligned, weights)
    confidence = weighted_mean(support, weights)
    imputed = ~np.isfinite(geometry).all(axis=-1) | (confidence < 0.4)
    grid = np.arange(LENGTH, dtype=float)
    geometry = resample(geometry, grid, grid)
    geometry = gaussian_filter1d(geometry, sigma=0.65, axis=0, mode="nearest")
    # Reconstruct finger chains after filtering so smoothing cannot shorten bones.
    geometry = canonical_hands(geometry, aligned, weights)
    # Missing inactive hand is explicitly neutral, not a fabricated observed hand.
    neutral_hand = np.array([
        [0, 0, 0], [.05, -.03, .01], [.10, -.08, .02], [.13, -.13, .03], [.15, -.18, .04],
        [.06, -.16, 0], [.07, -.25, .01], [.07, -.31, .02], [.07, -.36, .03],
        [0, -.18, 0], [0, -.28, .01], [0, -.35, .02], [0, -.40, .03],
        [-.05, -.17, 0], [-.06, -.26, .01], [-.06, -.32, .02], [-.06, -.37, .03],
        [-.10, -.14, 0], [-.12, -.21, .01], [-.12, -.26, .02], [-.12, -.30, .03],
    ])
    imputed |= ~np.isfinite(geometry).all(axis=-1)
    for start, wrist, sign in ((33, 15, 1), (54, 16, -1)):
        neutral = neutral_hand * np.array([sign, 1, 1])
        fallback = geometry[:, wrist, None] + neutral[None]
        missing = ~np.isfinite(geometry[:, start:start + 21]).all(axis=-1)
        geometry[:, start:start + 21][missing] = fallback[missing]
    # Unused face/leg points can be absent; wrists/shoulders/hands must be finite.
    required = [0, 11, 12, 13, 14, 15, 16] + list(range(33, 75))
    if not np.isfinite(geometry[:, required]).all():
        raise ValueError(f"{word['label']}: missing required geometry after consensus")
    geometry = np.nan_to_num(geometry)
    duration = int(round(np.median([item["duration_ms"] for item in selected])))
    result = {
        "schema": "clinic-motion-v1", "profile": PROFILE,
        "synthesis_profile": "palm-local-single-v1" if single_reference else "palm-local-consensus-v2",
        "source_kind": "qipedc-single" if single_reference else "local-consensus",
        "id": word["id"], "label": word["label"],
        "duration_ms": duration, "frame_count": LENGTH,
        "coordinates": "shoulder-centered, shoulder-width units; x right, y up, z toward viewer; no mirror",
        "joint_layout": "pose33 + anatomical-left-hand21 + anatomical-right-hand21",
        "frames": np.round(geometry, 5).tolist(),
        "confidence": np.round(confidence, 3).tolist(),
        "imputed": imputed.astype(int).tolist(),
        "reference_ids": [item["row"]["video_id"] for item in selected],
        "source_hashes": [item["row"]["sha256"] for item in selected],
        "source_windows_ms": [item["row"].get("source_window_ms") for item in selected],
        "declared_signers": [item["row"]["signer_id"] for item in selected],
        "medoid_id": template["row"]["video_id"], "consensus_weights": np.round(weights, 5).tolist(),
        "pairwise_dtw_cost": np.round(distances, 5).tolist(),
        "alignment_paths": paths,
        "reference_quality": [{key: item[key] for key in ("quality", "body_coverage", "hand_coverage")} for item in selected],
        "excluded": excluded,
        "review_status": "technical-demo; naturalness and sign intelligibility require fluent VSL review",
    }
    (output / f"{word['id']}.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    exemplar = {"id": word["id"], "frames": np.round(np.nan_to_num(template["xyz"]), 5).tolist(), "duration_ms": int(template["duration_ms"]), "source_id": template["row"]["video_id"]}
    (ROOT / "research" / f"medoid-{word['id']}.json").write_text(json.dumps(exemplar, ensure_ascii=False), encoding="utf-8")
    return {"id": word["id"], "label": word["label"], "source_kind": result["source_kind"], "path": f"/assets/motions/{word['id']}.json",
            "reference_count": len(selected), "medoid_id": result["medoid_id"], "duration_ms": duration,
            "imputed_fraction": float(imputed[:, required].mean()), "sha256": __import__("hashlib").sha256((output / f"{word['id']}.json").read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--word", default=None)
    parser.add_argument("--skip-extraction", action="store_true")
    parser.add_argument("--only-missing", action="store_true", help="Preserve reviewed existing motion bytes during vocabulary expansion")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "research/source-manifest.json").read_text(encoding="utf-8"))
    words = [word for word in manifest["words"] if args.word is None or word["label"] == args.word]
    if args.only_missing:
        words = [word for word in words if not (ROOT / "assets/motions" / f"{word['id']}.json").is_file()]
        if not words:
            print("All selected motions already exist; reviewed files retained.")
            return
    if not words:
        raise ValueError("No matching reference word; existing bank retained")
    rows = [row for word in words for row in word["references"]]
    errors = []
    if not args.skip_extraction:
        with ProcessPoolExecutor(max_workers=max(1, min(4, args.workers))) as pool:
            jobs = {pool.submit(extract_clip, row): row for row in rows}
            for number, future in enumerate(as_completed(jobs), 1):
                row = jobs[future]
                try:
                    future.result()
                    print(f"EXTRACT {number}/{len(rows)} {row['video_id']}", flush=True)
                except Exception as error:
                    errors.append({"video_id": row["video_id"], "error": str(error)})
                    print(f"EXCLUDED {row['video_id']} {error}", flush=True)
    output = ROOT / "assets/motions"
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for word in words:
        entry = build_word(word, output)
        entries.append(entry)
        print(f"BANK {word['label']} refs={entry['reference_count']} imputed={entry['imputed_fraction']:.3f}", flush=True)
    manifest_path = output / "manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    updated_ids = {entry["id"] for entry in entries}
    combined = [entry for entry in previous.get("entries", []) if entry["id"] not in updated_ids] + entries
    method = "local-consensus-plus-explicit-qipedc-single-v1" if any(entry.get("source_kind") == "qipedc-single" for entry in combined) else "shared-band-DTW-medoid-weighted-palm-local-consensus-v2"
    manifest_path.write_text(json.dumps({"schema": "clinic-bank-v1", "method": method, "entries": combined, "extraction_errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
