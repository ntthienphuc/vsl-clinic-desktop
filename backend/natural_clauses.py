"""Compose Vietnamese clinic clauses from motion-backed semantic slots.

Every consumed word belongs to a subject, predicate, modality, time, question
or a bounded politeness wrapper. Unknown modifiers remain unknown. These rules
describe a pilot signing profile, not a claim of fluent regional VSL grammar.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


class NaturalClauses:
    def __init__(self, words: list[dict]):
        self.words = {normalized(word["label"]): word for word in words}
        # Each value is the signing order, preserving the established avatar
        # profile (object before verb), independently of Vietnamese word order.
        self.predicates = {
            "đau": ("Đau",), "mệt": ("Mệt",), "khỏe": ("Khỏe",),
            "yếu": ("Yếu",), "ốm": ("Ốm",), "sốt": ("Sốt",),
            "lạnh": ("Lạnh",), "nóng": ("Nóng",),
            "đau bụng": ("Bụng", "Đau"), "đau tay": ("Tay", "Đau"),
            "nghỉ ngơi": ("Nghỉ ngơi",), "ngồi nghỉ ngơi": ("Ngồi", "Nghỉ ngơi"),
            "ngồi": ("Ngồi",), "ngủ": ("Ngủ",), "thức dậy": ("Thức dậy",),
            "uống nước": ("Nước", "Uống"), "uống sữa": ("Sữa", "Uống"),
            "ăn cơm": ("Cơm", "Ăn"), "ăn ngon miệng": ("Ăn", "Ngon miệng"),
            "đo nhiệt độ": ("Nhiệt độ", "Đo"), "khám bệnh": ("Khám bệnh",),
            "rửa tay": ("Rửa tay",), "giúp đỡ": ("Giúp đỡ",),
            "gọi y tá": ("Y tá", "Gọi"), "gọi bác sĩ": ("Bác sĩ", "Gọi"),
            "chú ý nghe": ("Chú ý", "Nghe"), "tiếp tục": ("Tiếp tục",),
            "dừng lại": ("Dừng lại",), "đồng ý": ("Đồng ý",),
            "thở": ("Thở",), "cảm ơn": ("Cảm ơn",), "xin lỗi": ("Xin lỗi",),
            "buồn nôn": ("Buồn nôn",), "nằm": ("Nằm",),
            "nằm nghỉ ngơi": ("Nằm", "Nghỉ ngơi"), "nằm trên giường": ("Giường", "Nằm"),
            "đợi": ("Đợi",), "ngồi đợi": ("Ngồi", "Đợi"),
            "đau mắt": ("Đau mắt",), "đau tai": ("Đau tai",),
            "ăn uống": ("Ăn uống",), "băng bó": ("Băng bó",), "tiêm": ("Tiêm",),
            "cấp cứu": ("Cấp cứu",), "gọi cấp cứu": ("Cấp cứu", "Gọi"),
            "đi vệ sinh": ("Nhà vệ sinh", "Đi"), "đi ngủ": ("Ngủ",),
            "đọc": ("Đọc",), "viết": ("Viết",), "xem": ("Xem",),
            "nghe": ("Nghe",), "nói": ("Nói",), "nói chuyện": ("Nói chuyện",),
            "gọi mẹ": ("Mẹ", "Gọi"), "gọi bố": ("Bố", "Gọi"),
            "gọi vợ": ("Vợ", "Gọi"), "gọi chồng": ("Chồng", "Gọi"),
            "viết ra": ("Viết",),
            "đi": ("Đi",), "ăn": ("Ăn",), "uống": ("Uống",),
            "chú ý": ("Chú ý",), "đúng": ("Đúng",), "sai": ("Sai",),
            "rửa mặt": ("Rửa mặt",), "gội đầu": ("Gội đầu",), "tắm rửa": ("Tắm rửa",),
            "ngồi trên ghế": ("Cái ghế", "Ngồi"), "gọi lễ tân": ("Lễ tân", "Gọi"),
            "gọi điện thoại": ("Điện thoại", "Gọi"),
            "gối": ("Gối (đầu)",), "mền": ("Mền",), "điện thoại": ("Điện thoại",),
            "ghế": ("Cái ghế",), "uống nước ấm": ("Nước", "Ấm", "Uống"),
            "yên tĩnh": ("Yên tĩnh",), "từ chối": ("Từ chối",), "thay đổi": ("Thay đổi",),
        }
        self.states = {"đau", "mệt", "khỏe", "yếu", "ốm", "sốt", "lạnh", "nóng", "đau bụng", "đau tay"}
        self.states.update({"buồn nôn", "đau mắt", "đau tai"})
        for place, label in (("bụng", "Bụng"), ("tay", "Tay")):
            for side, side_label in (("trái", "Bên trái"), ("phải", "Bên phải")):
                self.predicates[f"đau {place} bên {side}"] = (label, side_label, "Đau")
                self.states.add(f"đau {place} bên {side}")
        self.aliases = {
            "mệt mỏi": "mệt", "nhức": "đau", "nhức bụng": "đau bụng", "nhức tay": "đau tay",
            "ngồi nghỉ": "ngồi nghỉ ngơi", "nghỉ": "nghỉ ngơi",
            "đo thân nhiệt": "đo nhiệt độ", "kiểm tra thân nhiệt": "đo nhiệt độ",
            "kiểm tra nhiệt độ": "đo nhiệt độ", "ăn có ngon miệng": "ăn ngon miệng",
            "nằm nghỉ": "nằm nghỉ ngơi", "chờ": "đợi", "chờ đợi": "đợi", "ngồi chờ": "ngồi đợi",
            "đau tay trái": "đau tay bên trái", "đau tay phải": "đau tay bên phải",
            "đi nhà vệ sinh": "đi vệ sinh", "vào nhà vệ sinh": "đi vệ sinh",
            "nhức mắt": "đau mắt", "nhức tai": "đau tai",
            "ngồi chờ đợi": "ngồi đợi",
            "gối đầu": "gối", "chăn": "mền", "cái ghế": "ghế",
            "ngồi ghế": "ngồi trên ghế", "tắm": "tắm rửa", "giữ yên tĩnh": "yên tĩnh",
        }
        # After need/want, "được" can express receiving the opportunity for a
        # self-directed activity. It does not change the actor in these frames.
        # Do not apply this to "được khám/đo/giúp": those are passive actions
        # whose recipient would otherwise become the actor.
        self.benefactive_activities = {
            "nghỉ ngơi", "ngồi nghỉ ngơi", "nằm nghỉ ngơi", "ngồi", "nằm",
            "nằm trên giường", "ngủ", "uống nước", "uống sữa", "ăn cơm",
            "đợi", "ngồi đợi",
            "đi vệ sinh", "đi ngủ", "ăn uống", "đọc", "viết", "nói chuyện",
            "rửa mặt", "gội đầu", "tắm rửa", "ngồi trên ghế", "gọi điện thoại", "uống nước ấm",
        }

    def retrieval_entries(self) -> list[dict]:
        texts = ["Bạn cần nghỉ ngơi không?", "Bạn có buồn nôn không?", "Mời bạn nằm trên giường.",
                 "Bạn hãy ngồi đợi.", "Bạn có đau bụng bên trái không?", "Bạn có đau bụng bên phải không?",
                 "Bạn có cần nằm nghỉ ngơi không?", "Bạn muốn uống sữa không?"]
        texts += ["Đồng ý nằm nghỉ ngơi.", "Mời bạn nằm nghỉ nhé.",
                  "Bạn có đau mắt không?", "Bạn có đau tai không?",
                  "Bạn cần đi vệ sinh không?", "Bạn có muốn ăn uống không?",
                  "Bác sĩ băng bó.", "Y tá tiêm.", "Gọi cấp cứu.",
                  "Bạn hãy viết nhé.", "Bạn muốn nói chuyện không?", "Bạn hãy tiếp tục thở nhé."]
        texts += ["Bạn muốn rửa mặt không?", "Bạn có muốn gội đầu không?", "Bạn cần tắm rửa không?",
                  "Bạn cần gối không?", "Bạn có cần chăn không?", "Mời bạn ngồi trên ghế.",
                  "Bạn cần điện thoại không?", "Bạn muốn gọi điện thoại không?", "Gọi lễ tân.",
                  "Bạn có muốn uống nước ấm không?", "Bạn hãy giữ yên tĩnh nhé.",
                  "Bạn có muốn thay đổi không?", "Bạn có muốn từ chối không?"]
        texts += ["Bạn muốn gọi mẹ không?", "Bạn muốn gọi bố không?",
                  "Bạn muốn gọi vợ không?", "Bạn muốn gọi chồng không?", "Mời bạn viết ra."]
        return [entry for text in texts if (entry := self.parse(text)) is not None]

    def parse(self, text: str, inherited_subject: str | None = None) -> dict | None:
        value = normalized(text)
        if not value or re.search(r"[^\w\s,.!?]", value) or re.search(r"[.!?].+|[.!?]{2,}", value):
            return None
        punctuation_question = value.endswith("?")
        value = value.rstrip(".!?").strip()
        # Wrappers are anchored. A meaningful adjective or quantity anywhere
        # inside the predicate cannot be consumed as a generic stop word.
        value = re.sub(r"(?:\s+(?:ạ|nhé|nha|nhá|nhỉ|vậy))+$", "", value)
        value = re.sub(r"\s+(?:giúp tôi|giúp em)(?:\s+với)?$", "", value)
        asking = bool(re.match(r"(?:cho tôi hỏi|cho bác sĩ hỏi)\s+", value))
        value = re.sub(r"^(?:cho tôi hỏi|cho bác sĩ hỏi)\s+", "", value)
        request = bool(re.match(r"(?:(?:xin )?mời|vui lòng|hãy)\s+", value))
        value = re.sub(r"^(?:(?:xin )?mời|vui lòng|hãy)\s+", "", value)
        time = None
        if value.startswith("bây giờ "):
            time, value = "Bây giờ", value[8:]
        elif value.endswith(" bây giờ"):
            time, value = "Bây giờ", value[:-8]
        subject = inherited_subject
        explicit_subject = False
        subject_match = re.match(r"^(bác sĩ|(?:chị |cô )?y tá|bệnh nhân|bạn|anh|chị|cô|chú|bác|em)(?:\s+ơi)?(?:,?\s+)", value)
        if subject_match:
            token = subject_match[1]
            subject = "Y tá" if token.endswith("y tá") else "Bác sĩ" if token == "bác sĩ" else "Bệnh nhân" if token == "bệnh nhân" else "addressee"
            explicit_subject = True
            value = value[subject_match.end():]
        # Vietnamese topic-first symptom questions: "Bụng của chị có đau không?"
        topic = re.fullmatch(r"(bụng|tay)(?:(?: của)? (?:bạn|anh|chị|cô|chú|bác|em))? (?:có )?(?:bị )?(đau|nhức)( không)?", value)
        if topic:
            subject, explicit_subject = "addressee", True
            value = f"đau {topic[1]}" + (" không" if topic[3] else "")
        if value.startswith("hãy "):
            request, value = True, value[4:]
        yes_no = value.endswith(" không")
        if yes_no:
            value = value[:-6]
            if value.startswith("có "):
                value = value[3:]
        elif value.startswith("có "):
            # "có" can indicate possession/existence; do not discard it in
            # affirmative sentences or incomplete questions.
            return None
        wh = None
        for ending in ("vào lúc nào", "lúc nào", "khi nào", "bao giờ", "như thế nào", "thế nào", "ra sao"):
            if value.endswith(" " + ending):
                wh = "Thế nào" if ending in {"như thế nào", "thế nào", "ra sao"} else "Bao giờ"
                value = value[:-(len(ending) + 1)]
                break
        if wh and yes_no or request and (yes_no or wh or punctuation_question):
            return None
        question = yes_no or wh is not None or punctuation_question
        if asking and not question:
            return None
        modal = None
        for marker in ("không cần", "không nên", "đồng ý", "tiếp tục", "cần", "muốn", "nên", "thử"):
            if value.startswith(marker + " "):
                modal, value = marker.capitalize(), value[len(marker) + 1:]
                break
        if value.startswith("được "):
            activity = self.aliases.get(value[5:], value[5:])
            if modal not in {"Cần", "Muốn", "Không cần"} or activity not in self.benefactive_activities:
                return None
            value = activity
        feeling = False
        for marker in ("có cảm giác", "cảm thấy", "cảm giác", "thấy"):
            if value == marker or value.startswith(marker + " "):
                feeling, value = True, value[len(marker):].strip()
                if value.startswith("trong người "):
                    value = value[12:]
                break
        passive = value.startswith("bị ")
        if passive:
            value = value[3:]
        predicate = self.aliases.get(value, value)
        if feeling and not predicate and wh == "Thế nào":
            labels = []
        elif predicate in self.predicates:
            if (feeling or passive) and predicate not in self.states:
                return None
            labels = list(self.predicates[predicate])
        else:
            return None
        if wh == "Thế nào" and not feeling:
            return None
        if wh and modal:
            return None
        prefix = ([time] if time else [])
        if subject and subject != "addressee":
            prefix.append(subject)
        labels = prefix + ([modal] if modal else []) + (["Cảm thấy"] if feeling else []) + labels + ([wh] if wh else [])
        if not labels or any(normalized(label) not in self.words for label in labels):
            return None
        act = "wh_question" if wh else "yes_no_question" if question else "request" if request or modal in {"Nên", "Không nên", "Thử"} else "statement"
        frame = {"subject": subject, "predicate": predicate, "modal": modal, "time": time, "feeling": feeling, "act": act}
        signature = hashlib.sha256(repr(frame).encode("utf8")).hexdigest()[:16]
        return {"id": "natural-" + signature, "text": text, "aliases": [],
                "gloss_ids": [self.words[normalized(label)]["id"] for label in labels],
                "nonmanual": "question" if question else "neutral", "act": act,
                "explanation": "Giữ chủ thể, ý hỏi và thứ tự từng ý; câu gốc hiển thị cùng ký hiệu.",
                "frame": frame, "explicit_subject": explicit_subject, "rule": "natural-clauses-v1"}


def split_clauses(text: str) -> list[tuple[str, str]]:
    """Retain every input character except explicit, ordered clause boundaries."""
    text = re.sub(r"\b(ơi),\s*", r"\1 ", text, flags=re.IGNORECASE)
    pieces = re.split(r"([.!?;\n]+|\s+(?:rồi|sau đó|tiếp theo|và)\s+|,\s*)", text, flags=re.IGNORECASE)
    clauses = []
    connector = ""
    for index in range(0, len(pieces), 2):
        part = pieces[index].strip()
        delimiter = pieces[index + 1] if index + 1 < len(pieces) else ""
        if not part:
            if delimiter or index == 0:
                return []
            continue
        if re.fullmatch(r"[.!?;\n]+", delimiter):
            if len(delimiter.strip()) > 1:
                return []
            part += delimiter if delimiter in ".!?" else ""
        clauses.append((part, connector))
        connector = delimiter.strip().casefold()
    return clauses
