"""Import an explicit small QIPEDC selection without changing the 400 model labels."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import numpy as np

from build_reference_bank import build_word
from motion_extract import ROOT, extract_clip


SELECTION = {
    "W00362": "Bụng",
    "W03090": "Tay",
    "W03008": "Sốt",
    "W02400N": "Ngồi",
    "W01227": "Đo",
    "W01298": "Nhiệt độ",
    "W00884": "Cơm",
    "W03305": "Thở",
    "W00248": "Bệnh nhân",
}

# Reviewed against the unchanged source video. W00248 demonstrates the same
# sign again after turning sideways; that second take must not enter one motion.
REVIEWED_WINDOWS = {
    "W00248": (1500, 4200, "front-facing take only; side-view repetition excluded after visual review"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dictionary", type=Path, required=True)
    args = parser.parse_args()
    dictionary = {row["_id"]: row for row in read(args.dictionary)}
    with (ROOT / "assets/gloss.csv").open(encoding="utf-8", newline="") as handle:
        model_labels = {label.casefold(): int(identity) for identity, label in csv.reader(handle)}
    original_words = read(ROOT / "assets/vocabulary.json")
    bank = read(ROOT / "assets/motions/manifest.json")
    sources_path = ROOT / "research/qipedc-sources.json"
    old_sources = {word["id"]: word for word in read(sources_path)["words"]} if sources_path.exists() else {}
    selected = []
    entries = []
    for code, label in SELECTION.items():
        if label.casefold() in model_labels:
            raise ValueError(f"Use local consensus references for model label {label}")
        row = dictionary[code]
        if row["word"].casefold() != label.casefold():
            raise ValueError(f"Dictionary sense mismatch for {code}")
        identity = "qipedc-" + code
        path = ROOT / "assets/reference-source/qipedc" / f"{code}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        downloaded_at = old_sources.get(identity, {}).get("downloaded_at")
        if not path.exists():
            request = urllib.request.Request(row["video_url"], headers={"User-Agent": "VSL-Clinic-Local-Reference/0.2.1"})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read(30 * 1024 * 1024 + 1)
            if len(data) > 30 * 1024 * 1024 or b"ftyp" not in data[:64]:
                raise ValueError(f"Invalid MP4 download: {code}")
            path.write_bytes(data)
            downloaded_at = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if identity in old_sources and old_sources[identity]["references"][0]["sha256"] != digest:
            raise ValueError(f"Downloaded reference changed: {code}")
        source = {"video_id": identity, "signer_id": "qipedc-unknown-" + code,
                  "path": str(path), "sha256": digest, "url": row["video_url"]}
        word = {"id": identity, "label": label, "model_id": None, "category": "Khám bệnh",
                "demo": None, "source_kind": "qipedc-single", "source_id": code,
                "source_url": row["video_url"], "description": row.get("description", ""),
                "downloaded_at": downloaded_at, "references": [source]}
        cache = extract_clip(source)
        with np.load(cache, allow_pickle=False) as data:
            visible = np.flatnonzero(np.max(data["confidence"][:, [33, 54]], axis=1) > 0.5)
            if len(visible) < 8:
                raise ValueError(f"Too few observed hand frames: {code}")
            times = data["time_ms"]
            source["source_window_ms"] = [max(0, float(times[visible[0]]) - 400),
                                           min(float(times[-1]), float(times[visible[-1]]) + 400)]
            source["window_method"] = "first-to-last observed hand plus 400ms; original video retained for review"
            if code in REVIEWED_WINDOWS:
                start, end, reason = REVIEWED_WINDOWS[code]
                if not 0 <= start < end <= float(times[-1]):
                    raise ValueError(f"Reviewed source window outside video: {code}")
                source["source_window_ms"] = [start, end]
                source["window_method"] = reason
        entry = build_word(word, ROOT / "assets/motions")
        entries.append(entry)
        selected.append(word)
        print(f"IMPORTED {label}: single reference, {entry['duration_ms']} ms, imputed={entry['imputed_fraction']:.3f}", flush=True)
        # Checkpoint provenance before the next network/MediaPipe operation.
        checkpoint = {**old_sources, **{item["id"]: item for item in selected}}
        write(sources_path, {"schema": "clinic-qipedc-sources-v1", "words": list(checkpoint.values()),
                            "scope": "Local demo. Single videos, not a multi-signer average. Fluent review pending."})
    ids = {word["id"] for word in selected}
    vocabulary = [word for word in original_words if word["id"] not in ids]
    vocabulary.extend({key: value for key, value in word.items() if key not in {"references", "downloaded_at", "description"}} for word in selected)
    bank["entries"] = [entry for entry in bank["entries"] if entry["id"] not in ids] + entries
    bank["method"] = "local-consensus-plus-explicit-qipedc-single-v1"
    write(ROOT / "assets/vocabulary.json", vocabulary)
    write(ROOT / "assets/motions/manifest.json", bank)
    write(ROOT / "assets/qipedc-provenance.json", {
        "source": "QIPEDC, Ministry of Education and Training, Vietnam",
        "dictionary_url": "https://qipedc.moet.gov.vn/dictionary",
        "source_kind": "single reference per word; no consensus claim",
        "scope": "Downloaded on user request for local demo. Original video redistribution is not part of this package.",
        "entries": [{"id": word["id"], "label": word["label"], "source_id": word["source_id"],
                     "url": word["source_url"], "description": word["description"],
                     "sha256": word["references"][0]["sha256"], "downloaded_at": word["downloaded_at"],
                     "source_window_ms": word["references"][0]["source_window_ms"],
                     "window_method": word["references"][0]["window_method"]} for word in selected],
    })
    print(f"Bank ready: {len(vocabulary)} words; original 400-label recognizer unchanged.")


if __name__ == "__main__":
    main()
