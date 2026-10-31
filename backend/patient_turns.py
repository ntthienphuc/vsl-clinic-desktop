"""Incremental patient words with a separate, non-blocking turn endpoint."""
from __future__ import annotations

import uuid


TURN_PAUSE_MS = 1500


def paraphrase(words: list[dict]) -> dict:
    """Conservative local grammar. Never replace an n-best label or add a symptom."""
    labels = [word["text"] for word in words]
    raw = " · ".join(labels)
    if any(word.get("uncertain") for word in words):
        return {"text": raw, "rewritten": False, "rule": "uncertain-verbatim"}
    keys = tuple(label.casefold() for label in labels)
    exact = {
        ("cần", "giúp đỡ"): "Cần giúp đỡ.",
        ("muốn", "uống", "nước"): "Muốn uống nước.",
        ("uống", "nước", "muốn"): "Muốn uống nước.",
        ("cần", "nghỉ ngơi"): "Cần nghỉ ngơi.",
        ("nghỉ ngơi", "cần"): "Cần nghỉ ngơi.",
        ("bụng", "đau"): "Đau bụng.",
        ("đau", "bụng"): "Đau bụng.",
        ("tay", "đau"): "Đau tay.",
        ("đau", "tay"): "Đau tay.",
        ("nhiệt độ", "đo"): "Đo nhiệt độ.",
        ("đo", "nhiệt độ"): "Đo nhiệt độ.",
        ("cơm", "ăn"): "Ăn cơm.",
        ("ăn", "cơm"): "Ăn cơm.",
    }
    symptoms = {"đau", "mệt", "lạnh", "nóng", "ốm", "yếu"}
    if keys in exact:
        return {"text": exact[keys], "rewritten": True, "rule": "reviewed-short-request-v1"}
    if 1 < len(keys) <= 4 and len(set(keys)) == len(keys) and all(key in symptoms for key in keys):
        text = ", ".join(labels[:-1]) + " và " + labels[-1].lower() + "."
        return {"text": text, "rewritten": True, "rule": "symptom-conjunction-v1"}
    return {"text": raw, "rewritten": False, "rule": "verbatim"}


class PatientTurns:
    def __init__(self):
        self.current = None
        self.last_activity_ms = 0.0

    def activity(self, now: float):
        self.last_activity_ms = now

    def append(self, word: dict, now: float) -> dict:
        if self.current and len(self.current["words"]) >= 128:
            self.finish(now, "continued_in_next_turn")
        if self.current is None:
            self.current = {"id": uuid.uuid4().hex[:12], "role": "patient", "kind": "patient_turn",
                            "created_at_ms": now, "status": "streaming", "words": [], "text": ""}
        self.current["words"].append(word)
        word["turn_id"] = self.current["id"]
        self.current["text"] = " · ".join(item["text"] for item in self.current["words"])
        self.current["uncertain"] = any(item.get("uncertain") for item in self.current["words"])
        self.current["updated_at_ms"] = now
        self.last_activity_ms = now
        return self.current

    def finish(self, now: float, reason: str = "pause") -> dict | None:
        turn = self.current
        if turn is None:
            return None
        turn["status"] = "candidate"
        turn["ended_at_ms"] = now
        turn["end_reason"] = reason
        turn["raw_text"] = " · ".join(item["text"] for item in turn["words"])
        turn["reading"] = paraphrase(turn["words"])
        turn["text"] = turn["reading"]["text"]
        self.current = None
        return turn

    def tick(self, now: float, capture: dict) -> bool:
        if self.current is None or capture.get("status") in {"signing", "starting"}:
            return False
        if capture.get("inflight_segments", 0) or capture.get("queued_segments", 0):
            return False
        if now - self.last_activity_ms < TURN_PAUSE_MS:
            return False
        return self.finish(now) is not None
