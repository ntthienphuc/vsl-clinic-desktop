"""Meaning-preserving planning: vocabulary coverage does not imply sentence grammar."""
from __future__ import annotations

import re
import unicodedata

from .semantic_router import SemanticRouter


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def phrase_key(value: str) -> str:
    return " ".join(normalize(value).strip().rstrip(".! ").split())


def tokens_of(value: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", unicodedata.normalize("NFC", value), re.UNICODE)


class TextPlanner:
    def __init__(self, words: list[dict], catalog: dict | None = None, semantic_bank: dict | None = None):
        self.words = words
        self.phrases = {tuple(normalize(word["label"]).split()): word for word in words}
        self.maximum = max((len(key) for key in self.phrases), default=1)
        self.catalog = catalog or {}
        self.by_id = {word["id"]: word for word in words}
        self.templates = {}
        grammar = self.catalog.get("grammar", {})
        self.vocative_subjects = sorted(
            (subject["text"] for subject in grammar.get("subjects", [])),
            key=lambda value: len(tokens_of(value)),
            reverse=True,
        )
        self.entries = list(self.catalog.get("entries", []))
        for subject in grammar.get("subjects", []):
            for predicate in grammar.get("predicates", []):
                self.entries.append({
                    "id": f"subject-{subject['gloss_id']}-{predicate['id']}",
                    "text": f"{subject['text']} {predicate['text']}.",
                    "aliases": [],
                    "gloss_ids": [subject["gloss_id"], *predicate["gloss_ids"]],
                    "act": "statement",
                    "nonmanual": "neutral",
                    "explanation": predicate["explanation"],
                    "rule": "subject-predicate-v1",
                })
        for entry in self.entries:
            if not entry["gloss_ids"] or any(key not in self.by_id for key in entry["gloss_ids"]):
                raise ValueError("Phrase references an unknown motion")
            for alias in [entry["text"], *entry.get("aliases", [])]:
                key = phrase_key(alias)
                if key in self.templates and self.templates[key]["id"] != entry["id"]:
                    raise ValueError(f"Ambiguous phrase: {alias}")
                self.templates[key] = entry
        self.semantic_router = SemanticRouter(semantic_bank) if semantic_bank else None

    def _semantic_clause(self, value: str) -> str:
        """Remove only approved discourse markers before sign planning.

        Spoken Vietnamese often adds a vocative ``ơi`` and a polite ending
        such as ``nha``. They carry tone, but do not add a sign in this demo.
        The removal is deliberately narrow: meaningful words are left in the
        clause so an unsupported meaning still stops automatic playback.
        """
        semantic = value.strip()
        for subject in self.vocative_subjects:
            pattern = rf"(?<!\w)({re.escape(subject)})\s+ơi\b"
            semantic = re.sub(pattern, r"\1", semantic, count=1, flags=re.IGNORECASE)
        semantic = re.sub(r"\s*,\s*", " ", semantic)
        semantic = re.sub(r"\s+(?:nha|nhé|nhá|ạ)(?=\s*[.!?;]?\s*$)", "", semantic, count=1, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", semantic).strip()

    def suggestions(self, text: str) -> list[dict]:
        return [{"text": item["canonical"], "reason": item["reason"]}
                for item in self.catalog.get("aliases_for_review", [])
                if phrase_key(text) == phrase_key(item["input"])]

    def contextual_candidates(self, predictions: list[dict], question_id: str | None) -> list[dict]:
        entry = next((item for item in self.entries if item["id"] == question_id), None)
        if not entry or entry["act"] != "yes_no_question" or not predictions:
            return []
        expected = set(entry["gloss_ids"])
        threshold = max(0.10, predictions[0]["score"] * 0.5)
        return [{**item, "reason": "Có trong n-best và liên quan câu hỏi vừa gửi; cần đối chiếu."}
                for item in predictions if str(item.get("model_id")) in expected and item["score"] >= threshold]

    def _lexical(self, text: str, token_offset: int = 0) -> tuple[list[dict], list[dict]]:
        tokens = tokens_of(text)
        matches = []
        unsupported = []
        index = 0
        while index < len(tokens):
            found = False
            for size in range(min(self.maximum, len(tokens) - index), 0, -1):
                key = tuple(normalize(token) for token in tokens[index:index + size])
                if key in self.phrases:
                    word = self.phrases[key]
                    matches.append({"id": word["id"], "label": word["label"], "start": token_offset + index, "tokens": size})
                    index += size
                    found = True
                    break
            if not found:
                unsupported.append({"text": tokens[index], "index": token_offset + index})
                index += 1
        return matches, unsupported

    def _plan_raw(self, text: str) -> dict:
        text = text.strip()
        if not text or len(text) > 500:
            raise ValueError("Nhập nội dung, tối đa 500 ký tự.")
        tokens = tokens_of(text)
        if not tokens:
            raise ValueError("Nội dung chưa có từ để hiển thị.")
        # Preserve clause boundaries from typed text and ASR. Never discard a
        # conjunction, negation, number, punctuation operator or unknown clause.
        raw_parts = [match.group() for match in re.finditer(r"[^.!?;\n]+[.!?;\n]*", text)]
        parts = [part.strip() for part in raw_parts]
        clauses = []
        glosses = []
        unsupported = []
        normalized_parts = []
        issues = [] if "".join(raw_parts) == text else [{"text": text, "reason": "unknown_grammar"}]
        token_offset = 0
        covered = 0
        semantic_token_total = 0
        for part in parts:
            content = part.rstrip(";\n ")
            semantic_content = self._semantic_clause(content)
            normalized_parts.append(semantic_content)
            semantic_token_total += len(tokens_of(semantic_content))
            entry = self.templates.get(phrase_key(semantic_content))
            lexical, missing = self._lexical(semantic_content, token_offset)
            symbols = re.findall(r"[^\w\s.!?;’']|_", normalize(semantic_content), re.UNICODE)
            single = len(lexical) == 1 and not missing and not symbols and "?" not in content
            if entry and not symbols:
                selected = [{"id": key, "label": self.by_id[key]["label"], "start": token_offset, "tokens": 0}
                            for key in entry["gloss_ids"]]
                valid = True
                missing = []
                covered += len(tokens_of(semantic_content))
            else:
                selected = lexical
                valid = single
                covered += sum(item["tokens"] for item in lexical)
            start = len(glosses)
            glosses.extend(selected)
            unsupported.extend(missing)
            unsupported.extend({"text": symbol, "index": token_offset} for symbol in symbols)
            if not valid:
                reason = "missing_vocabulary" if missing else "unknown_grammar"
                issues.append({"text": content, "reason": reason})
            clauses.append({
                "text": content, "gloss_start": start, "gloss_end": len(glosses),
                "supported": valid,
                "phrase_id": entry["id"] if entry and valid else None,
                "nonmanual": entry["nonmanual"] if entry and valid else "neutral",
                "act": entry["act"] if entry and valid else "word",
                "explanation": entry["explanation"] if entry and valid else "Một ký hiệu riêng lẻ.",
            })
            token_offset += len(tokens_of(content))
        if len(clauses) > 6 or len(glosses) > 24:
            issues.append({"text": text, "reason": "too_long"})
        supported = bool(clauses) and not issues and not unsupported
        if supported:
            message = clauses[0]["explanation"] if len(clauses) == 1 else "Các câu được thể hiện nối tiếp, giữ thứ tự và nét mặt riêng của từng câu."
        elif any(item["reason"] == "too_long" for item in issues):
            message = "Hãy chia nội dung thành tối đa 6 câu ngắn hoặc 24 ký hiệu mỗi lần gửi."
        elif unsupported:
            message = "Có từ hoặc nội dung chưa hỗ trợ avatar. Hãy sửa nội dung hoặc gửi nguyên văn bằng chữ."
        else:
            message = "Các từ đã có nhưng cấu trúc câu chưa được hỗ trợ. Chọn mẫu câu hoặc gửi nguyên văn bằng chữ."
        return {
            "text": text, "supported": supported, "glosses": glosses,
            "unsupported": unsupported, "issues": issues, "clauses": clauses,
            "coverage": covered / semantic_token_total if semantic_token_total else 0,
            "grammar_supported": not issues,
            "normalized_text": " ".join(part for part in normalized_parts if part),
            "projection": [item["label"] for item in glosses],
            "mode": "phrase" if any(item["phrase_id"] for item in clauses) else "word",
            "nonmanual": clauses[0]["nonmanual"] if len(clauses) == 1 else "neutral",
            "act": clauses[0]["act"] if len(clauses) == 1 else "sentences",
            "phrase_id": clauses[-1]["phrase_id"] if clauses else None,
            "suggestions": self.suggestions(text) if not supported else [],
            "message": message,
            "regional_review": self.catalog.get("regional_review"),
        }

    def plan(self, text: str) -> dict:
        """Plan text, optionally through the finite semantic bank first.

        A safe semantic match is only accepted after its canonical phrase has
        passed the ordinary phrase planner.  A review-only match is surfaced as
        an explicit suggestion and remains blocked from automatic playback.
        """
        raw = self._plan_raw(text)
        # Fully covered, reviewed clauses take precedence over a partial alias
        # candidate. Otherwise one "uống nước" match can invalidate an entire
        # valid three-sentence message and propose dropping the other clauses.
        if raw["supported"] or not self.semantic_router:
            return raw
        semantic = self.semantic_router.resolve(text, set(self.templates))
        if not semantic:
            return raw
        canonical = semantic["canonical_text"]
        canonical_plan = self._plan_raw(canonical)
        if semantic["decision"] == "auto" and canonical_plan["supported"]:
            result = dict(canonical_plan)
            result["text"] = text
            result["semantic"] = {
                **semantic,
                "applied": True,
                "candidate_projection": canonical_plan["projection"],
            }
            result["message"] = semantic["message"]
            return result
        result = raw
        result["semantic"] = {
            **semantic,
            "applied": False,
            "candidate_projection": canonical_plan["projection"],
        }
        # The raw lexical pass cannot know multiword semantic aliases, so it
        # may split a recognized alias into misleading missing tokens.  The
        # semantic bank is the reviewed source of truth for this review path.
        result["unsupported"] = list(semantic["unmatched"])
        result["supported"] = False
        result["grammar_supported"] = False
        result["issues"] = [*result["issues"], {"text": text, "reason": "semantic_review"}]
        result["suggestions"] = [{"text": canonical, "reason": semantic["explanation"]}]
        result["message"] = semantic["message"]
        return result
