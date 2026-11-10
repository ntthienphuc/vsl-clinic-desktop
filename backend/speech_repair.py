"""Narrow ASR-only repair: never fuzzy-match clinical meaning into the bank."""
import re
import unicodedata


def repair_speech(result):
    raw = result["text"]
    # Only a complete low-risk courtesy expression. Extra words, negation,
    # quantities, unclear audio and truncated utterances remain untouched.
    key = " ".join(unicodedata.normalize("NFC", raw).casefold().strip().rstrip(".!? ").split())
    if result.get("uncertain") or result.get("cut_at_limit"):
        return raw, None
    segments = result.get("segments", [])
    acoustic_ok = bool(segments) and all(
        item.get("avg_logprob", -99) >= -.6 and item.get("no_speech_prob", 1) < .3
        for item in segments)
    if acoustic_ok and re.fullmatch(r"c[ạá]m ơn(?: ạ)?", key):
        return "Cảm ơn", {"rule": "courtesy-thanks-asr-v1", "raw_text": raw,
                           "corrected_text": "Cảm ơn", "scope": "whole courtesy utterance"}
    return raw, None
