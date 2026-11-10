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


def verify(payload: Path, installed: Path) -> dict:
    payload, installed = payload.resolve(strict=True), installed.resolve(strict=True)
    if payload == installed:
        raise ValueError('Installation must be separate from the portable build.')
    files = sorted(p for p in payload.rglob('*') if p.is_file())
    problems = []
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
    unexpected = [name for name in extra if name not in {'unins000.exe', 'unins000.dat', 'unins000.msg'}]
    if unexpected:
        problems.append(dict(reason='unexpected installed files', paths=unexpected))
    if not (installed / 'unins000.exe').is_file():
        problems.append(dict(reason='Windows uninstaller missing'))
    return dict(checked_at=datetime.now(timezone.utc).isoformat(), payload=str(payload),
                installed=str(installed), files_verified=len(files), payload_bytes=total,
                extra_files=extra, receipt_sha256=digest(payload / 'BUILD_RECEIPT.json'),
                launcher_sha256=digest(installed / 'VSL Clinic.exe'),
                problems=problems, passed=not problems,
                scope='Byte parity for every portable file, including Electron, models, runtime and voice. Runtime and UI checks are separate.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.payload, args.installed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), 'utf8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
