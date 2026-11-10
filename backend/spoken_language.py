"""Anchored conversational variants of existing clinic phrases.

Only complete clauses match. Clinical modifiers are never removed by a global
stop-word list. These are pilot language rules, not a fluent-signer certification.
"""
from __future__ import annotations

import re
import unicodedata


PERSON = r"(?:bạn|anh|chị|cô|chú|bác)"
PREFIX = r"(?:(?:cho tôi hỏi|cho bác sĩ hỏi)\s+)?"
SUFFIX = r"(?:\s+(?:ạ|nhé|nha))?"


def spoken_variant(text: str) -> dict | None:
    value = unicodedata.normalize("NFC", text).casefold().strip().rstrip(".!? ")
    value = re.sub(r"\s+", " ", value)
    variants: list[tuple[str, str]] = []
    for symptom in ("đau", "đau bụng", "đau tay", "sốt", "mệt", "khỏe", "lạnh", "nóng", "yếu"):
        variants.append((rf"{PERSON} (?:có )?(?:bị )?{symptom} (?:không|không ạ)", f"Bạn có {symptom} không?"))
    for symptom in ("mệt", "yếu"):
        variants.append((rf"{PERSON} (?:có )?(?:cảm thấy|thấy) {symptom} không", f"Bạn có cảm thấy {symptom} không?"))
    variants.extend([
        (rf"{PERSON} (?:cảm thấy|thấy)(?: trong người)? (?:thế nào|như thế nào|ra sao)", "Bạn cảm thấy thế nào?"),
        (rf"{PERSON} (?:có )?ăn (?:có )?ngon miệng không", "Bạn có ăn ngon miệng không?"),
        (rf"{PERSON} (?:có )?cần giúp đỡ không", "Bạn có cần giúp đỡ không?"),
    ])
    for action in ("uống nước", "ngủ", "nghỉ ngơi"):
        variants.append((rf"{PERSON} (?:có )?muốn {action} không", f"Bạn muốn {action} không?"))
    for action, canonical in (("đau bụng", "Bạn đau bụng vào lúc nào?"), ("ngủ", "Bạn ngủ vào lúc nào?"), ("thức dậy", "Bạn thức dậy vào lúc nào?")):
        variants.append((rf"{PERSON} {action} (?:vào )?(?:lúc nào|khi nào|bao giờ)", canonical))
    for action, canonical in (("uống nước", "Uống nước."), ("ngồi nghỉ", "Ngồi nghỉ ngơi."), ("ngồi nghỉ ngơi", "Ngồi nghỉ ngơi."), ("rửa tay", "Rửa tay."), ("chú ý nghe", "Chú ý nghe."), ("tiếp tục", "Tiếp tục.")):
        variants.append((rf"(?:{PERSON} (?:hãy )?|hãy |vui lòng |(?:xin )?mời (?:{PERSON} )?)?{action}", canonical))
    for index, (pattern, canonical) in enumerate(variants):
        question = canonical.endswith("?")
        prefix = PREFIX if question else ""
        suffix = r"(?:\s+(?:ạ|nhé|nha|vậy|nhỉ))?" if question else SUFFIX
        if re.fullmatch(prefix + pattern + suffix, value):
            return {
                "rule_id": f"spoken-clause-v1-{index}", "canonical_text": canonical,
                "intent": "conversational_variant", "confidence": 1.0,
                "risk": "safe", "source": "anchored-clinic-variants-v1",
                "explanation": "Cùng ý hỏi hoặc yêu cầu với một mẫu đã có ký hiệu; giữ nguyên câu gốc.",
                "matched": [{"text": text, "concept": "whole_clause", "start": 0, "end": len(value.split())}],
                "omitted": [], "unmatched": [], "input_text": text,
                "decision": "auto", "message": "Đã tìm được mẫu cùng ý. Câu gốc vẫn hiển thị để đối chiếu.",
            }
    return None
