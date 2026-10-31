from types import SimpleNamespace
from backend.recognition import sampling_quality
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner


def frames(times):
    return [SimpleNamespace(clinic_timestamp_ms=t) for t in times]


def test_capture_density_and_long_gaps_are_independent_of_model_confidence():
    assert sampling_quality(frames(range(0, 2000, 33)))["quality_warning"] is None
    assert sampling_quality(frames(range(0, 2000, 125)))["quality_warning"]
    assert sampling_quality(frames([0, 33, 66, 99, 400, 433]))["quality_warning"]
    assert sampling_quality([SimpleNamespace()])["observed_fps"] is None


def test_sparse_capture_stays_uncertain_even_with_high_classifier_score():
    s = ClinicSession(TextPlanner([{"id": "379", "label": "Đau"}]), {"379": 1000})
    quality = sampling_quality(frames(range(0, 2000, 125)))
    s.capture_event({"type": "recognition", "generation": 1, **quality,
                     "predictions": [{"gloss": "Đau", "score": .99, "model_id": 379}]})
    assert s.current_result["uncertain"]
    assert s.current_result["text"] == "Đau"  # Raw word is still streamed immediately.
    assert s.current_result["quality_warning"]
    turn = s.turns.current
    s.turns.finish(1000, "test")
    assert not turn["reading"]["rewritten"]
