"""Verify packaged payloads against build inputs and record source fingerprints."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
PACKAGE = ROOT / CONFIG["build"]["directories"]["output"] / "win-unpacked"


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def main():
    records = []
    desktop_files = [path.relative_to(ROOT).as_posix() for path in sorted((ROOT / 'desktop').glob('*.cjs'))]
    archive_script = """
const fs = require('node:fs');
const crypto = require('node:crypto');
const asar = require('@electron/asar');
const files = JSON.parse(process.argv[2]);
const hashes = Object.fromEntries(files.map(name => [name, crypto.createHash('sha256').update(asar.extractFile(process.argv[1], name)).digest('hex')]));
const manifest = asar.extractFile(process.argv[1], 'package.json');
process.stdout.write(JSON.stringify({hashes, manifest: JSON.parse(manifest), manifest_sha256: crypto.createHash('sha256').update(manifest).digest('hex')}));
"""
    archive_result = json.loads(subprocess.check_output(['node', '-e', archive_script, str(PACKAGE / 'resources/app.asar'), json.dumps(desktop_files)], cwd=ROOT, text=True, encoding="utf-8"))
    archived = archive_result["hashes"]
    # electron-builder removes development-only fields and reserializes JSON.
    # Verify every remaining value rather than expecting identical whitespace.
    expected_manifest = {key: value for key, value in CONFIG.items() if key not in {"scripts", "devDependencies", "build"}}
    if archive_result["manifest"] != expected_manifest:
        raise RuntimeError("Packaged application manifest differs from expected production metadata")
    for name, checksum in archived.items():
        if digest(ROOT / name) != checksum:
            raise RuntimeError(f'Packaged desktop code differs: {name}')
    notices = PACKAGE / "resources/THIRD_PARTY_NOTICES.md"
    if not notices.is_file() or digest(notices) != digest(ROOT / "THIRD_PARTY_NOTICES.md"):
        raise RuntimeError("Packaged third-party notices differ")
    for source_folder, destination_folder in [
        (ROOT / "dist", PACKAGE / "resources/frontend"),
        (ROOT / "assets", PACKAGE / "resources/assets"),
        (ROOT / "build/engine/ClinicEngine", PACKAGE / "resources/engine"),
        (ROOT / "licenses", PACKAGE / "resources/licenses"),
        (ROOT / "demo", PACKAGE / "demo"),
    ]:
        for source in sorted(source_folder.rglob("*")):
            if not source.is_file() or source.suffix == ".map" or "reference-source" in source.parts:
                continue
            relative = source.relative_to(source_folder)
            packaged = destination_folder / relative
            original_hash = digest(source)
            if not packaged.is_file() or digest(packaged) != original_hash:
                raise RuntimeError(f"Packaged content differs: {packaged}")
            records.append({"path": packaged.relative_to(PACKAGE).as_posix(), "sha256": original_hash, "bytes": packaged.stat().st_size})
    # Ship the evidence referenced by this demo's handoff, including failed runs.
    # The receipt itself is excluded to avoid a recursive checksum dependency.
    evidence = ROOT / "docs/evidence"
    evidence_files = set(evidence.glob("*2026-10-31*")) | set(evidence.glob("native-*-034*.png")) | {evidence / "motion-audit.json"}
    for source in sorted(evidence_files):
        if not source.is_file():
            continue
        destination = PACKAGE / "docs/evidence" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        checksum = digest(source)
        if digest(destination) != checksum:
            raise RuntimeError(f"Packaged demo evidence differs: {destination}")
        records.append({"path": destination.relative_to(PACKAGE).as_posix(), "sha256": checksum, "bytes": destination.stat().st_size})
    source_records = {}
    for folder in ["src", "backend", "desktop", "tools", "tests"]:
        for source in sorted((ROOT / folder).rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                source_records[source.relative_to(ROOT).as_posix()] = digest(source)
    for name in ["package.json", "package-lock.json", "requirements.txt", "vite.config.ts", "README.md"]:
        source_records[name] = digest(ROOT / name)
    for name in ["README.md", "THIRD_PARTY_NOTICES.md"]:
        shutil.copy2(ROOT / name, PACKAGE / name)
    for source in sorted((ROOT / "docs").glob("*.md")):
        destination = PACKAGE / "docs" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_records[source.relative_to(ROOT).as_posix()] = digest(source)
    report = {
        "schema": "clinic-local-release-receipt-v1",
        "version": CONFIG["version"],
        "package": PACKAGE.relative_to(ROOT).as_posix(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "Uncommitted local project. Build payload parity, not clean-machine or clinical validation.",
        "payload_files_verified": len(records),
        "asar_source_files_verified": archived,
        "packaged_manifest_sha256": archive_result["manifest_sha256"],
        "manifest_verification": "All production metadata equal; electron-builder strips scripts/devDependencies/build and reserializes JSON.",
        "source_sha256": source_records,
        "payload": records,
        "app_asar_sha256": digest(PACKAGE / "resources/app.asar"),
        "launcher_sha256": digest(PACKAGE / "VSL Clinic.exe"),
    }
    report_path = ROOT / "docs/evidence/release-receipt.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(report_path, PACKAGE / "BUILD_RECEIPT.json")
    print(f"Verified {len(records)} packaged payload files; receipt: {report_path}")


if __name__ == "__main__":
    main()
