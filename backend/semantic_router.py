"""Constrained spoken-Vietnamese routing for the doctor-to-patient flow.

The router deliberately does not generate gloss IDs.  It recognizes a reviewed
intent, removes only reviewed discourse markers, and returns a canonical phrase
that the existing TextPlanner must still validate.  This keeps the language
layer useful without allowing a language model or fuzzy match to invent a sign.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def tokens_of(value: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", normalize(value), re.UNICODE)


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str
    concept: str | None = None


class SemanticRouter:
    """Match a finite reviewed semantic bank while preserving unmatched words."""

    def __init__(self, bank: dict | None = None):
        self.bank = bank or {}
        self.rules = tuple(self.bank.get("rules", []))
        self.aliases = tuple(self.bank.get("aliases", []))
        self.filler_phrases = tuple(
            sorted(
                (normalize(item) for item in self.bank.get("filler_phrases", [])),
                key=lambda item: (-len(tokens_of(item)), -len(item)),
            )
        )

    @staticmethod
    def _find_phrase(tokens: list[str], phrase: str) -> list[Span]:
        wanted = tokens_of(phrase)
        if not wanted:
            return []
        spans = []
        for start in range(0, len(tokens) - len(wanted) + 1):
            if tokens[start:start + len(wanted)] == wanted:
                spans.append(Span(start, start + len(wanted), phrase))
        return spans

    def _concept_spans(self, tokens: list[str], concept: dict) -> list[Span]:
        spans = []
        for alias in concept.get("aliases", []):
            spans.extend(
                Span(span.start, span.end, alias, concept.get("id"))
                for span in self._find_phrase(tokens, alias)
            )
        return sorted(spans, key=lambda span: (span.start, -(span.end - span.start)))

    def _filler_spans(self, tokens: list[str]) -> list[Span]:
        spans = []
        occupied = set()
        for phrase in self.filler_phrases:
            for span in self._find_phrase(tokens, phrase):
                indexes = set(range(span.start, span.end))
                if indexes & occupied:
                    continue
                occupied.update(indexes)
                spans.append(span)
        return spans

    @staticmethod
    def _is_overlap(first: Span, second: Span) -> bool:
        return first.start < second.end and second.start < first.end

    def _match_rule(self, tokens: list[str], rule: dict, allow_partial: bool = False) -> dict | None:
        selected: list[Span] = []
        for concept in rule.get("concepts", []):
            candidates = self._concept_spans(tokens, concept)
            candidates = [
                candidate
                for candidate in candidates
                if not any(self._is_overlap(candidate, previous) for previous in selected)
            ]
            if not candidates:
                if concept.get("required", True):
                    return None
                continue
            selected.append(candidates[0])

        for forbidden in rule.get("forbidden", []):
            if self._find_phrase(tokens, forbidden):
                return None

        filler_spans = self._filler_spans(tokens)
        consumed = set()
        for span in [*selected, *filler_spans]:
            consumed.update(range(span.start, span.end))
        remainder = [
            {"text": tokens[index], "index": index}
            for index in range(len(tokens))
            if index not in consumed
        ]
        if remainder and not allow_partial:
            return None

        return {
            "rule_id": rule["id"],
            "canonical_text": rule["canonical_text"],
            "intent": rule.get("intent", rule["id"]),
            "confidence": float(rule.get("confidence", 0.96)),
            "risk": rule.get("risk", "review"),
            "source": rule.get("source", "clinic-semantic-bank"),
            "explanation": rule.get("explanation", "Câu được đưa về một mẫu đã duyệt."),
            "matched": [
                {"text": span.text, "concept": span.concept, "start": span.start, "end": span.end}
                for span in selected
            ],
            "omitted": [
                {"text": span.text, "reason": "reviewed_discourse_marker", "start": span.start, "end": span.end}
                for span in filler_spans
            ],
            "unmatched": remainder,
        }

    def resolve(self, text: str, known_phrase_keys: set[str] | None = None) -> dict | None:
        """Return a safe candidate only when every input token is accounted for.

        Exact entries already handled by TextPlanner are intentionally skipped;
        the router is for natural spoken variants and longer polite utterances.
        """
        tokens = tokens_of(text)
        if not tokens:
            return None
        if known_phrase_keys is not None:
            key = " ".join(tokens)
            if key in known_phrase_keys:
                return None
        matches = []
        for rule in self.rules:
            result = self._match_rule(tokens, rule)
            if result:
                matches.append(result)
        if not matches:
            partial_matches = []
            for rule in self.rules:
                result = self._match_rule(tokens, rule, allow_partial=True)
                if result and result["unmatched"]:
                    matched_count = sum(
                        item["end"] - item["start"] for item in result["matched"]
                    )
                    result["coverage"] = matched_count / len(tokens)
                    partial_matches.append(result)
            if not partial_matches:
                return None
            partial_matches.sort(
                key=lambda item: (
                    -item["coverage"],
                    -item["confidence"],
                    item["rule_id"],
                )
            )
            result = partial_matches[0]
        else:
            matches.sort(key=lambda item: (-item["confidence"], item["rule_id"]))
            result = matches[0]
        result["input_text"] = text
        result["token_count"] = len(tokens)
        matched_terms = [
            item["text"][:1].upper() + item["text"][1:]
            for item in result["matched"]
        ]
        result["decision"] = (
            "auto"
            if result["risk"] == "safe" and not result["unmatched"]
            else "review"
        )
        if result["decision"] == "auto":
            result["message"] = "Đã bỏ từ đệm đã duyệt và giữ lại mẫu ký hiệu phù hợp. Bác sĩ vẫn thấy câu gốc để đối chiếu."
        elif result["unmatched"]:
            unknown = ", ".join(item["text"] for item in result["unmatched"])
            recognized = ", ".join(matched_terms)
            result["message"] = (
                f"Đã nhận ra: {recognized}. Chưa phân loại được: "
                f"{unknown}. Kiểm tra mẫu đề xuất trước khi phát avatar."
            )
        else:
            result["message"] = "Có cách diễn đạt gần mẫu ký hiệu nhưng cần bác sĩ kiểm tra trước khi phát."
        return result
