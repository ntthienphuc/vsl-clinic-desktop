"""Fresh per-utterance speech evidence, independent of streaming VAD state."""
import numpy as np
from .speech_activity import FRAME_BYTES, FRAME_MS, SAMPLE_RATE, SpeechActivity


def speech_evidence(pcm: bytes):
    detector = SpeechActivity()
    voice_frames = 0
    peak = 0.0
    for offset in range(0, len(pcm), FRAME_BYTES):
        frame = pcm[offset:offset + FRAME_BYTES]
        frame += bytes(FRAME_BYTES - len(frame))
        voice_frames += int(detector.is_speech(frame, SAMPLE_RATE))
        peak = max(peak, detector.probability)
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
    return dict(voiced_ms=voice_frames * FRAME_MS, peak_speech_probability=peak,
                rms=float(np.sqrt(np.mean(samples * samples))),
                accepted=voice_frames >= 6)


def accept_decoder_segment(segment):
    # A confident sequence of words does not overrule "no speech" evidence.
    return segment.no_speech_prob <= 0.65
