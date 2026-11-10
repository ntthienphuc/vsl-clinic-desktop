import json
from pathlib import Path

import pytest

from backend.language_assist import LanguageAssist, candidates_for, preserves_protected
from backend.text_to_sign import TextPlanner
from backend.session import ClinicSession

ASSETS = Path(__file__).resolve().parents[1] / "assets"


@pytest.fixture
def planner():
    read = lambda name: json.loads((ASSETS / name).read_text(encoding="utf-8"))
    return TextPlanner(read("vocabulary.json"), read("phrases.json"), read("semantic_bank.json"))


@pytest.mark.parametrize("text,projection", [
    ("Chị có bị đau bụng không ạ?", ["Bụng", "Đau"]),
    ("Cho bác sĩ hỏi anh có sốt không?", ["Sốt"]),
    ("Cô thấy trong người ra sao?", ["Cảm thấy", "Thế nào"]),
    ("Chú có cảm thấy yếu không?", ["Cảm thấy", "Yếu"]),
    ("Anh có muốn uống nước không?", ["Muốn", "Nước", "Uống"]),
    ("Chị đau bụng khi nào?", ["Bụng", "Đau", "Bao giờ"]),
    ("Vui lòng ngồi nghỉ nhé.", ["Ngồi", "Nghỉ ngơi"]),
    ("Mời bạn uống nước.", ["Nước", "Uống"]),
    ("Xin mời chị rửa tay.", ["Rửa tay"]),
    ("Bạn thấy trong người ra sao vậy?", ["Cảm thấy", "Thế nào"]),
    ("Cho tôi hỏi uống nước.", None),  # An incomplete question cannot become a request.
])
def test_conversational_variants_cover_entire_clause(planner, text, projection):
    plan = planner.plan(text)
    assert plan["text"] == text
    if projection is None:
        assert not plan["supported"]
    else:
        assert plan["supported"]
        assert plan["projection"] == projection


@pytest.mark.parametrize("text", [
    "Chị không đau bụng.", "Chị có hơi đau bụng không?", "Bạn có đau bụng bên trái không?",
    "Bạn có sốt 2 ngày không?", "Chị uống nước trước khám.", "Anh nên uống hai ly nước.",
    "Bạn không được uống nước.", "Bạn có đau ngực không?", "Cho tôi hỏi bạn có dị ứng thuốc không?",
    "Y tá đo nhiệt độ và tiêm thuốc.", "Chị bị sốt từ hôm qua.", "Bạn uống nước hoặc nghỉ ngơi.",
])
def test_modifiers_negation_and_unknown_clinical_content_never_auto_play(planner, text):
    assert not planner.plan(text)["supported"]


def test_composition_keeps_question_and_request_without_swallowing_clauses(planner):
    text = "Chị có bị đau bụng không? Vui lòng ngồi nghỉ nhé. Y tá kiểm tra thân nhiệt giúp em."
    plan = planner.plan(text)
    assert plan["supported"]
    assert plan["projection"] == ["Bụng", "Đau", "Ngồi", "Nghỉ ngơi", "Y tá", "Nhiệt độ", "Đo"]
    assert len(plan["clauses"]) == 3
    assert plan["clauses"][0]["nonmanual"] == "question"
    assert plan["clauses"][1]["nonmanual"] == "neutral"
    bad = planner.plan(text + " Uống thuốc hai viên.")
    assert not bad["supported"] and bad["suggestions"] == []


def test_auto_speech_sends_new_variant_exactly_once(planner):
    durations = {word["id"]: 1000 for word in planner.words}
    session = ClinicSession(planner, durations)
    session.configure_conversation("auto")
    session.start_conversation()
    result = {"text": "Chị có bị đau bụng không ạ?", "utterance_id": "upgrade-040", "uncertain": False}
    epoch = session.conversation["epoch"]
    session.speech_result(result, epoch)
    session.speech_result(result, epoch)
    assert len(session.messages) == 1
    assert session.messages[0]["text"] == result["text"]
    assert session.speech_drafts == []


@pytest.mark.parametrize("source,target", [
    ("Bạn không đau bụng", "Bạn có đau bụng không?"),
    ("Tôi ăn cơm", "Ăn cơm."), ("Uống hai ly nước", "Uống nước."),
    ("Y tá đo nhiệt độ hôm nay", "Y tá đo nhiệt độ."),
    ("Bạn có hơi mệt không", "Bạn có mệt không?"),
    ("Bạn có đau bụng bên trái không", "Bạn có đau bụng không?"),
])
def test_retrieval_does_not_offer_meaning_dropping_candidates(source, target):
    assert not preserves_protected(source, target)


def test_model_cannot_invent_ids_or_bypass_plan(planner, monkeypatch):
    helper = LanguageAssist(ASSETS, planner)
    monkeypatch.setattr(LanguageAssist, "available", property(lambda self: True))
    monkeypatch.setattr(helper, "_start", lambda: None)
    monkeypatch.setattr(helper, "_request", lambda *args, **kwargs: {"choices": [{"message": {"content": '{"id":"new-sign"}'}}]})
    assert helper.suggest("Bụng của bạn có bị nhức không")["suggestions"] == []
    assert all(preserves_protected("Bụng của bạn có bị nhức không", item["text"]) for item in candidates_for("Bụng của bạn có bị nhức không", planner.entries))


def test_busy_and_offline_assistant_do_not_block_normal_planning(planner, monkeypatch):
    helper = LanguageAssist(ASSETS, planner)
    monkeypatch.setattr(LanguageAssist, "available", property(lambda self: True))
    helper._busy.acquire()
    assert helper.suggest("Bụng của bạn có bị nhức không")["source"] == "none"
    assert planner.plan("Chị có bị đau bụng không?")["supported"]
    helper._busy.release()
    monkeypatch.setattr(LanguageAssist, "available", property(lambda self: False))
    assert helper.suggest("Bụng của bạn có bị nhức không")["suggestions"] == []


def test_model_parse_failure_and_close_cannot_return_a_suggestion(planner, monkeypatch):
    helper = LanguageAssist(ASSETS, planner)
    monkeypatch.setattr(LanguageAssist, "available", property(lambda self: True))
    monkeypatch.setattr(helper, "_start", lambda: None)
    monkeypatch.setattr(helper, "_request", lambda *args, **kwargs: {"choices": [{"message": {"content": 'not JSON'}}]})
    assert helper.suggest("Bụng của bạn có bị nhức không")["suggestions"] == []


@pytest.mark.parametrize("content", ["[]", "null", '{"id":[]}', '{"id":123}'])
def test_valid_json_with_invalid_shape_is_rejected(planner, monkeypatch, content):
    helper = LanguageAssist(ASSETS, planner)
    monkeypatch.setattr(LanguageAssist, "available", property(lambda self: True))
    monkeypatch.setattr(helper, "_start", lambda: None)
    monkeypatch.setattr(helper, "_request", lambda *args, **kwargs: {"choices": [{"message": {"content": content}}]})
    assert helper.suggest("Bụng của bạn có bị nhức không")["suggestions"] == []
    helper.close()
    monkeypatch.setattr(helper, "_request", lambda *args, **kwargs: {"choices": [{"message": {"content": '{"id":"0"}'}}]})
    assert helper.suggest("Bụng của bạn có bị nhức không")["suggestions"] == []
