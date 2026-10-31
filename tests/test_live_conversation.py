from pathlib import Path
import json

import pytest

from backend.patient_turns import PatientTurns, paraphrase
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session():
    words = json.loads((ROOT / "assets/vocabulary.json").read_text(encoding="utf-8"))
    phrases = json.loads((ROOT / "assets/phrases.json").read_text(encoding="utf-8"))
    return ClinicSession(TextPlanner(words, phrases), {word["id"]: 1000 for word in words})


def recognized(session, label, score=.9):
    session.capture_event({"type": "recognition", "generation": 1,
                           "predictions": [{"gloss": label, "score": score, "model_id": 1}]})


def test_each_word_broadcast_before_sentence_end(session, monkeypatch):
    now = [1000]
    monkeypatch.setattr("backend.session.now_ms", lambda: now[0])
    recognized(session, "Đau")
    first = session.snapshot()
    assert first["patient_turn"]["text"] == "Đau"
    assert first["messages"][0]["status"] == "streaming"
    now[0] += 700
    recognized(session, "Mệt")
    assert session.snapshot()["patient_turn"]["text"] == "Đau · Mệt"
    assert first["patient_turn"]["text"] == "Đau"  # snapshots never mutate
    now[0] += 1499
    session.tick()
    assert session.turns.current is not None
    now[0] += 1
    session.tick()
    assert session.turns.current is None
    assert len(session.messages) == 1
    assert session.messages[0]["text"] == "Đau và mệt."
    assert session.messages[0]["raw_text"] == "Đau · Mệt"


def test_long_sentence_does_not_wait_to_show_words(session, monkeypatch):
    now = [1000]
    monkeypatch.setattr("backend.session.now_ms", lambda: now[0])
    for index in range(25):
        now[0] += 1200
        recognized(session, "Đau")
        session.tick()
        assert len(session.snapshot()["patient_turn"]["words"]) == index + 1
    assert len(session.messages) == 1


def test_very_long_turn_keeps_all_words_when_bounded_turn_splits(session, monkeypatch):
    now = [1000]
    monkeypatch.setattr("backend.session.now_ms", lambda: now[0])
    for _ in range(129):
        now[0] += 1000
        recognized(session, "Đau")
    assert [len(turn["words"]) for turn in session.messages] == [128, 1]
    assert session.messages[0]["end_reason"] == "continued_in_next_turn"
    assert session.messages[1]["status"] == "streaming"
    assert len({word["id"] for turn in session.messages for word in turn["words"]}) == 129


def test_inference_and_motion_fence_sentence_end(session, monkeypatch):
    monkeypatch.setattr("backend.session.now_ms", lambda: 1000)
    recognized(session, "Đau")
    assert not session.turns.tick(4000, {"status": "ready", "inflight_segments": 1})
    assert not session.turns.tick(4000, {"status": "signing"})
    assert session.turns.tick(4000, {"status": "ready", "inflight_segments": 0})


def test_no_context_hallucination_or_negation_loss():
    for labels in [["Không cần", "Đau"], ["Muốn", "Ngủ", "Ăn"], ["Đau", "Đau"]]:
        words = [{"text": label, "uncertain": False} for label in labels]
        result = paraphrase(words)
        assert result["text"] == " · ".join(labels)
        assert not result["rewritten"]
    assert not paraphrase([{"text": "Đau", "uncertain": True}, {"text": "Mệt"}])["rewritten"]


def test_manual_never_sends_until_review(session):
    session.start_conversation()
    epoch = session.conversation["epoch"]
    result = {"utterance_id": "a:1", "text": "Uống nước", "uncertain": False}
    assert session.speech_result(result, epoch)["status"] == "review"
    assert not session.messages
    assert session.speech_result(result, epoch) is None
    session.review_speech("a:1", "Uống nước", "sign")
    assert len(session.messages) == 1
    assert not session.speech_drafts
    with pytest.raises(ValueError):
        session.review_speech("a:1", "Uống nước", "sign")


def test_auto_sends_known_sentence_and_holds_unknown(session):
    session.configure_conversation("auto")
    session.start_conversation()
    epoch = session.conversation["epoch"]
    assert session.speech_result({"utterance_id": "a:1", "text": "Uống nước"}, epoch)["status"] == "sent"
    assert session.speech_result({"utterance_id": "a:2", "text": "Uống thuốc 2 viên"}, epoch)["status"] == "review"
    assert len(session.messages) == 1
    assert session.speech_drafts[0]["text"] == "Uống thuốc 2 viên"


def test_unknown_user_question_warns_and_retry_then_auto_sends(session):
    session.configure_conversation('auto')
    session.start_conversation()
    epoch = session.conversation['epoch']
    result = {'utterance_id': 'mic:1', 'text': 'Bạn cảm thấy thế nào?'}
    assert session.speech_result(result, epoch)['status'] == 'review'
    draft = session.speech_drafts[0]
    assert draft['reason_code'] == 'unsupported'
    assert 'nói lại' in draft['reason']
    assert session.playback is None
    assert session.messages == []
    # Nói lại explicitly dismisses this draft, never sends it as text.
    session.review_speech('mic:1', None)
    assert session.speech_drafts == []
    assert session.speech_result({'utterance_id': 'mic:2', 'text': 'Bạn có đau không?'}, epoch)['status'] == 'sent'
    assert len(session.messages) == 1
    assert session.playback['status'] == 'loading'
    assert [word['label'] for word in session.playback['glosses']] == ['Đau']


@pytest.mark.parametrize('text', ['...', 'uống ' * 150])
def test_malformed_or_overlong_asr_does_not_stop_microphone(session, text):
    session.configure_conversation('auto')
    session.start_conversation()
    result = session.speech_result({'utterance_id': 'bad:1', 'text': text}, session.conversation['epoch'])
    assert result['status'] == 'review'
    assert not session.messages
    assert 'nói lại' in session.speech_drafts[0]['reason']


def test_stop_or_mode_change_fences_late_asr(session):
    session.configure_conversation("auto")
    session.start_conversation()
    epoch = session.conversation["epoch"]
    session.configure_conversation("manual")
    assert session.speech_result({"utterance_id": "a:1", "text": "Đau"}, epoch) is None
    epoch = session.conversation["epoch"]
    session.stop_conversation()
    assert session.speech_result({"utterance_id": "a:2", "text": "Đau"}, epoch) is None
    assert not session.messages


def test_word_correction_updates_completed_turn(session):
    recognized(session, "Đau")
    recognized(session, "Mệt")
    identity = session.current_result["id"]
    session.turns.finish(3000)
    session.confirm(identity, "Lạnh")
    assert session.messages[0]["raw_text"] == "Đau · Lạnh"
    assert session.messages[0]["text"] == "Đau và lạnh."
