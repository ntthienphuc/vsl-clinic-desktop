"""Per-microphone streaming state for the bundled Silero v6 ONNX detector.

The graph and h/c/context contract come from faster-whisper 1.2.1 vad.py.
Weights are shared, recurrent state is not. No network or extra model download.
"""
import numpy as np

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512
FRAME_BYTES = FRAME_SAMPLES * 2
FRAME_MS = 32


class SpeechActivity:
    def __init__(self):
        self.model = None
        self.h = np.zeros((1, 1, 128), dtype=np.float32)
        self.c = np.zeros((1, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
        self.speaking = False
        self.probability = 0.0

    def is_speech(self, frame: bytes, rate: int) -> bool:
        if rate != SAMPLE_RATE or len(frame) != FRAME_BYTES:
            raise ValueError('Speech activity requires 512 mono PCM16 samples at 16 kHz.')
        if self.model is None:
            from faster_whisper.vad import get_vad_model
            self.model = get_vad_model()
        samples = np.frombuffer(frame, dtype='<i2').astype(np.float32).reshape(1, -1) / 32768
        inputs = np.concatenate((self.context, samples), axis=1)
        output, self.h, self.c = self.model.session.run(None, {'input': inputs, 'h': self.h, 'c': self.c})
        self.context = samples[:, -64:].copy()
        self.probability = float(output.reshape(-1)[0])
        threshold = 0.35 if self.speaking else 0.60
        # The energy floor excludes digital near-silence, not quiet normal speech.
        self.speaking = self.probability >= threshold and float(np.sqrt(np.mean(samples * samples))) >= 0.0003
        return self.speaking
