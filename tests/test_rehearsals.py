"""The shipped rehearsal must remain inside both runtime vocabulary contracts."""
import csv
import json
from pathlib import Path
import pytest
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
STEPS = [step for scenario in read("demo/scenarios-v0.3.4.json")["scenarios"] for step in scenario["steps"]]


@pytest.mark.parametrize("step", STEPS, ids=[s["doctor"] for s in STEPS])
def test_demo_speech_auto_routes_once_and_manual_waits(step):
    words = read("assets/vocabulary.json")
    planner = TextPlanner(words, read("assets/phrases.json"), read("assets/semantic_bank.json"))
    bank = read("assets/motions/manifest.json")
    durations = {e["id"]: e["duration_ms"] for e in bank["entries"]}
    session = ClinicSession(planner, durations)
    session.configure_conversation("auto")
    session.start_conversation()
    result = {"utterance_id": "test-utterance", "text": step["doctor"], "uncertain": False}
    epoch = session.conversation["epoch"]
    assert session.speech_result(result, epoch)["status"] == "sent"
    assert session.speech_result(result, epoch) is None
    assert len(session.messages) == 1
    assert session.playback["glosses"]
    assert all(g["id"] in durations for g in session.playback["glosses"])
    session.reset()
    session.start_conversation()
    assert session.speech_result(result, session.conversation["epoch"])["status"] == "review"
    assert not session.messages and session.playback is None
    session.review_speech("test-utterance", step["doctor"], "sign")
    assert len(session.messages) == 1
    with (ROOT / "assets/gloss.csv").open(encoding="utf-8", newline="") as f:
        labels = dict(csv.reader(f))
    for identity in step["patient_ids"]:
        assert str(identity) in labels
        assert (ROOT / f"assets/samples/{identity:03d}.mp4").is_file()
