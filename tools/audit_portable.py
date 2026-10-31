"""Read-only inventory and checksum audit of a complete Windows portable folder."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(package: Path) -> dict:
    package = package.resolve(strict=True)
    assets = package / "resources/assets"
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    receipt = read(package / "BUILD_RECEIPT.json")
    problems = []

    def verify(relative: str, checksum: str | None = None):
        path = (package / relative).resolve()
        if not path.is_relative_to(package):
            problems.append({"path": relative, "reason": "outside package"})
        elif not path.is_file():
            problems.append({"path": relative, "reason": "missing"})
        elif checksum and digest(path) != checksum:
            problems.append({"path": relative, "reason": "checksum mismatch"})

    for row in receipt["payload"]:
        verify(row["path"], row["sha256"])
    verify("VSL Clinic.exe", receipt["launcher_sha256"])
    verify("resources/app.asar", receipt["app_asar_sha256"])
    words = read(assets / "vocabulary.json")
    motions = read(assets / "motions/manifest.json")["entries"]
    for row in motions:
        verify("resources/" + row["path"].lstrip("/"), row["sha256"])
    for row in words:
        if row.get("demo"):
            verify("resources/" + row["demo"].lstrip("/"))
    if {w["id"] for w in words} != {m["id"] for m in motions}:
        problems.append({"reason": "vocabulary and motion IDs differ"})
    speech = read(assets / "speech/phowhisper-base-int8/provenance.json")
    for name, checksum in speech["files"].items():
        verify("resources/assets/speech/phowhisper-base-int8/" + name, checksum)
    verify("resources/assets/avatar/ClinicMale.vrm")
    verify("resources/engine/ClinicEngine.exe")
    verify("resources/engine/_internal/python311.dll")
    silero = sorted((package / "resources/engine").rglob("*silero*.onnx"))
    if not silero:
        problems.append({"reason": "Silero VAD ONNX is missing"})
    with (assets / "gloss.csv").open(encoding="utf-8", newline="") as stream:
        labels = list(csv.reader(stream))
    if len(labels) != 400 or {int(row[0]) for row in labels} != set(range(400)):
        problems.append({"reason": "recognizer label count differs from 400"})
    catalog = read(assets / "catalog.json")["words"]
    # These are inherited catalog metadata URLs, not the app's runtime demos.
    old_video_links = [w for w in catalog if w.get("video_path")]
    present_catalog_videos = sum((package / "resources" / w["video_path"].lstrip("/")).is_file() for w in old_video_links)
    files = [p for p in package.rglob("*") if p.is_file()]
    return {
        "schema": "clinic-portable-inventory-v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "version": receipt["version"],
        "distribution": "portable folder, not a single-file executable or installer",
        "receipt_payload_files_verified": len(receipt["payload"]),
        "launcher_sha256": digest(package / "VSL Clinic.exe"),
        "app_asar_sha256": digest(package / "resources/app.asar"),
        "package_files": len(files),
        "package_bytes": sum(p.stat().st_size for p in files),
        "recognizer_labels": len(labels),
        "avatar_vocabulary": len(words),
        "motion_entries": len(motions),
        "sample_videos": len(list((assets / "samples").glob("*.mp4"))),
        "demo_kit_videos": len(list((package / "demo").rglob("*.mp4"))),
        "raw_reference_videos": len(list((assets / "reference-source").rglob("*.mp4"))),
        "inherited_catalog_video_links": len(old_video_links),
        "inherited_catalog_video_files_present": present_catalog_videos,
        "speech_files_verified": list(speech["files"]),
        "silero_payload": [p.relative_to(package).as_posix() for p in silero],
        "recognition_models": [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted((assets / "models").glob("*")) if p.is_file()],
        "problems": problems,
        "passed": not problems,
        "scope": "Checks bundled runtime assets and existing build receipt. Raw research references and all 400 dictionary videos are not required by the current runtime and are reported separately. Does not prove clean-machine compatibility or signer comprehension.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.package)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
