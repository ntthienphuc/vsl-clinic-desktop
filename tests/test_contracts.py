from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unicodedata

import numpy as np
import pytest

from backend.recognition import MODEL_SHA256, Recognizer, Segmenter
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
WORDS = json.loads((ASSETS / "vocabulary.json").read_text(encoding="utf-8"))
BANK = json.loads((ASSETS / "motions/manifest.json").read_text(encoding="utf-8"))
CATALOG = json.loads((ASSETS / "phrases.json").read_text(encoding="utf-8"))


@pytest.fixture
def session():
    return ClinicSession(TextPlanner(WORDS, CATALOG), {item["id"]: item["duration_ms"] for item in BANK["entries"]})


@pytest.mark.parametrize("word", WORDS, ids=[item["label"] for item in WORDS])
def test_each_gloss_and_unicode_normalization(word):
    result = TextPlanner(WORDS).plan(unicodedata.normalize("NFD", word["label"].upper()))
    assert result["supported"]
    assert [item["id"] for item in result["glosses"]] == [word["id"]]


@pytest.mark.parametrize("text", ["Không đau", "Chưa khỏe", "Đau 2 ngày", "Uống thuốc", "Đau bụng 2 ngày"])
def test_uncovered_content_never_becomes_partial_signs(session, text):
    plan = session.planner.plan(text)
    assert not plan["supported"]
    assert plan["unsupported"]
    with pytest.raises(ValueError):
        session.send(text, "sign")
    assert not session.messages
    message = session.send(text, "text")
    assert message["text"] == text
    assert session.playback is None


def test_compound_words_longest_match():
    result = TextPlanner(WORDS).plan("Bác sĩ, khám bệnh. Uống nước; nghỉ ngơi!")
    assert not result["supported"]
    assert result["coverage"] == 1
    assert not result["grammar_supported"]
    assert [item["label"] for item in result["glosses"]] == ["Bác sĩ", "Khám bệnh", "Uống", "Nước", "Nghỉ ngơi"]


def test_playback_waits_for_patient_and_clock_is_continuous(session, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    session.send("Uống nước", "sign")
    identity = session.playback["id"]
    assert session.playback["status"] == "loading"
    clock[0] += 2000
    assert session.elapsed() == 0
    session.control_playback("ready", identity)
    clock[0] += 400
    assert session.elapsed() == 400
    session.control_playback("pause", identity)
    clock[0] += 900
    assert session.elapsed() == 400
    session.control_playback("speed", identity, 0.5)
    session.control_playback("resume", identity)
    clock[0] += 600
    assert session.elapsed() == 700
    session.control_playback("replay", identity)
    assert session.elapsed() == 0
    with pytest.raises(ValueError):
        session.control_playback("speed", identity, 99)


def test_ordered_queue_and_stale_completion(session, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("backend.session.now_ms", lambda: clock[0])
    first = session.send("Bác sĩ", "sign")
    first_playback = session.playback["id"]
    second = session.send("Cảm ơn", "sign")
    assert len(session.pending) == 1
    session.control_playback("ready", first_playback)
    clock[0] += session.playback["total_ms"]
    session.control_playback("complete", first_playback, iteration=0)
    assert session.playback["message_id"] == second["id"]
    next_playback = dict(session.playback)
    session.control_playback("complete", first_playback, iteration=0)
    assert session.playback == next_playback
    assert first["status"] == "completed"
    assert not session.pending


def test_queue_bound_does_not_silently_drop(session):
    session.send("Đau", "sign")
    for _ in range(6):
        session.send("Mệt", "sign")
    with pytest.raises(ValueError):
        session.send("Khỏe", "sign")
    assert len(session.messages) == 7
    assert len(session.pending) == 6


def test_generation_fence_and_reset(session):
    session.capture_stopped(5)
    session.capture_event({"generation": 4, "type": "recognition", "predictions": [{"gloss": "Đau", "score": .9}]})
    assert not session.messages
    session.capture_event({"generation": 6, "type": "capture", "status": "signing", "captured": 300})
    session.capture_event({"generation": 7, "type": "capture", "status": "starting"})
    assert "captured" not in session.capture
    session.capture_event({"generation": 7, "type": "recognition", "predictions": [{"gloss": "Đau", "score": .9}]})
    session.confirm(session.current_result["id"], "Mệt")
    assert session.current_result["text"] == "Mệt"
    session.capture_stopped(8)
    assert session.current_result is None
    assert len(session.messages) == 1
    session.reset()
    assert not session.messages


def test_latest_snapshot_contains_all_ordered_messages(session):
    channel = asyncio.Queue(maxsize=1)
    session.listeners["test"] = ("doctor", channel)
    for text in ["Đau", "Mệt", "Nước"]:
        session.send(text, "text")
    assert channel.qsize() == 1
    snapshot = channel.get_nowait()
    assert [item["text"] for item in snapshot["messages"]] == ["Đau", "Mệt", "Nước"]
    session.messages[0]["text"] = "changed"
    assert snapshot["messages"][0]["text"] == "Đau"


def test_missing_person_and_nonmonotonic_timestamps():
    segmenter = Segmenter()
    missing = SimpleNamespace(pose_landmarks=None, left_hand_landmarks=None, right_hand_landmarks=None)
    for index in range(100):
        assert segmenter.consume(missing, index * 33.3, 1000 + index * 33.3) is None
    assert segmenter.flush() is None
    with pytest.raises(ValueError):
        segmenter.consume(missing, 1, 1001)


def test_model_and_inherited_preprocessing():
    recognizer = Recognizer(ASSETS)
    assert recognizer.sha256 == MODEL_SHA256
    assert len(recognizer.model.id2label) == 400
    assert recognizer.model.session.get_inputs()[0].shape[1:] == [3, 150, 27, 1]
    inherited = json.loads((ROOT / "backend/legacy/provenance.json").read_text(encoding="utf-8"))
    for relative, checksum in inherited["files"].items():
        copied = ROOT / "backend/legacy" / relative
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == checksum, relative


@pytest.mark.parametrize("entry", BANK["entries"], ids=[item["label"] for item in BANK["entries"]])
def test_reference_geometry_and_provenance(entry):
    path = ASSETS / "motions" / (entry["id"] + ".json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    motion = json.loads(path.read_text(encoding="utf-8"))
    frames = np.asarray(motion["frames"])
    confidence = np.asarray(motion["confidence"])
    assert frames.shape == (72, 75, 3)
    assert confidence.shape == (72, 75)
    assert np.isfinite(frames).all()
    assert np.isfinite(confidence).all()
    assert ((confidence >= 0) & (confidence <= 1)).all()
    single = entry.get("source_kind") == "qipedc-single"
    assert len(motion["reference_ids"]) == len(set(motion["declared_signers"]))
    assert len(motion["reference_ids"]) == 1 if single else len(motion["reference_ids"]) >= 4
    source_file = "qipedc-sources.json" if single else "source-manifest.json"
    sources = json.loads((ROOT / "research" / source_file).read_text(encoding="utf-8"))
    source = next(item for item in sources["words"] if item["id"] == entry["id"])
    if single:
        assert source["model_id"] is None
        assert source["demo"] is None
        assert motion["synthesis_profile"] == "palm-local-single-v1"
        assert source["source_url"].startswith("https://qipedc.moet.gov.vn/videos/")
        original = ASSETS / "reference-source/qipedc" / Path(source["references"][0]["path"]).name
        assert hashlib.sha256(original.read_bytes()).hexdigest() == motion["source_hashes"][0]
    else:
        assert source["demo_source"]["video_id"] not in motion["reference_ids"]
    refs = {item["video_id"]: item for item in source["references"]}
    for identity, digest in zip(motion["reference_ids"], motion["source_hashes"], strict=True):
        assert refs[identity]["sha256"] == digest
    for alignment in motion["alignment_paths"]:
        aligned = np.asarray(alignment)
        assert list(aligned[0]) == [0, 0]
        assert list(aligned[-1]) == [71, 71]
        step = np.diff(aligned, axis=0)
        assert ((step >= 0) & (step <= 1)).all()
        assert (step.sum(axis=1) > 0).all()
        assert np.max(np.abs(aligned[:, 0] - aligned[:, 1])) <= 15
    for base in [33, 54]:
        for chain in [[0, 1, 2, 3, 4], [0, 5, 6, 7, 8], [0, 9, 10, 11, 12], [0, 13, 14, 15, 16], [0, 17, 18, 19, 20]]:
            for parent, child in zip(chain[:-1], chain[1:]):
                lengths = np.linalg.norm(frames[:, base + child] - frames[:, base + parent], axis=-1)
                assert lengths.min() > .005
                assert np.ptp(lengths) < .001
