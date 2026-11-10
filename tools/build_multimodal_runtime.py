"""Build an isolated, relocatable CPython runtime from verified local installs.

No venv or absolute Python installation is used at runtime. Immutable files
are hard-linked on the same NTFS volume to avoid duplicating ~5 GB of CUDA DLLs.
They remain ordinary portable files, not junctions/symlinks. Never mutate them
in place. A release copy is audited by hashes.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(r"C:\\Users\thien\AppData\Local\Programs\Python\Python311")
ENV = Path(r"E:\\Project\VSL Projects\vsl-translator-multimodal-v2\.venv")
OUT = ROOT / "build/multimodal-runtime"


def copy_immutable(src, dst):
    if dst.exists():
        if src.stat().st_size != dst.stat().st_size:
            raise ValueError(f"Existing runtime file differs: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.drive == dst.drive:
        os.link(src, dst)
    else:
        shutil.copy2(src, dst)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["python.exe", "python3.dll", "python311.dll", "vcruntime140.dll",
                 "vcruntime140_1.dll", "LICENSE.txt"]:
        copy_immutable(BASE / name, OUT / name)
    for folder in ["DLLs", "Lib"]:
        for source in (BASE / folder).rglob("*"):
            if not source.is_file() or any(p in {"site-packages", "__pycache__", "test", "tests", "ensurepip", "idlelib", "tkinter"} for p in source.parts):
                continue
            copy_immutable(source, OUT / source.relative_to(BASE))
    packages = ENV / "Lib/site-packages"
    # Optional accelerator frameworks and build/test tooling are not needed by
    # the actual source graph. Preserve runtime metadata/licenses for all others.
    excluded = ("jax", "jaxlib", "pytest", "_pytest", "pip", "setuptools")
    for source in packages.rglob("*"):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(packages)
        if any(relative.parts[0] == n or relative.parts[0].startswith(n + "-") for n in excluded):
            continue
        copy_immutable(source, OUT / "Lib/site-packages" / relative)
    # Isolated path search ignores user/system site-packages and PYTHONPATH.
    (OUT / "python311._pth").write_text(".\nLib\nDLLs\nLib/site-packages\n", "utf8")
    records = []
    for file in OUT.rglob("*"):
        if not file.is_file() or file.name == "RUNTIME_MANIFEST.json":
            continue
        h = hashlib.sha256()
        with file.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024**2), b""):
                h.update(block)
        records.append(dict(path=file.relative_to(OUT).as_posix(), bytes=file.stat().st_size, sha256=h.hexdigest()))
    (OUT / "RUNTIME_MANIFEST.json").write_text(json.dumps(dict(
        schema="clinic-mm100-python-runtime-v1", python="3.11.9", torch="2.6.0+cu124",
        runtime_resolution="python311._pth; fully relative; no site import",
        storage="ordinary files; immutable NTFS hardlinks where on same drive",
        files=records), indent=2), "utf8")
    print(json.dumps(dict(files=len(records), logical_gb=sum(r["bytes"] for r in records) / 1e9)))


if __name__ == "__main__":
    main()
