"""Create one offline Windows setup from an audited portable Clinic payload."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_portable import audit

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def find_compiler(explicit: Path | None) -> Path:
    candidates = [explicit, os.environ.get('INNO_SETUP_COMPILER'), shutil.which('ISCC.exe')]
    for environment in ('LOCALAPPDATA', 'ProgramFiles', 'ProgramFiles(x86)'):
        base = Path(os.environ.get(environment, ''))
        candidates.extend([base / 'Programs/Inno Setup 7/ISCC.exe', base / 'Inno Setup 7/ISCC.exe'])
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError('Install Inno Setup 7, set INNO_SETUP_COMPILER or pass --compiler.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path)
    args = parser.parse_args()
    config = json.loads((ROOT / 'package.json').read_text('utf8'))
    version = config['version']
    payload = (ROOT / config['build']['directories']['output'] / 'win-unpacked').resolve()
    output = ROOT.parent / 'Installer'
    evidence = ROOT.parent / 'Organization' / f'Installer_{version}'
    evidence.mkdir(parents=True, exist_ok=True)
    compiler = find_compiler(args.compiler)
    inventory = audit(payload)
    (evidence / 'payload-inventory.json').write_text(json.dumps(inventory, indent=2), 'utf8')
    if not inventory['passed'] or inventory['version'] != version:
        raise RuntimeError('Portable inventory failed or version differs; rebuild and refresh the receipt first.')
    output.mkdir(exist_ok=True)
    command = [str(compiler), '/Qp', f'/DAppVersion={version}', f'/DPayloadDir={payload}',
               f'/DInstallerOutput={output}', str(ROOT / 'installer/vsl-clinic.iss')]
    with (evidence / 'compiler.log').open('w', encoding='utf8') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    setup = output / f'VSL-Clinic-Setup-{version}.exe'
    if not setup.is_file() or not 0 < setup.stat().st_size < 4 * 1024**3:
        raise RuntimeError('The single setup file is missing or exceeds the Windows executable size limit.')
    report = dict(version=version, created_at=datetime.now(timezone.utc).isoformat(),
                  setup=str(setup), bytes=setup.stat().st_size, sha256=digest(setup),
                  compiler=str(compiler), compiler_sha256=digest(compiler),
                  payload_receipt_sha256=digest(payload / 'BUILD_RECEIPT.json'),
                  inventory_passed=True, installation_verified=False,
                  note='Build receipt only. Verify a real installation and installed app before handoff.')
    (evidence / 'installer-build.json').write_text(json.dumps(report, indent=2), 'utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
