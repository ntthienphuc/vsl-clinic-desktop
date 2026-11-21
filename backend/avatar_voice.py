"""Speak each signed gloss on the avatar's shared playback clock."""
import json
from pathlib import Path


def load_avatar_voice(assets: Path):
    path = assets / "avatar-voice/manifest.json"
    return {item["id"]: item for item in json.loads(path.read_text(encoding="utf8"))["entries"]} if path.is_file() else {}


def attach_narration(timing, glosses, bank):
    # Word clips follow sign order, including deliberate repetitions. Sentence
    # recordings must not run ahead of (or reorder) the signed instruction.
    original = timing["timeline"]
    segments, cues, extensions = [], [], []
    shift = 0
    for segment in original:
        current = {**segment, "start_ms": segment["start_ms"] + shift,
                   "end_ms": segment["end_ms"] + shift}
        segments.append(current)
        if segment["phase"] != "sign":
            continue
        index = segment["index"]
        entry = bank.get("w:" + glosses[index]["id"])
        if not entry:
            continue
        start = current["start_ms"]
        end = start + entry["duration_ms"]
        cues.append({"entry_id": entry["id"], "text": entry["text"], "file": entry["file"],
                     "gloss_index": index, "start_ms": start, "end_ms": end,
                     "duration_ms": entry["duration_ms"]})
        # Never speed up a measured sign stroke or start the next word early.
        # If needed, hold this sign's final pose while its voice finishes.
        extra = max(0, end + 80 - current["end_ms"])
        if extra:
            segments.append({"phase": "voice_hold", "index": index,
                             "source_ms": segment["source_end_ms"],
                             "start_ms": current["end_ms"], "end_ms": current["end_ms"] + extra})
            extensions.append((segment["end_ms"], extra))
            shift += extra
    for clause in timing["clauses"]:
        for key in ("start_ms", "end_ms"):
            at = clause[key]
            clause[key] += sum(extra for boundary, extra in extensions if boundary <= at)
    timing["timeline"] = segments
    timing["total_ms"] += shift
    timing["audio_cues"] = cues
    timing["narration_mode"] = "per_sign"
    return timing
