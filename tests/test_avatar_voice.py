import copy
import json
from pathlib import Path
import pytest
from backend.avatar_voice import attach_narration, load_avatar_voice
from backend.playback import build_timeline
from backend.speech_repair import repair_speech
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner

ROOT = Path(__file__).resolve().parents[1]


def test_word_narration_keeps_strokes_and_holds_final_pose_without_overlap():
    glosses = [{"id": "a"}, {"id": "b"}]
    clauses = [{"text": "first", "phrase_id": "one", "gloss_start": 0, "gloss_end": 1},
               {"text": "second", "phrase_id": "two", "gloss_start": 1, "gloss_end": 2}]
    base = build_timeline(glosses, clauses, {"a": 1000, "b": 1000})
    bank = {"w:a": {"id": "w:a", "file": "one.wav", "text": "first", "duration_ms": 3000},
            "w:b": {"id": "w:b", "file": "two.wav", "text": "second", "duration_ms": 2500}}
    result = attach_narration(copy.deepcopy(base), glosses, bank)
    assert result["total_ms"] > base["total_ms"]
    assert result["timeline"][0]["start_ms"] == 0
    for before, after in zip(result["timeline"], result["timeline"][1:]):
        assert before["end_ms"] == after["start_ms"]
    assert result["timeline"][-1]["end_ms"] == result["total_ms"]
    for original, current in zip([s for s in base["timeline"] if s["phase"] == "sign"],
                                 [s for s in result["timeline"] if s["phase"] == "sign"]):
        assert original["end_ms"] - original["start_ms"] == current["end_ms"] - current["start_ms"]
        assert original["source_start_ms"] == current["source_start_ms"]
    assert result["audio_cues"][0]["end_ms"] < result["clauses"][1]["start_ms"]
    for sign, audio in zip([s for s in result['timeline'] if s['phase'] == 'sign'], result['audio_cues']):
        assert sign['index'] == audio['gloss_index']
        assert sign['start_ms'] == audio['start_ms']
    assert all(s['source_ms'] == 1000 for s in result['timeline'] if s['phase'] == 'voice_hold')


def test_three_signs_speak_three_word_clips_in_avatar_order_not_sentence_order():
    glosses = [{'id': 'doctor'}, {'id': 'temperature'}, {'id': 'measure'}]
    clause = dict(gloss_start=0, gloss_end=3, phrase_id='measure-temperature', text='Bác sĩ đo nhiệt độ.')
    bank = {f'w:{g["id"]}': dict(id=f'w:{g["id"]}', text=g['id'], file=g['id']+'.wav', duration_ms=600)
            for g in glosses}
    bank['p:measure-temperature'] = dict(id='p:measure-temperature',text='Bác sĩ đo nhiệt độ.',file='sentence.wav',duration_ms=2500)
    original = build_timeline(glosses, [clause], {g['id']: 1200 for g in glosses})
    result = attach_narration(copy.deepcopy(original), glosses, bank)
    assert result['timeline'] == original['timeline']
    assert [c['entry_id'] for c in result['audio_cues']] == ['w:doctor','w:temperature','w:measure']
    assert [c['start_ms'] for c in result['audio_cues']] == [s['start_ms'] for s in original['timeline'] if s['phase']=='sign']


def test_no_bank_preserves_original_motion_timing():
    glosses = [{"id": "a"}]
    original = build_timeline(glosses, [], {"a": 1000})
    result = attach_narration(copy.deepcopy(original), glosses, {})
    assert result["timeline"] == original["timeline"]
    assert result["audio_cues"] == []


@pytest.mark.parametrize("text", ["Cạm ơn.", "Cám ơn ạ!"])
def test_low_risk_whole_utterance_repair_requires_acoustic_evidence(text):
    data = {"text": text, "segments": [{"avg_logprob": -.3, "no_speech_prob": .01}]}
    assert repair_speech(data)[0] == "Cảm ơn"
    assert repair_speech({**data, "uncertain": True}) == (text, None)
    assert repair_speech({**data, "cut_at_limit": True}) == (text, None)
    assert repair_speech({"text": text}) == (text, None)


@pytest.mark.parametrize("text", ["Không cảm ơn", "Cạm ơn bác sĩ", "Cạm ơn, tôi không đau", "Đau tay trái", "hai viên thuốc"])
def test_repair_never_fuzzy_maps_clinical_or_extra_content(text):
    assert repair_speech({"text": text, "segments": [{"avg_logprob": -.1, "no_speech_prob": .01}]}) == (text, None)


def make_session():
    load = lambda name: json.loads((ROOT / "assets" / name).read_text(encoding="utf8"))
    words = load("vocabulary.json")
    return ClinicSession(TextPlanner(words, load("phrases.json"), load("semantic_bank.json")),
                         {w["id"]: 1000 for w in words})


def test_auto_repaired_speech_preserves_raw_input_and_deduplicates():
    session = make_session()
    session.configure_conversation("auto")
    session.start_conversation()
    result = {"utterance_id": "thanks", "text": "Cạm ơn", "segments": [{"avg_logprob": -.1, "no_speech_prob": .01}]}
    assert session.speech_result(result, session.conversation["epoch"])["status"] == "sent"
    assert session.messages[-1]["text"] == "Cảm ơn"
    assert session.messages[-1]["raw_text"] == "Cạm ơn"
    assert session.speech_result(result, session.conversation["epoch"]) is None
    assert len(session.messages) == 1


@pytest.mark.parametrize("score", [.2, .9])
def test_patient_readout_does_not_pause_avatar(score):
    session = make_session()
    session.send("Uống nước.", "sign")
    session.control_playback("ready", session.playback["id"], iteration=0)
    session.capture_event({"type": "recognition", "generation": 1, "predictions": [{"gloss": "Đau", "score": score}]})
    assert session.playback["status"] == "playing"
    assert "pause_reason" not in session.playback
    assert session.current_result["text"] == "Đau"
