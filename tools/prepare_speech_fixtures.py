"""Generate explicitly synthetic Vietnamese QA utterances, outside runtime assets.

Only the fixed public test phrases below are sent to Google Translate TTS.
No microphone audio, conversation data, credentials or patient data is sent.
The app itself remains fully local/offline.
"""
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'research/speech-samples/synthetic-vi'
PHRASES = {
    'drink-water': 'Uống nước.',
    'pain-question': 'Bạn có đau không?',
    'unsupported-feeling': 'Bạn cảm thấy thế nào?',
    'unsupported-dose': 'Uống thuốc hai viên.',
}


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    for name, text in PHRASES.items():
        path = DESTINATION / (name + '.mp3')
        url = 'https://translate.google.com/translate_tts?' + urllib.parse.urlencode({
            'ie': 'UTF-8', 'client': 'tw-ob', 'tl': 'vi', 'q': text,
        })
        if not path.exists():
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(2 * 1024 * 1024)
                if 'audio' not in response.headers.get('Content-Type', ''):
                    raise ValueError('Expected synthetic audio')
            path.write_bytes(data)
        records.append({'file': path.name, 'text': text, 'url': url,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        print(name, path.stat().st_size, flush=True)
    (DESTINATION / 'provenance.json').write_text(json.dumps({
        'kind': 'synthetic TTS smoke fixtures, not human microphone evaluation',
        'runtime_distribution': False, 'records': records,
    }, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
