"""Fingerprint existing authorized local inputs and the selected build runtime.

Never downloads assets or changes their bytes. Original asset rows remain so a
source restore still includes research inputs; obsolete runtime rows are replaced
by the active self-contained runtime. Review the manifest diff before committing.
"""
import hashlib
import json
from pathlib import Path

from packaging_assets import multimodal_runtime, extra_multimodal_runtimes

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'local-assets-manifest.json'
    old = json.loads(path.read_text('utf8'))
    names = {row['path'] for row in old['files'] if not row['path'].startswith('build/multimodal-runtime')}
    runtime = multimodal_runtime(ROOT)
    runtimes = [runtime, *[source for source, _ in extra_multimodal_runtimes(ROOT)]]
    for folder in [*runtimes, ROOT / 'assets/avatar-voice', ROOT / 'assets/patient-voice', ROOT / 'assets/reference-source/qipedc']:
        names.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts
                     and (folder in runtimes or p.suffix in {'.wav', '.mp4'}))
    rows = []
    for name in sorted(names):
        file = (ROOT / name).resolve(strict=True)
        if not file.is_relative_to(ROOT):
            raise ValueError('Input escapes source: ' + name)
        with file.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        rows.append(dict(path=name, bytes=file.stat().st_size, sha256=checksum))
    old.update(version=json.loads((ROOT / 'package.json').read_text('utf8'))['version'],
               scope='Exact authorized local source assets, including preserved originals and active CPU/GPU runtime. Restore from a complete authorized Clinic Source folder; no downloads.',
               files=rows)
    path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps(dict(version=old['version'], files=len(rows), runtime=runtime.name)))


if __name__ == '__main__':
    main()
