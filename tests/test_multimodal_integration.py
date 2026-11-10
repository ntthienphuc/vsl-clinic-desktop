"""Protocol/session tests with explicit synthetic transport; not model accuracy."""
import json
from pathlib import Path
import sys
import time

import pytest

from backend.multimodal_provider import MultimodalProvider
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner
from multimodal.policy import decide, recognition_event

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def session():
    words = json.loads((ASSETS / "vocabulary.json").read_text("utf8"))
    phrases = json.loads((ASSETS / "phrases.json").read_text("utf8"))
    return ClinicSession(TextPlanner(words, phrases), {w["id"]: 1000 for w in words})


def event(segment="s:1", gloss="Sốt", score=.99, committed=True, generation=1):
    return dict(type="recognition", generation=generation, engine_family="multimodal100",
                segment_id=segment, actual_mode="fusion", contract="test-contract",
                predictions=[dict(gloss=gloss, original_gloss=gloss, score=score,
                                  class_id="W068", class_index=67, model_id=None, voice_key="mm100-W068")],
                policy=dict(committed=committed, version="test"))


def test_fever_identity_never_becomes_legacy_index_or_threshold():
    s = session()
    s.capture_event(event(score=.99, committed=False))
    assert s.current_result["uncertain"]
    assert s.current_result["predictions"][0]["model_id"] is None
    assert s.current_result["voice_key"] == "mm100-W068"
    assert s.current_result["original_gloss"] == "Sốt"
    assert s.current_result["context_candidates"] == []


def test_transport_duplicate_and_deliberate_repeated_word_differ():
    s = session()
    s.capture_event(event())
    s.capture_event(event())
    s.capture_event(event("s:2"))
    assert [w["text"] for w in s.turns.current["words"]] == ["Sốt", "Sốt"]
    assert len({w["id"] for w in s.turns.current["words"]}) == 2


def test_multimodal_end_rejects_inflight_results_and_quality():
    s = session()
    s.capture_event(event())
    s.stop_conversation(generation=2)
    s.capture_event(event("s:2"))
    s.capture_event(dict(type="recognition_unavailable", generation=1, quality_warning="late"))
    assert not s.messages and s.current_result is None
    assert "quality_warning" not in s.capture


def test_pending_inference_does_not_close_patient_turn(monkeypatch):
    s = session()
    clock = [1000]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    s.capture_event(dict(type="capture", generation=1, status="ready", inflight_segments=1))
    s.capture_event(event())
    clock[0] = 20000
    s.tick()
    assert s.turns.current is not None
    s.capture_event(dict(type="capture", generation=1, status="ready", inflight_segments=0))
    s.tick()
    assert s.turns.current is None


def test_missing_modality_never_returns_fusion_guess():
    policy = decide(dict(status="unavailable", reason="fusion_requires_both"), {}, {})
    assert policy["disposition"] == "unavailable" and not policy["committed"]


def test_r3_context_preserves_decision_and_does_not_read_future_frames(monkeypatch):
    from dataclasses import asdict
    monkeypatch.syspath_prepend(str(ASSETS / "multimodal100"))
    from multimodal.boundaries import make_gate, extend_context
    original = make_gate({})
    r3 = make_gate({"profile": "slgcn-avhubert"})
    old_config, new_config = asdict(original.config), asdict(r3.config)
    for key in old_config:
        if key not in {"version", "context_before_ms", "context_after_ms"}:
            assert old_config[key] == new_config[key]
    boundary = dict(start_capture_ms=1000, end_capture_ms=2000,
                    decision_capture_ms=2200, selected_frame_ids=list(range(10,21)),
                    boundary_config=new_config, reason="arms_returned_to_neutral")
    metadata = [dict(capture_ms=i*100, frame_id=i) for i in range(30)]
    extended = extend_context(boundary, metadata)
    assert extended["decision_capture_ms"] == 2200
    assert extended["selected_frame_ids"] == list(range(5,23))
    assert extended["core_frame_ids"] == boundary["selected_frame_ids"]
    assert boundary["start_capture_ms"] == 1000


def test_r3_context_is_limited_to_observed_buffer(monkeypatch):
    from dataclasses import asdict
    monkeypatch.syspath_prepend(str(ASSETS / "multimodal100"))
    from multimodal.boundaries import make_gate, extend_context
    config = asdict(make_gate({"profile": "slgcn-avhubert"}).config)
    boundary = dict(start_capture_ms=100, end_capture_ms=500,
                    decision_capture_ms=750, selected_frame_ids=list(range(1,6)),
                    boundary_config=config, reason="arms_returned_to_neutral")
    metadata = [dict(capture_ms=i*100, frame_id=i) for i in range(7)]
    extended = extend_context(boundary, metadata)
    assert extended["start_capture_ms"] == 0 and extended["end_capture_ms"] == 600
    assert extended["decision_capture_ms"] == 750


def test_activity_hold_resumes_without_committing_a_word():
    from backend.patient_handover import PatientHandover
    handover = PatientHandover()
    playback = dict(id="p",status="playing",elapsed_ms=0,rate=1)
    capture = dict(status="signing",boundary_state="signing",has_face=True,hand_count=1)
    assert handover.observe(playback,capture,True,lambda:500,1000)
    assert playback["pause_reason"] == "patient_activity" and playback["elapsed_ms"] == 500
    assert not handover.settle(playback,dict(status="ready",inflight_segments=1),3000)
    assert handover.settle(playback,dict(status="ready",inflight_segments=0),3100)
    assert playback["status"] == "playing" and playback["elapsed_ms"] == 500


def test_committed_reply_cannot_auto_resume_and_manual_mode_does_not_hold():
    from backend.patient_handover import PatientHandover
    hold = PatientHandover()
    playback = dict(id="p",status="playing",elapsed_ms=0)
    capture = dict(status="signing",boundary_state="signing",has_face=True,hand_count=1)
    assert not hold.observe(playback,capture,False,lambda:500,1000)
    assert hold.observe(playback,capture,True,lambda:500,1000)
    playback["pause_reason"] = "patient_reply"
    assert not hold.settle(playback,dict(status="ended"),9000)
    hold.manual()
    playback.update(status="playing")
    assert not hold.observe(playback,capture,True,lambda:500,10000)


def test_explicit_stop_is_never_undone_by_activity_timeout():
    from backend.patient_handover import PatientHandover
    hold = PatientHandover()
    playback = dict(id="p",status="playing",elapsed_ms=0)
    capture = dict(status="signing",boundary_state="signing",has_face=True,hand_count=1)
    hold.observe(playback,capture,True,lambda:500,1000)
    playback["status"] = "stopped"
    assert not hold.settle(playback,dict(status="ended"),10000)
    assert playback["status"] == "stopped"


@pytest.mark.parametrize("reason,value", [
    ("hand_coverage", .1), ("single_face_fraction", .1),
    ("input_fps", 4), ("max_capture_gap_ms", 700)])
def test_bad_sampling_or_visibility_cannot_be_read_as_fact(reason, value):
    info = dict(sign_valid=True, mouth_valid=True, hand_coverage=1,
                single_face_fraction=1, input_fps=25, max_capture_gap_ms=40)
    info[reason] = value
    result = dict(status="ok", top_k=[dict(score=.999), dict(score=.0001)])
    assert not decide(result, info, dict(reason="arms_returned_to_neutral"))["committed"]


def test_voice_covers_all_100_raw_labels_and_hashes():
    import hashlib
    mapping = json.loads((ASSETS / "multimodal100/label_mapping.json").read_text("utf8"))
    bank = {e["id"]: e for e in json.loads((ASSETS / "patient-voice/manifest.json").read_text("utf8"))["entries"]}
    assert len(mapping) == 100
    for i, row in enumerate(mapping):
        assert row["class_index"] == i and row["class_id"] == f"W{i+1:03d}"
        entry = bank[row["voice_key"]]
        assert entry["text"] == row["display_text"]
        assert hashlib.sha256((ASSETS / "patient-voice" / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]


def test_pipe_late_events_are_fenced_and_process_joins():
    # This fake deliberately emits a result AFTER parent Stop; model runs have
    # separate integration probes. No camera, GPU or patient data are used here.
    code = """import json,sys,time
print(json.dumps(dict(type='worker_ready',device='test')),flush=True)
for line in sys.stdin:
 r=json.loads(line)
 if r['action']=='start':
  time.sleep(.15)
  print(json.dumps(dict(type='recognition',generation=r['generation'],predictions=[])),flush=True)
 elif r['action']=='shutdown': break
"""
    events = []
    provider = MultimodalProvider(ASSETS, events.append, command=[sys.executable, "-u", "-c", code])
    try:
        first = provider.start("fixture", "video")
        assert provider.ready.wait(3)
        time.sleep(.05)
        provider.stop()
        second = provider.start("fixture", "video")
        time.sleep(.5)
        recognized = [e for e in events if e["type"] == "recognition"]
        assert [e["generation"] for e in recognized] == [second]
        assert second > first
        process = provider.process
    finally:
        provider.close()
    assert process.poll() == 0
