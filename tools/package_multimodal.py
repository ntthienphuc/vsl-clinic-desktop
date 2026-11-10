"""Build the 0.5.x portable payload without duplicating immutable model DLLs.

Electron-builder still creates the EXE/app.asar/frontend. This wrapper excludes
large local assets from its copying phase, then links verified immutable source
files into the NEW version folder. It refuses to overwrite any baseline.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from packaging_assets import inactive_multimodal_weights

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_tree(src, dst, skip=lambda p: False):
    for path in src.rglob("*"):
        if not path.is_file() or skip(path) or "__pycache__" in path.parts:
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(path) != digest(target):
                # unlink destination only: never truncate a shared NTFS inode.
                target.unlink()
            else:
                continue
        # Mutable source, scripts, manifests and documents get independent copies.
        if path.suffix.lower() in {".dll", ".pyd", ".pt", ".safetensors", ".onnx", ".bin",
                                   ".gguf", ".wav", ".mp4", ".vrm", ".exe", ".lib"}:
            os.link(path, target)
        else:
            shutil.copy2(path, target)


def require_closed(package):
    if os.name != "nt":
        return
    target = str(package).replace("'", "''")
    command = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '"
               + target + "\\*' } | Select-Object ProcessId,Name | ConvertTo-Json -Compress")
    running = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", command],
                                      text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
    if running:
        raise RuntimeError("Close this candidate and its runtime before packaging: " + running)


def main():
    config = json.loads((ROOT / "package.json").read_text("utf8"))
    version = config["version"]
    if not version.startswith("0.5."):
        raise ValueError("This packager may only write the new 0.5.x integration")
    package = (ROOT / config["build"]["directories"]["output"] / "win-unpacked").resolve()
    allowed = (ROOT.parent / "App" / version).resolve()
    if not package.is_relative_to(allowed) or version == "0.4.1":
        raise ValueError("Refusing to overwrite baseline")
    require_closed(package)
    # Tie the embedded Python archive to the source actually compiled now.
    def engine_inputs():
        files = list((ROOT / "backend").rglob("*.py")) + list((ROOT / "tools/hooks").rglob("*.py"))
        files += [ROOT / "tools/clinic-engine.spec", ROOT / "requirements.txt"]
        return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files) if "__pycache__" not in p.parts}
    before = engine_inputs()
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", "build/engine",
               "--workpath", "build/engine-work", "tools/clinic-engine.spec"]
    subprocess.run(command, cwd=ROOT, check=True)
    if before != engine_inputs():
        raise RuntimeError("Engine inputs changed during build; rebuild before packaging")
    stamp = ROOT / "build/engine/ClinicEngine/ENGINE_BUILD_INFO.json"
    stamp.write_text(json.dumps(dict(schema="clinic-engine-build-v1", created_at=datetime.now(timezone.utc).isoformat(),
        command=command, source_sha256=before,
        executable_sha256=digest(ROOT / "build/engine/ClinicEngine/ClinicEngine.exe")), indent=2), "utf8")
    build = dict(config["build"])
    build["extraResources"] = [{"from": "dist", "to": "frontend", "filter": ["**/*", "!**/*.map"]}]
    build["extraFiles"] = []
    custom = ROOT / "build/multimodal-builder.json"
    custom.parent.mkdir(exist_ok=True)
    custom.write_text(json.dumps(build, ensure_ascii=False, indent=2), "utf8")
    subprocess.run(["npm.cmd", "run", "build"], cwd=ROOT, check=True, shell=True)
    require_closed(package)
    subprocess.run(["node", str(ROOT / "node_modules/electron-builder/cli.js"),
                    "--win", "dir", "--config", str(custom)], cwd=ROOT, check=True)
    inactive = inactive_multimodal_weights(ROOT / "assets")
    for source in inactive:
        target = package / "resources/assets" / source.relative_to(ROOT / "assets")
        if not target.resolve().is_relative_to(package):
            raise ValueError("Inactive weight escaped package")
        if target.is_file():
            target.unlink()  # Remove this generated hardlink, preserving source weights.
    stage_tree(ROOT / "assets", package / "resources/assets",
               skip=lambda p: p in inactive or "reference-source" in p.parts or p.suffix in {".partial", ".map"} or p == ROOT / "assets/language/runtime.zip")
    stage_tree(ROOT / "build/engine/ClinicEngine", package / "resources/engine")
    stage_tree(ROOT / "build/multimodal-runtime", package / "resources/multimodal-runtime")
    stage_tree(ROOT / "multimodal", package / "resources/multimodal")
    stage_tree(ROOT / "licenses", package / "resources/licenses")
    stage_tree(ROOT / "demo", package / "demo")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", package / "resources/THIRD_PARTY_NOTICES.md")
    print("Portable candidate:", package)
    print("Large payload files are immutable ordinary NTFS links, not external-path dependencies.")


if __name__ == "__main__":
    marker = ROOT / "build/PACKAGING_IN_PROGRESS"
    marker.parent.mkdir(exist_ok=True)
    with marker.open("x") as f:
        f.write(str(os.getpid()))
    try:
        main()
    finally:
        marker.unlink(missing_ok=True)
