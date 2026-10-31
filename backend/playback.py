"""One serialized playback timeline, shared by the server and avatar renderer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

INTRO_MS = 350
OUTRO_MS = 350
BRIDGE_MS = 280
CLAUSE_GAP_MS = 160


def load_join_profile(assets: Path) -> dict:
    path = assets / "sentence_motion.json"
    if not path.is_file():
        return {}
    profile = json.loads(path.read_text(encoding="utf-8"))
    for identity, window in profile.get("windows", {}).items():
        source = assets / "motions" / f"{identity}.json"
        if hashlib.sha256(source.read_bytes()).hexdigest() != window["motion_sha256"]:
            raise ValueError(f"Sentence motion annotations are stale: {identity}")
        motion = json.loads(source.read_text(encoding="utf-8"))
        count = len(motion["frames"])
        if not 0 <= window["entry_frame"] < window["exit_frame"] < count:
            raise ValueError(f"Invalid sentence motion window: {identity}")
        window["entry_ms"] = motion["duration_ms"] * window["entry_frame"] / (count - 1)
        window["exit_ms"] = motion["duration_ms"] * window["exit_frame"] / (count - 1)
    return profile


def build_timeline(glosses: list[dict], clauses: list[dict], durations: dict[str, float], profile: dict | None = None) -> dict:
    if not glosses:
        raise ValueError("Không có ký hiệu để phát.")
    profile = profile or {}
    windows = profile.get("windows", {})
    joins = {tuple(item["ids"]): item["duration_ms"] for item in profile.get("joins", [])}
    timeline = []
    cues = []
    offset = 0.0

    def append(phase, duration, **values):
        nonlocal offset
        timeline.append({"phase": phase, "start_ms": offset, "end_ms": offset + duration, **values})
        offset += duration

    if not clauses:
        clauses = [{"gloss_start": 0, "gloss_end": len(glosses), "nonmanual": "neutral", "text": ""}]
    cursor = 0
    for clause_index, clause in enumerate(clauses):
        first, end = clause["gloss_start"], clause["gloss_end"]
        if first != cursor or not first < end <= len(glosses):
            raise ValueError("Invalid sentence timeline coverage")
        cursor = end
        cue_start = offset
        append("intro", INTRO_MS, index=first, source_ms=0)
        for index in range(first, end):
            identity = glosses[index]["id"]
            previous = glosses[index - 1]["id"] if index > first else None
            following = glosses[index + 1]["id"] if index + 1 < end else None
            incoming = (previous, identity) in joins
            outgoing = (identity, following) in joins
            source_start = windows[identity]["entry_ms"] if incoming else 0
            source_end = windows[identity]["exit_ms"] if outgoing else durations[identity]
            append("sign", source_end - source_start, index=index, source_start_ms=source_start, source_end_ms=source_end)
            if following is not None:
                target = windows[following]["entry_ms"] if outgoing else 0
                append("bridge", joins.get((identity, following), BRIDGE_MS),
                       index=index + 1, from_index=index, from_ms=source_end, to_ms=target)
        last = end - 1
        append("outro", OUTRO_MS, index=last, source_ms=durations[glosses[last]["id"]])
        cues.append({**clause, "start_ms": cue_start, "end_ms": offset})
        if clause_index + 1 < len(clauses):
            append("hold", CLAUSE_GAP_MS, index=last)
    if cursor != len(glosses):
        raise ValueError("Uncovered signs in sentence timeline")
    return {"timeline": timeline, "clauses": cues, "total_ms": offset, "timeline_schema": "clinic-playback-v2"}
