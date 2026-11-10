"""Mode changes must fence old words, release camera and preserve label spaces."""
from pathlib import Path
from types import SimpleNamespace
import json

from backend.recognition_modes import RecognitionModes, load_catalogs
from backend.clinic_phrases import quick_phrases
from backend.text_to_sign import TextPlanner
from backend.session import ClinicSession
from backend.speech_quality import accept_decoder_segment

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class Provider:
    owners = set()

    def __init__(self, callback, name):
        self.publish, self.name = callback, name
        self.generation = 0
        self.recognizer = SimpleNamespace(sha256="test-only")
        self.stops = 0

    def warmup(self):
        pass

    def start(self, source, kind):
        assert not self.owners, "two providers opened the same camera"
        self.owners.add(self.name)
        self.generation += 1
        self.publish(dict(type="capture", status="starting", generation=self.generation))
        return self.generation

    def stop(self):
        self.owners.discard(self.name)
        self.stops += 1

    stop_and_wait = stop
    close = stop

    def info(self):
        return dict(name="fake fusion", worker=dict(status="ready"), labels=100)

    def preview_frame(self):
        return 1, b"frame"


def router(events):
    Provider.owners.clear()
    return RecognitionModes(ASSETS, events.append, {
        m: (lambda callback, name=m: Provider(callback, name))
        for m in ("fusion", "sign_only")
    })


def test_switch_releases_camera_and_drops_delayed_old_word():
    events = []
    r = router(events)
    assert r.mode == "fusion"
    g1 = r.start(0, "camera")
    old = r.providers["fusion"]
    r.activate("sign_only")
    g2 = r.start(0, "camera")
    assert g2 > g1 and Provider.owners == {"sign_only"}
    count = len(events)
    old.publish(dict(type="recognition", generation=g1, predictions=[dict(gloss="Sốt")]))
    assert len(events) == count
    r.providers["sign_only"].publish(dict(type="recognition", generation=g2, predictions=[]))
    assert events[-1]["engine_family"] == "legacy400"
    assert events[-1]["actual_mode"] == "sign_only"
    r.activate("fusion")
    assert r.providers["fusion"] is old
    g3 = r.start(0, "camera")
    assert g3 > g2 and Provider.owners == {"fusion"}
    r.close()
    assert not Provider.owners


def test_external_end_floor_prevents_late_word_and_preview():
    events = []
    r = router(events)
    g = r.start(0, "camera")
    r.generation = g + 1
    r.stop()
    r.providers["fusion"].publish(dict(type="recognition", generation=g))
    assert not any(e["type"] == "recognition" for e in events)
    assert r.preview_frame()[1] is None


def test_dictionaries_have_exact_classes_voice_and_only_existing_demos():
    modes = load_catalogs(ASSETS)
    voices = {e["id"]: e["text"] for e in json.loads((ASSETS/"patient-voice/manifest.json").read_text("utf8"))["entries"]}
    assert [w["class_id"] for w in modes["fusion"]] == [f"W{i:03}" for i in range(1, 101)]
    assert [w["model_id"] for w in modes["sign_only"]] == list(range(400))
    assert all(w["model_id"] is None for w in modes["fusion"])
    assert not ({w["id"] for w in modes["fusion"]} & {w["id"] for w in modes["sign_only"]})
    for words in modes.values():
        for word in words:
            assert voices[word["voice_key"]] == word["label"]
            if word["demo"]:
                assert (ASSETS/word["demo"].removeprefix("/assets/")).is_file()


def test_mode_metadata_survives_end_without_old_capture_results():
    words = json.loads((ASSETS/"vocabulary.json").read_text("utf8"))
    phrases = json.loads((ASSETS/"phrases.json").read_text("utf8"))
    s = ClinicSession(TextPlanner(words, phrases), {})
    s.recognition = dict(mode="sign_only", labels=400)
    s.stop_conversation(generation=4)
    assert s.snapshot()["recognition"]["mode"] == "sign_only"
    s.capture_event(dict(type="recognition", generation=3, predictions=[]))
    assert not s.messages


def test_quick_clinic_phrases_keep_supported_meaning_and_examples():
    words = json.loads((ASSETS/"vocabulary.json").read_text("utf8"))
    phrases = json.loads((ASSETS/"phrases.json").read_text("utf8"))
    p = TextPlanner(words, phrases)
    rows = quick_phrases(p)
    assert len(rows) == 24 and all(r["supported"] for r in rows)
    assert {"Bác sĩ khám bệnh.", "Y tá đo nhiệt độ."} <= {r["text"] for r in rows}
    assert len({r["id"] for r in rows}) == len(rows)


def test_confident_hallucinated_text_cannot_overrule_no_speech():
    assert not accept_decoder_segment(SimpleNamespace(no_speech_prob=.91, avg_logprob=-.1))
    assert accept_decoder_segment(SimpleNamespace(no_speech_prob=.1, avg_logprob=-.4))


def test_end_during_model_load_clears_now_and_does_not_resume_capture(monkeypatch):
    """Exercise the actual endpoint race; a slow provider holds the control lock."""
    import asyncio
    import threading
    from backend import app as routes

    async def scenario():
        entered, release = threading.Event(), threading.Event()
        events = []
        r = router(events)
        r.warmup()
        original_activate = r.activate
        def slow_activate(mode):
            entered.set()
            assert release.wait(5)
            original_activate(mode)
        monkeypatch.setattr(r, 'activate', slow_activate)
        words = json.loads((ASSETS/'vocabulary.json').read_text('utf8'))
        phrases = json.loads((ASSETS/'phrases.json').read_text('utf8'))
        s = ClinicSession(TextPlanner(words, phrases), {})
        s.start_conversation()
        s.send('Bác sĩ khám bệnh.', 'text')
        monkeypatch.setattr(routes, 'session', s)
        monkeypatch.setattr(routes, 'engine', r)
        monkeypatch.setattr(routes, 'control', asyncio.Lock())
        async def clear():
            pass
        monkeypatch.setattr(routes, 'clear_language_context', clear)
        switch = asyncio.create_task(routes.recognition_mode(routes.RecognitionModeRequest(mode='sign_only')))
        await asyncio.to_thread(entered.wait, 2)
        end = asyncio.create_task(routes.stop_conversation(routes.EndConversationRequest()))
        await asyncio.sleep(.02)
        assert s.conversation['status'] == 'idle' and not s.messages
        assert not end.done(), 'worker cleanup still waits for the control lock'
        release.set()
        await asyncio.gather(switch, end)
        assert not r.running and not Provider.owners
        assert not s.messages and s.capture['status'] == 'idle'
    asyncio.run(scenario())


def test_camera_timeout_remains_fenced_on_retry():
    import pytest
    from backend.capture import CaptureEngine, Run
    alive = True
    worker = SimpleNamespace(name='blocked-camera', join=lambda timeout: None, is_alive=lambda: alive)
    capture = CaptureEngine(None, lambda event: None)
    run = Run(1, 0, 'camera')
    run.threads = [worker]
    capture.current = run
    for _ in range(2):
        with pytest.raises(RuntimeError, match='has not stopped'):
            capture.stop()
        assert capture.current is run and run.cancel.is_set()
    alive = False
    capture.stop()
    assert capture.current is None
