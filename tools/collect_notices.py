"""Collect installed license texts and asset metadata for the local portable build."""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import struct
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "licenses"


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def collect() -> None:
    DESTINATION.mkdir(exist_ok=True)
    inventory = {"scope": "Local build environment inventory; includes development dependencies, not an assertion that all are shipped.", "python": [], "javascript": []}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        records = []
        for entry in distribution.files or []:
            if not any(part.lower().startswith(("license", "copying", "notice", "authors")) for part in entry.parts):
                continue
            source = Path(distribution.locate_file(entry))
            if not source.is_file():
                continue
            destination = DESTINATION / "python" / safe(name) / Path(*entry.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            records.append(destination.relative_to(DESTINATION).as_posix())
        inventory["python"].append({"name": name, "version": distribution.version, "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License"), "texts": records})
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    for relative, package in lock["packages"].items():
        if not relative or package.get("dev"):
            continue
        folder = ROOT / relative
        records = []
        for source in folder.iterdir():
            if source.is_file() and source.name.lower().startswith(("license", "copying", "notice")):
                destination = DESTINATION / "javascript" / safe(relative.removeprefix("node_modules/")) / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                records.append(destination.relative_to(DESTINATION).as_posix())
        inventory["javascript"].append({"path": relative, "version": package.get("version"), "license": package.get("license"), "texts": records})
    for name in ["LICENSE", "LICENSES.chromium.html"]:
        source = ROOT / "node_modules/electron/dist" / name
        if source.exists():
            destination = DESTINATION / "electron" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    font_license = DESTINATION / "fonts/Nunito-OFL.txt"
    font_license.parent.mkdir(parents=True, exist_ok=True)
    if not font_license.exists():
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/OFL.txt", font_license)
    avatar_provenance = json.loads((ROOT / "assets/avatar/provenance.json").read_text(encoding="utf-8"))
    inventory["avatars"] = []
    for filename, source in [
        ("ClinicMale.vrm", avatar_provenance["download_url"]),
        ("VRM1_Constraint_Twist_Sample.vrm", "https://github.com/pixiv/three-vrm/tree/release/packages/three-vrm/examples/models"),
    ]:
        avatar = ROOT / "assets/avatar" / filename
        data = avatar.read_bytes()
        gltf = json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])
        extension = gltf["extensions"].get("VRMC_vrm") or gltf["extensions"]["VRM"]
        record = {"file": filename, "sha256": hashlib.sha256(data).hexdigest(),
                  "source": source, "metadata": extension["meta"], "active": filename == "ClinicMale.vrm"}
        if record["active"]:
            if record["sha256"] != avatar_provenance["runtime_sha256"]:
                raise ValueError("Runtime avatar no longer matches its provenance")
            record["provenance"] = avatar_provenance
        inventory["avatars"].append(record)
    speech_folder = ROOT / "assets/speech/phowhisper-base-int8"
    speech_license = DESTINATION / "models/PhoWhisper-base-LICENSE.txt"
    speech_license.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(speech_folder / "LICENSE", speech_license)
    inventory["speech_model"] = json.loads((speech_folder / "provenance.json").read_text(encoding="utf-8"))
    inventory["speech_model"]["license_text"] = speech_license.relative_to(DESTINATION).as_posix()
    from faster_whisper.utils import get_assets_path
    vad_model = Path(get_assets_path()) / 'silero_vad_v6.onnx'
    vad_license = DESTINATION / 'models/Silero-VAD-LICENSE.txt'
    if not vad_license.exists():
        urllib.request.urlretrieve('https://raw.githubusercontent.com/snakers4/silero-vad/master/LICENSE', vad_license)
    inventory['speech_activity_model'] = {
        'name': 'Silero VAD v6 ONNX bundled by faster-whisper 1.2.1',
        'source': 'https://github.com/snakers4/silero-vad',
        'sha256': hashlib.sha256(vad_model.read_bytes()).hexdigest(),
        'license': 'MIT', 'license_text': vad_license.relative_to(DESTINATION).as_posix(),
        'runtime': 'CPU, one thread; recurrent state per microphone; no network',
    }
    (DESTINATION / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected notices for {len(inventory['python'])} Python distributions and {len(inventory['javascript'])} production JavaScript packages.")


if __name__ == "__main__":
    collect()
