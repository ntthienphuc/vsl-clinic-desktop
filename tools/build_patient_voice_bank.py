"""Prepare fixed Vietnamese label audio for an entirely offline runtime.

Build-time networking sends only the public 400-label dictionary plus a fixed
uncertainty cue to Google Translate TTS, matching the project's existing fixture
generator. No user conversation, microphone, or patient data is uploaded.
The app ships WAVs only and does not call a synthesis service at runtime.
"""
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import wave

import numpy as np
from faster_whisper.audio import decode_audio

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'research/cache/patient-voice-natural'
OUTPUT = ROOT / 'assets/patient-voice'


def build(row):
    url = 'https://translate.google.com/translate_tts?' + urllib.parse.urlencode({
        'ie': 'UTF-8', 'client': 'tw-ob', 'tl': 'vi', 'q': row['text'] + '.',
    })
    cached = CACHE / (row['id'] + '.mp3')
    if not cached.exists():
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    if 'audio' not in response.headers.get('Content-Type', ''):
                        raise ValueError('Expected audio')
                    data = response.read(2 * 1024 * 1024)
                cached.write_bytes(data)
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(2 * (attempt + 1))
    rate = 24000
    samples = decode_audio(str(cached), sampling_rate=rate)
    assert len(samples) > rate * .1 and np.max(np.abs(samples)) > .01
    # Keep a 60 ms leading and 160 ms trailing guard. No time compression,
    # phoneme stretching, pitch adjustment, or aggressive silence removal.
    voiced = np.flatnonzero(np.abs(samples) > .002)
    samples = samples[max(0, voiced[0] - int(rate * .06)):min(len(samples), voiced[-1] + int(rate * .16))]
    audio = (np.clip(samples, -1, 1) * 32767).astype('<i2')
    path = OUTPUT / (row['id'] + '.wav')
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate)
        writer.writeframes(audio.tobytes())
    return {**row, 'file': path.name, 'duration_ms': round(len(audio) / rate * 1000),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_sha256': hashlib.sha256(cached.read_bytes()).hexdigest(), 'source_url': url}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'assets/gloss.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = [{'id': key, 'text': text} for key, text in csv.reader(stream)]
    assert {int(row['id']) for row in rows} == set(range(400))
    rows.append({'id': 'uncertain', 'text': 'Chưa chắc'})
    entries = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for entry in executor.map(build, rows):
            entries.append(entry)
            if len(entries) % 25 == 0: print(f'{len(entries)}/401 clips', flush=True)
    manifest = {'schema': 'clinic-patient-voice-v1', 'language': 'vi-VN',
                'voice': 'Google Translate Vietnamese fixed-label audio',
                'generation': 'Build-time fixed public labels only; native speaking rate; 60/160 ms silence guards',
                'runtime_network': False, 'entries': entries}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUTPUT / 'ATTRIBUTION.txt').write_text(
        'Fixed Vietnamese label audio generated using Google Translate TTS at build time.\n'
        'Only public dictionary labels and the fixed uncertainty cue were submitted.\n'
        'Original MP3s, request URLs and hashes are retained in the build cache/manifest.\n'
        'Changes: decoded to mono 24 kHz PCM WAV; short silence guards retained; native speaking rate.\n'
        'No TTS service or additional voice/model installation is used by the runtime.\n'
        'These generated voice assets are included for this local demo. No new public\n'
        'license or general redistribution right over service-generated audio is asserted.\n', encoding='utf-8')
    print(json.dumps({'files': len(entries), 'bytes': sum(p.stat().st_size for p in OUTPUT.glob('*.wav')),
                      'max_duration_ms': max(e['duration_ms'] for e in entries)}, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
