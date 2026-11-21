"""Compare every installed payload file with the audited portable build."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(payload: Path, installed: Path, compute: str | None = None) -> dict:
    payload, installed = payload.resolve(strict=True), installed.resolve(strict=True)
    if payload == installed:
        raise ValueError('Installation must be separate from the portable build.')
    all_files = sorted(p for p in payload.rglob('*') if p.is_file())
    problems = []
    preference = installed / 'runtime-preference.json'
    selected = json.loads(preference.read_text('utf8')).get('compute') if preference.exists() else 'gpu'
    if selected not in {'cpu', 'gpu'} or compute and selected != compute:
        problems.append(dict(reason='installed compute preference differs', expected=compute, selected=selected))
    excluded = [p for p in all_files if selected == 'cpu' and p.relative_to(payload).as_posix().startswith('resources/multimodal-runtime/')]
    excluded_set = set(excluded)
    files = [p for p in all_files if p not in excluded_set]
    total = 0
    for source in files:
        relative = source.relative_to(payload)
        destination = (installed / relative).resolve()
        total += source.stat().st_size
        if not destination.is_relative_to(installed):
            problems.append(dict(path=relative.as_posix(), reason='outside installation'))
        elif not destination.is_file():
            problems.append(dict(path=relative.as_posix(), reason='missing'))
        elif destination.stat().st_size != source.stat().st_size or digest(destination) != digest(source):
            problems.append(dict(path=relative.as_posix(), reason='content differs'))
    expected = {p.relative_to(payload).as_posix() for p in files}
    extra = sorted(p.relative_to(installed).as_posix() for p in installed.rglob('*')
                   if p.is_file() and p.relative_to(installed).as_posix() not in expected)
    unexpected = [name for name in extra if name not in {'unins000.exe', 'unins000.dat', 'unins000.msg', 'runtime-preference.json'}]
    if unexpected:
        problems.append(dict(reason='unexpected installed files', paths=unexpected))
    if not (installed / 'unins000.exe').is_file():
        problems.append(dict(reason='Windows uninstaller missing'))
    return dict(checked_at=datetime.now(timezone.utc).isoformat(), payload=str(payload),
                installed=str(installed), files_verified=len(files), payload_bytes=total, compute=selected,
                excluded_gpu_files=len(excluded), saved_gpu_bytes=sum(p.stat().st_size for p in excluded),
                extra_files=extra, receipt_sha256=digest(payload / 'BUILD_RECEIPT.json'),
                launcher_sha256=digest(installed / 'VSL Clinic.exe'),
                problems=problems, passed=not problems,
                scope='Byte parity for every file selected by the installer, including Electron, models, runtime and voice. CPU excludes the entire GPU runtime and rejects leftover GPU files. Runtime and UI checks are separate.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compute', choices=['cpu', 'gpu'])
    args = parser.parse_args()
    report = verify(args.payload, args.installed, args.compute)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), 'utf8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
