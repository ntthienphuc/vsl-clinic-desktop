"""Verify the preserved 0.5.2 payload and pinned research inputs without writing them."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'Organization/VoicePreviewCPU_2026-11-10'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-installer', type=Path, required=True)
    args = parser.parse_args()
    original = json.loads((ROOT.parent / 'Organization/MultimodalIntegration_2026-11-09/release-051/PRESERVATION.json').read_text('utf8'))
    rows = [dict(path=r['path'], sha256=r['sha256'],
                 unchanged=Path(r['path']).is_file() and digest(Path(r['path'])) == r['sha256']) for r in original['files']]
    receipt_path = OUT / 'baseline-052-receipt.json'
    receipt = json.loads(receipt_path.read_text('utf8'))
    baseline = ROOT.parent / 'App/0.5.2/win-unpacked'
    differences = []
    for row in receipt['payload']:
        file = (baseline / row['path']).resolve()
        if not file.is_relative_to(baseline.resolve()) or not file.is_file() or digest(file) != row['sha256']:
            differences.append(row['path'])
    expected_installer = json.loads((OUT / 'BASELINE.json').read_text('utf8'))['baseline_installer_sha256']
    checks = dict(research_and_original_inputs=all(r['unchanged'] for r in rows),
        baseline_payload=not differences,
        baseline_receipt=digest(baseline / 'BUILD_RECEIPT.json') == digest(receipt_path),
        baseline_executable=digest(baseline / 'VSL Clinic.exe') == receipt['launcher_sha256'],
        baseline_asar=digest(baseline / 'resources/app.asar') == receipt['app_asar_sha256'],
        baseline_installer=digest(args.baseline_installer) == expected_installer.lower())
    result = dict(checked_at=datetime.now(timezone.utc).isoformat(), checks=checks,
        baseline_files_verified=len(receipt['payload']), baseline_differences=differences,
        baseline_installer=str(args.baseline_installer), original_inputs=rows, passed=all(checks.values()))
    (OUT / 'PRESERVATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps({k:v for k,v in result.items() if k != 'original_inputs'}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
