"""Explicit demo clauses; never infer a translation by simply dropping unknown words."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "assets/phrases.json"
catalog = json.loads(path.read_text(encoding="utf-8"))
words = json.loads((ROOT / "assets/vocabulary.json").read_text(encoding="utf-8"))
ids = {word["label"]: word["id"] for word in words}
existing = {entry["id"] for entry in catalog["entries"]}


def add(identity, text, labels, act="request", aliases=()):
    if identity in existing:
        return
    catalog["entries"].append({
        "id": identity, "text": text, "aliases": list(aliases),
        "gloss_ids": [ids[label] for label in labels], "act": act,
        "nonmanual": "question" if act == "yes_no_question" else "neutral",
        "explanation": "Mẫu demo: " + " → ".join(labels) + ". Giữ nguyên câu bằng chữ; cần người dùng VSL duyệt cách thể hiện.",
    })


for label in ["Lạnh", "Nóng", "Yếu"]:
    text = f"Bạn có {label.lower()} không?"
    add(f"ask-{ids[label]}", text, [label], "yes_no_question", [text[:-1]])
for labels, text in [
    (["Cần", "Giúp đỡ"], "Bạn có cần giúp đỡ không?"),
    (["Muốn", "Nước", "Uống"], "Bạn muốn uống nước không?"),
    (["Muốn", "Ngủ"], "Bạn muốn ngủ không?"),
    (["Muốn", "Nghỉ ngơi"], "Bạn muốn nghỉ ngơi không?"),
    (["Cảm thấy", "Mệt"], "Bạn có cảm thấy mệt không?"),
]:
    add("question-" + "-".join(ids[label] for label in labels), text, labels, "yes_no_question", [text[:-1]])
for identity, text, labels, aliases in [
    ("wash-hands", "Rửa tay.", ["Rửa tay"], ["Bạn hãy rửa tay", "Hãy rửa tay"]),
    ("listen", "Chú ý nghe.", ["Chú ý", "Nghe"], ["Bạn hãy chú ý nghe"]),
    ("continue", "Tiếp tục.", ["Tiếp tục"], ["Bạn hãy tiếp tục", "Hãy tiếp tục"]),
    ("try-continue", "Thử tiếp tục.", ["Thử", "Tiếp tục"], []),
    ("call-nurse", "Gọi y tá.", ["Y tá", "Gọi"], ["Hãy gọi y tá"]),
    ("call-doctor", "Gọi bác sĩ.", ["Bác sĩ", "Gọi"], ["Hãy gọi bác sĩ"]),
    ("should-rest", "Nên nghỉ ngơi.", ["Nên", "Nghỉ ngơi"], []),
    ("need-help", "Cần giúp đỡ.", ["Cần", "Giúp đỡ"], []),
    ("want-water", "Muốn uống nước.", ["Muốn", "Nước", "Uống"], []),
    ("want-rest", "Muốn nghỉ ngơi.", ["Muốn", "Nghỉ ngơi"], []),
    ("no-need-help", "Không cần giúp đỡ.", ["Không cần", "Giúp đỡ"], []),
    ("now-exam", "Bây giờ bác sĩ khám bệnh.", ["Bây giờ", "Bác sĩ", "Khám bệnh"], []),
    ("now-temperature", "Bây giờ y tá đo nhiệt độ.", ["Bây giờ", "Y tá", "Nhiệt độ", "Đo"], []),
    ("now-rest", "Bây giờ nghỉ ngơi.", ["Bây giờ", "Nghỉ ngơi"], []),
]:
    add(identity, text, labels, aliases=aliases)
for entry in catalog["entries"]:
    if entry["id"] == "drink-water":
        entry["aliases"] = list(dict.fromkeys([*entry["aliases"], "Bạn hãy uống nước", "Hãy uống nước"]))
path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(catalog['entries'])} explicit templates plus subject-predicate combinations")
