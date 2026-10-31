import json
from pathlib import Path

from backend.patient_turns import paraphrase
from backend.text_to_sign import TextPlanner


ASSETS = Path(__file__).resolve().parents[1] / "assets"
WORDS = json.loads((ASSETS / "vocabulary.json").read_text(encoding="utf-8"))
PHRASES = json.loads((ASSETS / "phrases.json").read_text(encoding="utf-8"))
SEMANTIC = json.loads((ASSETS / "semantic_bank.json").read_text(encoding="utf-8"))


def planner():
    return TextPlanner(WORDS, PHRASES, SEMANTIC)


def test_spoken_politeness_and_synonym_route_to_reviewed_motion_sequence():
    plan = planner().plan("Y tá ơi, kiểm tra thân nhiệt giúp em nhé")
    assert plan["supported"]
    assert plan["text"] == "Y tá ơi, kiểm tra thân nhiệt giúp em nhé"
    assert plan["projection"] == ["Y tá", "Nhiệt độ", "Đo"]
    assert plan["semantic"]["decision"] == "auto"
    assert plan["semantic"]["applied"]
    assert {item["text"] for item in plan["semantic"]["omitted"]} == {"ơi", "giúp em", "nhé"}


def test_unknown_meaning_is_not_hidden_by_semantic_router():
    plan = planner().plan("Y tá ơi, không đo nhiệt độ")
    assert not plan["supported"]
    assert plan["unsupported"]
    assert plan["semantic"]["decision"] == "review"
    assert [item["text"] for item in plan["semantic"]["unmatched"]] == ["không"]
    assert plan["suggestions"][0]["text"] == "Y tá đo nhiệt độ."


def test_long_spoken_sentence_exposes_review_candidate_without_auto_playback():
    plan = planner().plan("Y tá ơi, hôm nay kiểm tra thân nhiệt giúp em nhé")
    assert not plan["supported"]
    assert plan["semantic"]["decision"] == "review"
    assert plan["semantic"]["applied"] is False
    assert [item["text"] for item in plan["semantic"]["unmatched"]] == ["hôm", "nay"]
    assert plan["semantic"]["candidate_projection"] == ["Y tá", "Nhiệt độ", "Đo"]
    assert [item["text"] for item in plan["unsupported"]] == ["hôm", "nay"]
    assert plan["suggestions"][0]["text"] == "Y tá đo nhiệt độ."
    assert "Đã nhận ra: Y tá, Kiểm tra thân nhiệt." in plan["message"]
    assert "hôm, nay" in plan["message"]


def test_partial_candidate_keeps_negation_in_review_instead_of_dropping_it():
    plan = planner().plan("Y tá không đo nhiệt độ")
    assert not plan["supported"]
    assert plan["semantic"]["decision"] == "review"
    assert [item["text"] for item in plan["semantic"]["unmatched"]] == ["không"]
    assert plan["suggestions"][0]["text"] == "Y tá đo nhiệt độ."


def test_pronoun_reordering_stays_review_only_until_signer_review():
    plan = planner().plan("Tôi ăn cơm")
    assert not plan["supported"]
    assert plan["semantic"]["decision"] == "review"
    assert plan["semantic"]["applied"] is False
    assert plan["unsupported"] == []
    assert plan["suggestions"][0]["text"] == "Ăn cơm."


def test_patient_turn_keeps_raw_glosses_and_uses_only_reviewed_reordering():
    reading = paraphrase([{"text": "Cơm"}, {"text": "Ăn"}])
    assert reading == {"text": "Ăn cơm.", "rewritten": True, "rule": "reviewed-short-request-v1"}
    assert paraphrase([{"text": "Không cần"}, {"text": "Đau"}])["rewritten"] is False


def test_partial_semantic_match_does_not_override_fully_supported_clauses():
    plan = planner().plan("Bác sĩ khám bệnh. Bạn có đau bụng không? Uống nước.")
    assert plan["supported"]
    assert plan["projection"] == ["Bác sĩ", "Khám bệnh", "Bụng", "Đau", "Nước", "Uống"]
    assert len(plan["clauses"]) == 3
    assert plan["clauses"][1]["nonmanual"] == "question"
    assert not plan["unsupported"]


def test_known_clause_does_not_make_unknown_clause_auto_safe():
    plan = planner().plan("Uống nước. Uống thuốc hai viên.")
    assert not plan["supported"]
    assert not plan.get("semantic", {}).get("applied")
