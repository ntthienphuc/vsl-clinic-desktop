"""Attach only allowlisted offline narration to the shared sign timeline."""
import json
from pathlib import Path


def load_avatar_voice(assets: Path):
    path = assets / "avatar-voice/manifest.json"
    return {item["id"]: item for item in json.loads(path.read_text(encoding="utf8"))["entries"]} if path.is_file() else {}


def voice_for_clause(clause, glosses, bank):
    key = "p:" + clause["phrase_id"] if clause.get("phrase_id") else (
        "w:" + glosses[clause["gloss_start"]]["id"] if clause["gloss_end"] - clause["gloss_start"] == 1 else "")
    return bank.get(key)


def attach_narration(timing, glosses, bank):
    # Preserve every measured sign stroke. If speech is longer, add a neutral
    # pause after the clause's existing outro, never accelerate a handshape.
    shift, cues, segments = 0, [], []
    original = timing["timeline"]
    for clause in timing["clauses"]:
        old_start, old_end = clause["start_ms"], clause["end_ms"]
        entry = voice_for_clause(clause, glosses, bank)
        for segment in original:
            if old_start <= segment["start_ms"] < old_end:
                segments.append({**segment, "start_ms": segment["start_ms"] + shift, "end_ms": segment["end_ms"] + shift})
        clause["start_ms"] += shift
        clause["end_ms"] += shift
        extra = 0
        if entry:
            start = clause["start_ms"] + 350
            end = start + entry["duration_ms"]
            cues.append({"entry_id": entry["id"], "text": entry["text"], "file": entry["file"],
                         "start_ms": start, "end_ms": end, "duration_ms": entry["duration_ms"]})
            extra = max(0, end + 120 - clause["end_ms"])
            if extra:
                segments.append({"phase": "hold", "start_ms": clause["end_ms"],
                                           "end_ms": clause["end_ms"] + extra, "index": clause["gloss_end"] - 1})
                clause["end_ms"] += extra
        shift += extra
        for segment in original:
            if segment["phase"] == "hold" and segment["start_ms"] == old_end:
                segments.append({**segment, "start_ms": segment["start_ms"] + shift, "end_ms": segment["end_ms"] + shift})
    timing["timeline"] = segments
    timing["total_ms"] += shift
    timing["audio_cues"] = cues
    return timing
