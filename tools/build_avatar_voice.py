"""Build fixed public doctor phrases/labels; no clinical input is uploaded.

edge-tts is a build-only dependency. Runtime uses bundled WAVs and 20 ms energy
envelopes. Mouth shapes are an audiovisual simulation, not phoneme alignment.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import wave
import re

import edge_tts
import numpy as np
from faster_whisper.audio import decode_audio

from backend.text_to_sign import TextPlanner

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/avatar-voice'
CACHE = ROOT / 'research/cache/avatar-voice'
VOICE = 'vi-VN-NamMinhNeural'


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    load = lambda name: json.loads((ROOT / 'assets' / name).read_text(encoding='utf8'))
    planner = TextPlanner(load('vocabulary.json'), load('phrases.json'), load('semantic_bank.json'))
    rows = [{'id': 'p:' + e['id'], 'text': e['text']} for e in planner.entries]
    rows += [{'id': 'w:' + e['id'], 'text': e['label']} for e in load('vocabulary.json')]
    by_text = {}
    for row in rows:
        by_text.setdefault(row['text'], []).append(row)
    # Synthesize a batch once, then split at verified word boundaries. This
    # avoids dozens of short service requests and keeps one consistent voice.
    texts = list(by_text)
    full_text = " ".join(text.rstrip(".!? ") + ("?" if text.endswith("?") else ".") for text in texts)
    batch_key = hashlib.sha256((VOICE + full_text).encode()).hexdigest()[:20]
    batch_audio, batch_words = CACHE / (batch_key + "-batch.mp3"), CACHE / (batch_key + "-batch.json")
    if not batch_audio.exists() or not batch_words.exists():
        for attempt in range(5):
            data, words = bytearray(), []
            try:
                async for chunk in edge_tts.Communicate(full_text, VOICE, rate='-10%', boundary='WordBoundary').stream():
                    if chunk['type'] == 'audio':
                        data.extend(chunk['data'])
                    elif chunk['type'] == 'WordBoundary':
                        words.append({'text': chunk['text'], 'start_ms': chunk['offset'] / 10000,
                                      'end_ms': (chunk['offset'] + chunk['duration']) / 10000})
                assert data and words
                batch_audio.write_bytes(data)
                batch_words.write_text(json.dumps(words, ensure_ascii=False), encoding='utf8')
                break
            except Exception as error:
                print(f"Batch retry {attempt + 1}: {type(error).__name__}", flush=True)
                if attempt == 4: raise
                await asyncio.sleep(2)
    samples = decode_audio(str(batch_audio), sampling_rate=24000)
    boundaries = json.loads(batch_words.read_text(encoding='utf8'))
    letters = lambda text: ''.join(re.findall(r'[^\W_]', text.casefold()))
    cursor, splits = 0, {}
    for text in texts:
        expected, observed, selected = letters(text), '', []
        while len(observed) < len(expected):
            item = boundaries[cursor]
            observed += letters(item['text'])
            selected.append(item)
            cursor += 1
        assert observed == expected, (text, observed, expected)
        start = max(0, selected[0]['start_ms'] - 40)
        end = min(len(samples) / 24, selected[-1]['end_ms'] + 100)
        if cursor < len(boundaries):
            end = min(end, boundaries[cursor]['start_ms'])
        splits[text] = (samples[int(start * 24):int(end * 24)],
                        [{**item, 'start_ms': item['start_ms'] - start, 'end_ms': item['end_ms'] - start} for item in selected])
    assert cursor == len(boundaries)
    completed = 0

    async def build(text, aliases):
        nonlocal completed
        name = hashlib.sha256((VOICE + '|-10%|' + text).encode()).hexdigest()[:20]
        audio_samples, words = splits[text]
        assert len(audio_samples) > 2400 and np.max(np.abs(audio_samples)) > .01
        pcm = (np.clip(audio_samples, -1, 1) * 32767).astype('<i2')
        target = OUT / (name + '.wav')
        with wave.open(str(target), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(pcm.tobytes())
        energy = np.array([np.sqrt(np.mean(audio_samples[i:i+480] ** 2)) for i in range(0, len(audio_samples), 480)])
        scale = max(.01, float(np.percentile(energy, 90)))
        envelope = np.clip((energy - .004) / scale, 0, 1)
        entry = {'file': target.name, 'duration_ms': round(len(audio_samples) / 24),
                 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                 'source_sha256': hashlib.sha256(batch_audio.read_bytes()).hexdigest(),
                 'envelope_step_ms': 20, 'envelope': np.rint(envelope * 255).astype(int).tolist(),
                 'words': words}
        completed += 1
        if completed % 10 == 0 or completed == len(by_text):
            print(f'{completed}/{len(by_text)} voice clips', flush=True)
        return [{**alias, **entry} for alias in aliases]

    built = await asyncio.gather(*(build(text, aliases) for text, aliases in by_text.items()))
    entries = [entry for group in built for entry in group]
    manifest = {'schema': 'clinic-avatar-voice-v1', 'voice': VOICE, 'language': 'vi-VN',
                'rate': '-10%', 'runtime_network': False,
                'mouth_mode': 'audio-energy and approximate word-vowel shapes; not validated lipreading', 'entries': entries}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (OUT / 'ATTRIBUTION.txt').write_text(
        'Fixed public dictionary labels and reviewed doctor phrases generated at build time\n'
        'with Microsoft Edge online TTS via edge-tts; vi-VN-NamMinhNeural, rate -10%.\n'
        'Local demo assets; no general redistribution license is asserted.\n'
        'Runtime performs no network synthesis and sends no conversation data.\n'
        'Original MP3 hashes and word timings are retained. WAV decoding and energy\n'
        'envelopes were computed locally. Mouth animation is approximate.\n', encoding='utf8')
    print(json.dumps({'entries': len(entries), 'clips': len(by_text), 'bytes': sum(p.stat().st_size for p in OUT.glob('*.wav'))}))


if __name__ == '__main__':
    asyncio.run(main())
