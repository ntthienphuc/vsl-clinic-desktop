"""Fetch pinned, hash-verified offline language-assistant assets from their publishers."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/language'
REVISION = '23749fefcc72300e3a2ad315e1317431b06b590a'
MODEL_SHA = '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031'
RUNTIME_SHA = '16c38cd9ff7487bf118a37808784245a2d639d844110f21fe9b373aaa40ff511'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.partial')
        request = urllib.request.Request(url, headers={'User-Agent': 'VSL-Clinic-Asset-Preparation/0.4.0'})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        if expected and digest(temporary) != expected:
            raise ValueError('Publisher hash mismatch: ' + str(path))
        temporary.replace(path)
    if expected and digest(path) != expected:
        raise ValueError('Existing asset hash mismatch: ' + str(path))
    return {'path': str(path.relative_to(OUT)), 'url': url, 'sha256': digest(path), 'bytes': path.stat().st_size}


def main():
    model = fetch(f'https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/{REVISION}/Qwen3-0.6B-Q8_0.gguf', OUT/'Qwen3-0.6B-Q8_0.gguf', MODEL_SHA)
    print('Model hash verified', flush=True)
    archive = fetch('https://github.com/ggml-org/llama.cpp/releases/download/b12034/llama-b12034-bin-win-cpu-x64.zip', OUT/'runtime.zip', RUNTIME_SHA)
    destination = (OUT/'runtime').resolve()
    with zipfile.ZipFile(OUT/'runtime.zip') as bundle:
        for member in bundle.infolist():
            target = (destination/member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Unsafe archive member')
        bundle.extractall(destination)
    licenses = [
        fetch(f'https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/{REVISION}/LICENSE', OUT/'QWEN_LICENSE'),
        fetch('https://raw.githubusercontent.com/ggml-org/llama.cpp/b12034/LICENSE', OUT/'LLAMA_CPP_LICENSE'),
    ]
    executable = list(destination.rglob('llama-server.exe'))
    assert len(executable) == 1
    manifest = {'schema': 'clinic-local-language-v1', 'model': 'Qwen3-0.6B-Q8_0', 'revision': REVISION,
                'runtime_version': 'llama.cpp-b12034', 'model_file': model, 'runtime_archive': archive,
                'runtime_executable': str(executable[0].relative_to(OUT)), 'licenses': licenses,
                'purpose': 'Offline reviewed-phrase retrieval suggestions only; never automatic clinical interpretation.',
                'runtime_files': [{'path': str(p.relative_to(OUT)), 'sha256': digest(p), 'bytes': p.stat().st_size}
                                  for p in destination.rglob('*') if p.is_file()]}
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'model_mb': model['bytes']/1024**2, 'runtime': manifest['runtime_executable']}), flush=True)


if __name__ == '__main__':
    main()
