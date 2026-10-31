"""Restore the exact local model/video inputs without downloading or overwriting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def confined(root: Path, relative: str) -> Path:
    name = PurePosixPath(relative)
    if name.is_absolute() or ".." in name.parts or ":" in relative or "\\" in relative:
        raise ValueError(f"Invalid asset path: {relative}")
    root = root.resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f"Asset escapes project directory: {relative}")
    return target


def restore_one(root: Path, source: Path | None, entry: dict) -> bool:
    target = confined(root, entry["path"])
    expected = entry["sha256"]
    if target.exists():
        if not target.is_file() or digest(target) != expected:
            raise ValueError(f"Existing asset differs; preserved: {entry['path']}")
        return False
    if source is None:
        raise FileNotFoundError(entry["path"])
    original = confined(source, entry["path"])
    if not original.is_file():
        raise FileNotFoundError(entry["path"])
    if digest(original) != expected:
        raise ValueError(f"Source checksum differs: {entry['path']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects a file created since the earlier check.
    with target.open("xb") as out:
        with original.open("rb") as incoming:
            shutil.copyfileobj(incoming, out, length=1024 * 1024)
    if digest(target) != expected:
        raise ValueError(f"Restored checksum differs: {entry['path']}; inspect this new file")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", type=Path, help="Existing complete vsl-clinic-desktop folder")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "local-assets-manifest.json").read_text(encoding="utf-8"))
    copied, problems = 0, []
    for entry in manifest["files"]:
        try:
            copied += restore_one(ROOT, args.source, entry)
        except (OSError, ValueError) as error:
            problems.append(str(error))
    print(json.dumps({"checked": len(manifest["files"]), "copied": copied, "problems": problems}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
