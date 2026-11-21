"""Build fixed public doctor phrases/labels; no clinical input is uploaded.

edge-tts is a build-only dependency. Runtime uses bundled WAVs and 20 ms energy
envelopes. Mouth shapes are an audiovisual simulation, not phoneme alignment.
"""
import asyncio
import argparse
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
# The standalone neural reading of "Bụng" is unclear. A short public context
# stabilizes pronunciation; retain only its FIRST word, with no preceding audio.
PRONUNCIATION_CONTEXT = {'Bụng': 'Bụng đau.'}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only-missing', action='store_true', help='Keep all existing voice bytes and synthesize new dictionary entries only.')
    parser.add_argument('--isolated', action='store_true', help='Synthesize each text independently to avoid cross-utterance audio at split boundaries.')
    parser.add_argument('--sentence-boundaries', action='store_true', help='Prefer complete-label timing for isolated labels when the service cannot return word timing; context trimming still requires word boundaries.')
    parser.add_argument('--replace-id', action='append', default=[], help='Regenerate just this known narration ID; old WAVs remain intact.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    load = lambda name: json.loads((ROOT / 'assets' / name).read_text(encoding='utf8'))
    planner = TextPlanner(load('vocabulary.json'), load('phrases.json'), load('semantic_bank.json'))
    rows = [{'id': 'p:' + e['id'], 'text': e['text']} for e in planner.entries]
    rows += [{'id': 'w:' + e['id'], 'text': e['label']} for e in load('vocabulary.json')]
    retained = []
    if (args.only_missing or args.replace_id) and (OUT / 'manifest.json').is_file():
        previous = json.loads((OUT / 'manifest.json').read_text('utf8'))
        expected = {row['id']: row['text'] for row in rows}
        if set(args.replace_id) - expected.keys():
            raise ValueError('Unknown replacement narration ID')
        for entry in previous['entries']:
            if expected.get(entry['id']) != entry['text']:
                raise ValueError('Existing narration identity changed: ' + entry['id'])
            if hashlib.sha256((OUT / entry['file']).read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Existing narration bytes changed: ' + entry['id'])
            if entry['id'] not in args.replace_id:
                retained.append(entry)
        existing = {entry['id'] for entry in retained}
        rows = [row for row in rows if row['id'] not in existing and
                (not args.replace_id or row['id'] in args.replace_id)]
        if not rows:
            print('All narration already exists; preserved existing clips.')
            return
    by_text = {}
    for row in rows:
        by_text.setdefault(row['text'], []).append(row)
    # Synthesize a batch once, then split at verified word boundaries. This
    # avoids dozens of short service requests and keeps one consistent voice.
    texts = list(by_text)
    full_text = " ".join(text.rstrip(".!? ") + ("?" if text.endswith("?") else ".") for text in texts)
    batch_key = hashlib.sha256((VOICE + full_text).encode()).hexdigest()[:20]
    batch_audio, batch_words = CACHE / (batch_key + "-batch.mp3"), CACHE / (batch_key + "-batch.json")
    if not args.isolated and (not batch_audio.exists() or not batch_words.exists()):
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
    samples = decode_audio(str(batch_audio), sampling_rate=24000) if not args.isolated else np.array([])
    boundaries = json.loads(batch_words.read_text(encoding='utf8')) if not args.isolated else []
    letters = lambda text: ''.join(re.findall(r'[^\W_]', text.casefold()))
    cursor, splits = 0, {}
    for text in ([] if args.isolated else texts):
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
    semaphore = asyncio.Semaphore(2)

    async def isolated_audio(text):
        spoken_text = PRONUNCIATION_CONTEXT.get(text, text)
        key = hashlib.sha256((VOICE + '|-10%|isolated-v1|' + spoken_text).encode()).hexdigest()[:20]
        source, timing = CACHE / (key + '.mp3'), CACHE / (key + '.json')
        if not source.exists() or not timing.exists():
            for attempt in range(3):
                try:
                    async with semaphore:
                        data, words = bytearray(), []
                        # Some service deployments return no audio when word
                        # boundaries are requested. Isolated dictionary labels
                        # can safely use a sentence boundary for that complete
                        # label. Context-trimmed pronunciation still requires
                        # word boundaries; never guess its cut position.
                        boundary = 'SentenceBoundary' if (attempt > 0 or args.sentence_boundaries) and spoken_text == text else 'WordBoundary'
                        request_text = spoken_text if spoken_text.endswith(('.', '!', '?')) else spoken_text + '.'
                        async for chunk in edge_tts.Communicate(request_text, VOICE, rate='-10%', boundary=boundary).stream():
                            if chunk['type'] == 'audio':
                                data.extend(chunk['data'])
                            elif chunk['type'] in ('WordBoundary', 'SentenceBoundary'):
                                words.append({'text': chunk['text'], 'start_ms': chunk['offset'] / 10000,
                                              'end_ms': (chunk['offset'] + chunk['duration']) / 10000,
                                              'boundary': chunk['type']})
                        if not data or not words or letters(''.join(w['text'] for w in words)) != letters(spoken_text):
                            raise ValueError('Isolated synthesis does not match the requested text: ' + text)
                        source.write_bytes(data)
                        timing.write_text(json.dumps(words, ensure_ascii=False), 'utf8')
                    break
                except Exception as error:
                    print(f'Voice {text!r}, attempt {attempt+1}: {type(error).__name__}', flush=True)
                    if attempt == 2:raise RuntimeError('Unable to synthesize public label: '+text) from error
                    await asyncio.sleep(2)
        words = json.loads(timing.read_text('utf8'))
        if spoken_text != text:
            # Exact prefix only; never discard meaningful words from runtime input.
            words = words[:len(text.split())]
            if letters(''.join(word['text'] for word in words)) != letters(text):
                raise ValueError('Pronunciation context must begin with the target label')
        samples = decode_audio(str(source), sampling_rate=24000)
        # The service appends roughly one second of silence to short isolated
        # labels. Keep 40ms onset and 100ms tail; there is no adjacent utterance.
        start = max(0, words[0]['start_ms'] - 40)
        end = min(len(samples) / 24, words[-1]['end_ms'] + 100)
        return key + '-trimmed', samples[int(start * 24):int(end * 24)], [
            {**word, 'start_ms': word['start_ms'] - start, 'end_ms': word['end_ms'] - start}
            for word in words], source

    async def build(text, aliases):
        nonlocal completed
        if args.isolated:
            name, audio_samples, words, source_audio = await isolated_audio(text)
        else:
            name = hashlib.sha256((VOICE + '|-10%|' + text).encode()).hexdigest()[:20]
            audio_samples, words = splits[text]
            source_audio = batch_audio
        assert len(audio_samples) > 2400 and np.max(np.abs(audio_samples)) > .01
        pcm = (np.clip(audio_samples, -1, 1) * 32767).astype('<i2')
        target = OUT / (name + '.wav')
        # Write separately, then retain an identical prior result from an
        # interrupted build. Never rewrite a linked published clip in place.
        temporary=target.with_suffix('.wav.tmp')
        with wave.open(str(temporary), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(pcm.tobytes())
        if target.exists():
            if target.read_bytes()!=temporary.read_bytes():
                temporary.unlink()
                raise FileExistsError('Refusing to replace different voice bytes: '+str(target))
            temporary.unlink()
        else:temporary.replace(target)
        energy = np.array([np.sqrt(np.mean(audio_samples[i:i+480] ** 2)) for i in range(0, len(audio_samples), 480)])
        scale = max(.01, float(np.percentile(energy, 90)))
        envelope = np.clip((energy - .004) / scale, 0, 1)
        entry = {'file': target.name, 'duration_ms': round(len(audio_samples) / 24),
                 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                 'source_sha256': hashlib.sha256(source_audio.read_bytes()).hexdigest(),
                 'synthesis': 'isolated-v1' if args.isolated else 'batch-split-v1',
                 'timing_boundary': sorted({w.get('boundary', 'WordBoundary') for w in words}),
                 'source_text': PRONUNCIATION_CONTEXT.get(text, text) if args.isolated else full_text,
                 'envelope_step_ms': 20, 'envelope': np.rint(envelope * 255).astype(int).tolist(),
                 'words': words}
        completed += 1
        if completed % 10 == 0 or completed == len(by_text):
            print(f'{completed}/{len(by_text)} voice clips', flush=True)
        return [{**alias, **entry} for alias in aliases]

    built = await asyncio.gather(*(build(text, aliases) for text, aliases in by_text.items()))
    entries = retained + [entry for group in built for entry in group]
    manifest = {'schema': 'clinic-avatar-voice-v1', 'voice': VOICE, 'language': 'vi-VN',
                'rate': '-10%', 'runtime_network': False,
                'mouth_mode': 'audio-energy and approximate word-vowel shapes; not validated lipreading', 'entries': entries}
    temporary = OUT / 'manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    temporary.replace(OUT / 'manifest.json')
    attribution = OUT / 'ATTRIBUTION.txt.tmp'
    attribution.write_text(
        'Fixed public dictionary labels and reviewed doctor phrases generated at build time\n'
        'with Microsoft Edge online TTS via edge-tts; vi-VN-NamMinhNeural, rate -10%.\n'
        'Local demo assets; no general redistribution license is asserted.\n'
        'Runtime performs no network synthesis and sends no conversation data.\n'
        'Original MP3 hashes and word timings are retained. WAV decoding and energy\n'
        'envelopes were computed locally. Mouth animation is approximate.\n', encoding='utf8')
    attribution.replace(OUT / 'ATTRIBUTION.txt')
    print(json.dumps({'entries': len(entries), 'clips': len(by_text), 'bytes': sum(p.stat().st_size for p in OUT.glob('*.wav'))}))


if __name__ == '__main__':
    asyncio.run(main())
