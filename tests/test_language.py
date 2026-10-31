import json
from pathlib import Path

import pytest

from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner


ASSETS = Path(__file__).resolve().parents[1] / "assets"
WORDS = json.loads((ASSETS / "vocabulary.json").read_text(encoding="utf-8"))
CATALOG = json.loads((ASSETS / "phrases.json").read_text(encoding="utf-8"))


@pytest.fixture
def planner():
    return TextPlanner(WORDS, CATALOG)


@pytest.mark.parametrize("entry", TextPlanner(WORDS, CATALOG).entries, ids=lambda item: item["id"])
def test_complete_phrase_preserves_written_meaning_and_nonmanuals(planner, entry):
    for text in [entry["text"], *entry["aliases"]]:
        plan = planner.plan(text)
        assert plan["text"] == text
        assert plan["supported"]
        assert [item["id"] for item in plan["glosses"]] == entry["gloss_ids"]
        assert plan["nonmanual"] == entry["nonmanual"]
    session = ClinicSession(planner, {word["id"]: 1000 for word in WORDS})
    session.send(entry["text"], "sign")
    assert session.playback["nonmanual"] == entry["nonmanual"]
    assert session.playback["text"] == entry["text"]


@pytest.mark.parametrize("text", ["Không đau", "Bạn không đau", "Bạn có đau không 2 ngày?", "Uống nước?", "Uống 2 nước", "khỏe?", "khoe", "ôm", "ấn", "Có mệt không hay đau?", "Không mệt mỏi"])
def test_unknown_semantics_are_not_replaced_or_partially_sent(planner, text):
    plan = planner.plan(text)
    assert not plan["supported"]
    assert not plan["suggestions"]
    session = ClinicSession(planner, {word["id"]: 1000 for word in WORDS})
    with pytest.raises(ValueError):
        session.send(text, "sign")
    assert not session.messages
    assert session.send(text, "text")["text"] == text


def test_curated_suggestion_requires_an_explicit_choice(planner):
    original = planner.plan("nhà thương")
    assert not original["supported"]
    assert original["suggestions"][0]["text"] == "Bệnh viện"
    assert planner.plan(original["suggestions"][0]["text"])["supported"]


def test_context_never_overwrites_model_ranking_or_invents_candidates(planner):
    predictions = [{"model_id": 204, "gloss": "Mệt", "score": .6}, {"model_id": 379, "gloss": "Đau", "score": .35}]
    session = ClinicSession(planner, {word["id"]: 1000 for word in WORDS})
    session.send("Bạn có đau không?", "sign")
    session.control_playback("ready", session.playback["id"])
    session.capture_event({"type": "recognition", "generation": 0, "predictions": predictions})
    result = session.current_result
    assert result["text"] == "Mệt"
    assert result["predictions"] == predictions
    assert result["context_candidates"][0]["gloss"] == "Đau"
    assert not planner.contextual_candidates(predictions[:1], "ask-pain")
    assert not planner.contextual_candidates([{**predictions[1], "score": .05}], "ask-pain")
    session.reset()
    session.capture_event({"type": "recognition", "generation": 0, "predictions": predictions})
    assert not session.current_result["context_candidates"]


def test_three_sign_clause_and_multisentence_order(planner):
    plan = planner.plan("Bác sĩ uống nước. Bạn có đau không? Cảm ơn.")
    assert plan["supported"]
    assert [item["id"] for item in plan["glosses"]] == ["11", "243", "348", "379", "86"]
    assert [item["nonmanual"] for item in plan["clauses"]] == ["neutral", "question", "neutral"]
    assert [(item["gloss_start"], item["gloss_end"]) for item in plan["clauses"]] == [(0, 3), (3, 4), (4, 5)]


@pytest.mark.parametrize("text", ["Nước bác sĩ uống", "Bác sĩ không uống nước", "Bác sĩ uống nước 2 lần", "Bác sĩ uống nước và nghỉ ngơi", "Tôi ăn cơm", "Uống nước. Không đau.", "?Đau", "Đau / Mệt", "Bác sĩ uống nước?", "Bạn có đau không??", "Đau_", "Uống nước…"])
def test_incomplete_or_unreviewed_clause_never_plays_partial_meaning(planner, text):
    assert not planner.plan(text)["supported"]
    session = ClinicSession(planner, {word["id"]: 1000 for word in WORDS})
    with pytest.raises(ValueError):
        session.send(text, "sign")
    assert session.playback is None
    assert session.send(text, "text")["text"] == text


def test_known_vocabulary_is_not_a_grammar_claim(planner):
    plan = planner.plan("Đau mệt khỏe")
    assert plan["coverage"] == 1
    assert not plan["supported"]
    assert not plan["grammar_supported"]
    assert plan["issues"][0]["reason"] == "unknown_grammar"


def test_future_queued_question_does_not_bias_current_recognition(planner):
    session = ClinicSession(planner, {word["id"]: 1000 for word in WORDS})
    session.send("Cảm ơn", "sign")
    session.control_playback("ready", session.playback["id"])
    session.send("Bạn có đau không?", "sign")
    session.capture_event({"type": "recognition", "predictions": [{"model_id": 379, "gloss": "Đau", "score": .8}]})
    assert not session.current_result["context_candidates"]


@pytest.mark.parametrize("text", [
    "Y tá ơi, đo nhiệt độ nha",
    "Y tá ơi đo nhiệt độ nhé.",
    "Bác sĩ ơi, uống nước ạ",
])
def test_polite_spoken_markers_are_removed_only_before_planning(planner, text):
    plan = planner.plan(text)
    assert plan["supported"]
    assert plan["normalized_text"].casefold().rstrip(".") in {
        "y tá đo nhiệt độ",
        "bác sĩ uống nước",
    }
    assert plan["projection"] in [
        ["Y tá", "Nhiệt độ", "Đo"],
        ["Bác sĩ", "Nước", "Uống"],
    ]
    assert plan["text"] == text


@pytest.mark.parametrize("text", [
    "Y tá ơi, không đo nhiệt độ nha",
    "Y tá ơi, đo nhiệt độ 2 lần nha",
    "Y tá ơi, đo nhiệt độ và uống nước nha",
])
def test_meaningful_unknown_words_still_block_partial_sign(planner, text):
    plan = planner.plan(text)
    assert not plan["supported"]
    assert plan["unsupported"]
    assert plan["projection"] != ["Y tá", "Nhiệt độ", "Đo"]
