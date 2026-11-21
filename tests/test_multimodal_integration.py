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


def test_slightly_lower_fusion_score_boundary_preserves_input_quality_guards():
    quality=dict(sign_valid=True,mouth_valid=True,hand_coverage=.9,single_face_fraction=.9,
                 input_fps=20,max_capture_gap_ms=100)
    boundary=dict(reason='arms_returned_to_neutral')
    result=dict(status='ok',top_k=[dict(score=.71),dict(score=.2)])
    assert decide(result,quality,boundary)['committed']
    result['top_k'][0]['score']=.69
    assert not decide(result,quality,boundary)['committed']
    result['top_k'][0]['score']=.99
    for bad in [dict(mouth_valid=False),dict(hand_coverage=.5),dict(input_fps=9),dict(max_capture_gap_ms=400)]:
        assert not decide(result,{**quality,**bad},boundary)['committed']


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


@pytest.mark.parametrize("first,last,ignored", [(100,333,True),(100,348,True),
    (100,399,True),(100,400,False),(100,800,False),(None,None,True)])
def test_short_return_motion_is_not_made_a_word_by_context_padding(monkeypatch,first,last,ignored):
    monkeypatch.syspath_prepend(str(ASSETS / "multimodal100"))
    from multimodal.boundaries import insufficient_active_core
    assert insufficient_active_core(dict(first_active_capture_ms=first,last_active_capture_ms=last,
        start_capture_ms=0,end_capture_ms=1200,buffered_frame_count=30)) is ignored


def test_ignored_motion_keeps_the_last_patient_word_and_records_the_reason():
    s=session()
    s.capture_event(event())
    previous=s.current_result
    s.capture_event(dict(type='segment_ignored',generation=1,reason='insufficient_active_motion'))
    assert s.current_result is previous
    assert len(s.turns.current['words'])==1
    assert s.metrics[-1]['reason']=='insufficient_active_motion'


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
