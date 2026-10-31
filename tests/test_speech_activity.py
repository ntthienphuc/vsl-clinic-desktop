"""Real bundled neural VAD regressions; ASR accuracy is measured separately."""
import numpy as np
import pytest

from backend.speech import UtteranceSegmenter
from backend.speech_activity import FRAME_BYTES, SpeechActivity
from tools.probe_speech_gate import fixtures


@pytest.mark.parametrize('name,count', [
    ('digital_silence_40s', 0),
    ('hiss_40s', 0),
    ('hum_40s', 0),
    ('keyboard_impulses_40s', 0),
    ('modulated_noise_40s', 0),
    ('speech_then_silence_40s', 1),
    ('speech_then_hum_40s', 1),
    ('speech_then_modulated_noise_40s', 1),
    ('same_speech_twice', 2),
])
def test_neural_gate_real_speech_then_long_quiet(name, count):
    samples = fixtures()[name]
    pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
    segmenter = UtteranceSegmenter()
    result = []
    # Worklet packets need not align with the detector's 32 ms windows.
    for offset in range(0, len(pcm), 3200):
        result.extend(segmenter.feed(pcm[offset:offset + 3200]))
    assert segmenter.finish() is None
    assert len(result) == count
    assert all(not item['cut_at_limit'] for item in result)
    assert all(item['endpoint_audio_ms'] == 576 for item in result)


def test_recurrent_states_are_per_microphone():
    first = SpeechActivity()
    second = SpeechActivity()
    samples = fixtures()['speech_then_silence_40s'][:16000 * 5]
    pcm = (samples * 32767).astype('<i2').tobytes()
    assert any(first.is_speech(pcm[i:i + FRAME_BYTES], 16000)
               for i in range(0, len(pcm) - FRAME_BYTES, FRAME_BYTES))
    assert not second.is_speech(bytes(FRAME_BYTES), 16000)
    assert first.model is second.model
    assert not np.shares_memory(first.h, second.h)
