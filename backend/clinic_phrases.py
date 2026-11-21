"""Present supported phrases by the doctor's task; signing semantics stay in the planner."""
import re

GROUPS = {
    "Khám bệnh": ["doctor-exam", "now-exam", "ask-pain", "ask-abdomen", "ask-hand", "ask-feeling-open"],
    "Điều dưỡng": ["nurse-temperature", "now-temperature", "doctor-temperature", "nurse-help", "wash-hands", "call-nurse"],
    "Hỏi tình trạng": ["ask-fever", "ask-tired", "ask-well", "ask-166", "ask-240", "ask-appetite"],
    "Hướng dẫn & hỗ trợ": ["sit-rest", "drink-water", "need-help", "ask-agree", "call-doctor", "continue"],
}


TASK_GROUPS = ("Hỏi triệu chứng", "Khám và đo", "Chăm sóc", "Nhu cầu hằng ngày", "Hướng dẫn", "Giao tiếp")


def phrase_category(text):
    text = text.casefold()
    if re.search(r"đau|sốt|mệt|khỏe|lạnh|nóng|buồn nôn|cảm thấy|yếu|ngon miệng", text):
        return "Hỏi triệu chứng"
    if re.search(r"khám|đo |nhiệt độ", text):
        return "Khám và đo"
    if re.search(r"băng bó|tiêm|cấp cứu|rửa|gội|vệ sinh cá nhân|súc miệng|vết thương|khẩu trang", text):
        return "Chăm sóc"
    if re.search(r"ăn|uống|ngủ|nghỉ|nằm|giường|gối|chăn|mền|vệ sinh|sữa|khát", text):
        return "Nhu cầu hằng ngày"
    if re.search(r"ngồi|đợi|tiếp tục|dừng|thở|đi|thử|bên trái|bên phải|giơ tay|nhắm mắt", text):
        return "Hướng dẫn"
    return "Giao tiếp"


def quick_phrases(planner):
    entries = {entry["id"]: entry for entry in planner.entries}
    ordered = []
    for ids in GROUPS.values():
        for phrase_id in ids:
            ordered.append(entries[phrase_id])
    # General grammar also allows sentences such as "Bác sĩ uống nước".
    # The quick library contains only the explicitly selected clinical tasks.
    ordered += planner.natural.retrieval_entries()
    seen, result = set(), []
    for entry in ordered:
        key = entry["text"].casefold().rstrip(".?! ")
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(id=entry["id"], text=entry["text"], category=phrase_category(entry["text"]),
                           supported=planner.plan(entry["text"])["supported"]))
    return sorted(result, key=lambda row: TASK_GROUPS.index(row["category"]))
