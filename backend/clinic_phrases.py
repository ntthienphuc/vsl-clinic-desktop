"""Frequently used existing, reviewed phrases; no new semantic projection."""

GROUPS = {
    "Khám bệnh": ["doctor-exam", "now-exam", "ask-pain", "ask-abdomen", "ask-hand", "ask-feeling-open"],
    "Điều dưỡng": ["nurse-temperature", "now-temperature", "doctor-temperature", "nurse-help", "wash-hands", "call-nurse"],
    "Hỏi tình trạng": ["ask-fever", "ask-tired", "ask-well", "ask-166", "ask-240", "ask-appetite"],
    "Hướng dẫn & hỗ trợ": ["sit-rest", "drink-water", "need-help", "ask-agree", "call-doctor", "continue"],
}


def quick_phrases(planner):
    entries = {entry["id"]: entry for entry in planner.entries}
    result = []
    for group, ids in GROUPS.items():
        for phrase_id in ids:
            entry = entries[phrase_id]
            result.append(dict(id=phrase_id, text=entry["text"], category=group,
                               supported=planner.plan(entry["text"])["supported"]))
    return result
