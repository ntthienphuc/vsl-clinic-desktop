import json
from pathlib import Path
import shutil

import pytest

from backend.playback import build_timeline, load_join_profile
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner

ASSETS = Path(__file__).resolve().parents[1] / "assets"
WORDS = json.loads((ASSETS / "vocabulary.json").read_text(encoding="utf-8"))
CATALOG = json.loads((ASSETS / "phrases.json").read_text(encoding="utf-8"))
BANK = json.loads((ASSETS / "motions/manifest.json").read_text(encoding="utf-8"))
DURATIONS = {item["id"]: item["duration_ms"] for item in BANK["entries"]}


@pytest.fixture
def session():
    return ClinicSession(TextPlanner(WORDS, CATALOG), DURATIONS, load_join_profile(ASSETS))


def test_three_signs_use_one_contiguous_timeline_and_only_authorized_trims(session):
    session.send("Bác sĩ uống nước", "sign")
    playback = session.playback
    timeline = playback["timeline"]
    assert [item["phase"] for item in timeline] == ["intro", "sign", "bridge", "sign", "bridge", "sign", "outro"]
    assert timeline[0]["start_ms"] == 0
    assert timeline[-1]["end_ms"] == playback["total_ms"]
    for previous, following in zip(timeline, timeline[1:]):
        assert previous["end_ms"] == following["start_ms"]
    signs = [item for item in timeline if item["phase"] == "sign"]
    assert signs[0]["source_start_ms"] == 0
    assert signs[-1]["source_end_ms"] == DURATIONS["348"]
    assert signs[1]["source_start_ms"] > 0
    assert signs[1]["source_end_ms"] < DURATIONS["243"]
    assert playback["total_ms"] < 700 + sum(DURATIONS[key] for key in ["11", "243", "348"]) + 560


def test_no_trim_across_clauses_and_unknown_join_keeps_complete_strokes(session):
    session.send("Bác sĩ khám bệnh. Uống nước.", "sign")
    playback = session.playback
    signs = [item for item in playback["timeline"] if item["phase"] == "sign"]
    for item, key in zip(signs[:2], ["11", "145"]):
        assert item["source_start_ms"] == 0
        assert item["source_end_ms"] == DURATIONS[key]
    assert [item["phase"] for item in playback["timeline"]].count("intro") == 2
    assert len(playback["clauses"]) == 2


def test_stop_and_replay_reject_old_completion(session, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    session.send("Bác sĩ uống nước", "sign")
    identity = session.playback["id"]
    session.control_playback("ready", identity)
    session.control_playback("complete", identity, iteration=0)
    assert session.playback["status"] == "playing"
    clock[0] += session.playback["total_ms"]
    session.control_playback("replay", identity)
    assert session.playback["iteration"] == 1
    assert session.playback["status"] == "loading"
    session.control_playback("ready", identity)
    clock[0] += session.playback["total_ms"]
    session.control_playback("complete", identity, iteration=0)
    assert session.playback["status"] == "playing"
    session.control_playback("stop", identity)
    assert session.playback["status"] == "stopped"
    assert not session.pending


@pytest.mark.parametrize("state", ["loading", "playing", "paused"])
@pytest.mark.parametrize("mode", ["sign", "text"])
def test_doctor_barge_in_replaces_delivery_and_ignores_late_callbacks(session, state, mode):
    previous = session.send("Bác sĩ uống nước", "sign")
    old_id = session.playback["id"]
    if state != "loading":
        session.control_playback("ready", old_id, iteration=0)
    if state == "paused":
        session.control_playback("pause", old_id)
    following = session.send("Cảm ơn", mode)
    assert previous["status"] == "interrupted"
    assert previous["superseded_by"] == following["id"]
    assert not session.pending
    new_id = session.playback["id"] if mode == "sign" else None
    for action in ["ready", "complete", "stop", "resume", "replay"]:
        session.control_playback(action, old_id, iteration=0)
    if mode == "sign":
        assert session.playback["id"] == new_id != old_id
        assert session.playback["message_id"] == following["id"]
        assert session.playback["status"] == "loading"
        session.control_playback("ready", new_id, iteration=0)
        assert session.playback["status"] == "playing"
    else:
        assert session.playback is None
        assert following["presented_at_ms"]


def test_unaccepted_speech_does_not_interrupt_but_accepted_speech_does(session):
    session.configure_conversation("auto")
    session.start_conversation()
    previous = session.send("Bác sĩ uống nước", "sign")
    old_id = session.playback["id"]
    session.control_playback("ready", old_id, iteration=0)
    epoch = session.conversation["epoch"]
    assert session.speech_result({"utterance_id": "mic:1", "text": "Uống thuốc 2 viên"}, epoch)["status"] == "review"
    assert session.playback["id"] == old_id
    result = session.speech_result({"utterance_id": "mic:2", "text": "Đồng ý nằm nghỉ ngơi"}, epoch)
    assert result["status"] == "sent"
    assert previous["status"] == "interrupted"
    assert session.playback["message_id"] == result["message_id"]
    assert session.playback["id"] != old_id
    assert not session.pending


def test_disconnection_freezes_playback_until_explicit_resume(session, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    session.send("Bác sĩ uống nước", "sign")
    identity = session.playback["id"]
    session.control_playback("ready", identity)
    clock[0] += 1200
    session.patient_disconnected()
    clock[0] += 10000
    assert session.elapsed() == 1200
    assert session.playback["pause_reason"] == "patient_disconnected"
    session.control_playback("resume", identity)
    clock[0] += 100
    assert session.elapsed() == 1300


def test_profile_and_complete_clause_coverage_are_checked(session):
    with pytest.raises(ValueError):
        build_timeline([{"id": "11"}, {"id": "243"}], [{"gloss_start": 0, "gloss_end": 1}], DURATIONS)


def test_packaged_sentence_joins_need_only_compact_motions(tmp_path):
    compact = tmp_path / "motions"
    compact.mkdir()
    for name in ["sentence_motion.json", "motions/manifest.json"]:
        shutil.copyfile(ASSETS / name, tmp_path / name)
    profile = json.loads((ASSETS / "sentence_motion.json").read_text("utf-8"))
    for identity, window in profile["windows"].items():
        shutil.copyfile(ASSETS / "motions" / (identity + ".vslm"), compact / (identity + ".vslm"))
    loaded = load_join_profile(tmp_path)
    assert loaded == load_join_profile(ASSETS)
    for identity, window in loaded["windows"].items():
        original = json.loads((ASSETS / "motions" / (identity + ".json")).read_text("utf-8"))
        assert window["entry_ms"] == original["duration_ms"] * window["entry_frame"] / (len(original["frames"]) - 1)
    assert not list(compact.glob("[0-9]*.json"))
    damaged = next(compact.glob("*.vslm"))
    data = bytearray(damaged.read_bytes())
    data[-1] ^= 1
    damaged.write_bytes(data)
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_join_profile(tmp_path)


def test_replay_ignores_ready_from_previous_iteration(session):
    session.send("Y tá đo nhiệt độ.", "sign")
    identity = session.playback["id"]
    session.control_playback("ready", identity, iteration=0)
    session.control_playback("replay", identity)
    session.control_playback("ready", identity, iteration=0)
    assert session.playback["status"] == "loading"
    session.control_playback("ready", identity, iteration=1)
    assert session.playback["status"] == "playing"


def test_context_uses_presented_clause_not_future_question(session, monkeypatch):
    # Inspect clause context without automatic patient handover pausing time.
    session.configure_conversation("manual")
    clock = [1000.0]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    session.send("Cảm ơn. Bạn có đau không?", "sign")
    session.control_playback("ready", session.playback["id"], iteration=0)
    event = {"type": "recognition", "predictions": [{"model_id": 379, "gloss": "Đau", "score": .8}]}
    session.capture_event(event)
    assert not session.current_result["context_candidates"]
    clock[0] += session.playback["clauses"][1]["start_ms"] + 100
    session.capture_event(event)
    assert session.current_result["context_candidates"][0]["gloss"] == "Đau"
