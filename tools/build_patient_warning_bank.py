"""Join the existing quiet beep and unchanged voice PCM into one offline clip.

No TTS requests, training, or edits to original voice files. A single media
stream avoids an asynchronous device/file startup between the cue and word.
"""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def warning_pcm(rate: int) -> bytes:
    with wave.open(str(ROOT / 'public/audio/uncertain-beep.wav'), 'rb') as source:
        assert (source.getnchannels(), source.getsampwidth(), source.getcomptype()) == (1, 2, 'NONE')
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2')
        old_rate = source.getframerate()
    positions = np.arange(round(len(samples) * rate / old_rate)) * old_rate / rate
    return np.rint(np.interp(positions, np.arange(len(samples)), samples)).astype('<i2').tobytes()


def main():
    folder = ROOT / 'assets/patient-voice'
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text('utf8'))
    prefixes = {}
    total = 0
    for entry in manifest['entries']:
        original = (folder / entry['file']).read_bytes()
        assert digest(original) == entry['sha256'], 'Original voice changed: ' + entry['file']
        with wave.open(BytesIO(original), 'rb') as source:
            assert (source.getnchannels(), source.getsampwidth(), source.getcomptype()) == (1, 2, 'NONE')
            rate = source.getframerate()
            voice = source.readframes(source.getnframes())
        if rate not in prefixes:
            prefixes[rate] = warning_pcm(rate)
        prefix = prefixes[rate]
        buffer = BytesIO()
        with wave.open(buffer, 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(prefix + voice)
        data = buffer.getvalue()
        target = folder / ('warning-' + entry['file'])
        if target.exists():
            assert target.read_bytes() == data, 'Preserve unexpected existing warning clip: ' + str(target)
        else:
            target.write_bytes(data)
        entry['warning'] = dict(file=target.name, prefix_ms=len(prefix) / 2 / rate * 1000,
                                duration_ms=(len(prefix) + len(voice)) / 2 / rate * 1000,
                                sha256=digest(data), original_sha256=entry['sha256'])
        total += len(data)
    manifest['warning_generation'] = 'Existing quiet 120 ms beep resampled to voice PCM rate, followed by byte-identical original voice PCM; one continuous media file.'
    # Replace the manifest inode so a previously packaged hardlink cannot change.
    temporary = manifest_path.with_suffix('.json.partial')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf8')
    temporary.replace(manifest_path)
    print(json.dumps(dict(clips=len(manifest['entries']), additional_bytes=total,
                          original_voice_bytes_unchanged=True)))


if __name__ == '__main__':
    main()
