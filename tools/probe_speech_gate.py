"""Reproducible speech/noise regression; synthetic noise, public Vietnamese speech.

No microphone recording and no patient data. Times here are audio times, not
live wall-clock delivery. Use probe_speech.py for the WebSocket transport.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.speech import SAMPLE_RATE, SpeechService, UtteranceSegmenter
from faster_whisper.audio import decode_audio


def fixtures():
    rng = np.random.default_rng(7321)
    size = SAMPLE_RATE * 40
    t = np.arange(size) / SAMPLE_RATE
    hiss = rng.normal(0, 0.003, size)
    hum = 0.012 * np.sin(2 * np.pi * 120 * t) + rng.normal(0, 0.0004, size)
    modulated = sosfilt(butter(2, [0.02, 0.2], btype='bandpass', output='sos'), rng.normal(size=size))
    modulated *= 1 + 0.8 * np.sin(2 * np.pi * 3 * t)
    modulated *= 0.003 / np.sqrt(np.mean(modulated * modulated))
    clicks = np.zeros(size)
    for second in range(1, 40, 2):
        clicks[second * SAMPLE_RATE:second * SAMPLE_RATE + 320] = rng.normal(0, 0.12, 320)
    voice = decode_audio(str(ROOT / 'research/speech-samples/91.wav'), sampling_rate=SAMPLE_RATE)
    return {
        'digital_silence_40s': np.zeros(size),
        'hiss_40s': hiss,
        'hum_40s': hum,
        'keyboard_impulses_40s': clicks,
        'modulated_noise_40s': modulated,
        'speech_then_silence_40s': np.concatenate([np.zeros(SAMPLE_RATE), voice, np.zeros(size)]),
        'speech_then_hum_40s': np.concatenate([hum[:SAMPLE_RATE], voice + hum[:len(voice)], hum]),
        'speech_then_modulated_noise_40s': np.concatenate([np.zeros(SAMPLE_RATE), voice, modulated]),
        'same_speech_twice': np.concatenate([np.zeros(SAMPLE_RATE), voice, np.zeros(SAMPLE_RATE * 2), voice, np.zeros(SAMPLE_RATE * 3)]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decode', action='store_true')
    args = parser.parse_args()
    report = {'kind': 'offline deterministic audio regression', 'cases': {}}
    service = SpeechService(ROOT / 'assets')
    try:
        for name, samples in fixtures().items():
            pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
            segmenter = UtteranceSegmenter()
            segments = []
            started = time.perf_counter()
            for offset in range(0, len(pcm), 3200):
                segments.extend(segmenter.feed(pcm[offset:offset + 3200]))
            tail = segmenter.finish()
            if tail:
                segments.append(tail)
            case = {
                'audio_seconds': len(samples) / SAMPLE_RATE,
                'segmenter_ms': (time.perf_counter() - started) * 1000,
                'utterance_count': len(segments),
                'segments': [{key: value for key, value in item.items() if key != 'pcm'} for item in segments],
            }
            if args.decode:
                case['transcripts'] = [service.transcribe(item['pcm']) for item in segments[:2]]
            report['cases'][name] = case
            print(name, json.dumps(case, ensure_ascii=False), flush=True)
    finally:
        service.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
