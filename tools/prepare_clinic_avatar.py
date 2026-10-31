"""Preserve the CC0 male rig and migrate legacy morph-name metadata for glTF 2."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "research/avatar-v0.3/Sakurada_Fumiriya.original.vrm"
raw = source.read_bytes()
length = struct.unpack_from("<I", raw, 12)[0]
gltf = json.loads(raw[20:20 + length])
for mesh in gltf["meshes"]:
    names = [primitive.get("extras", {}).get("targetNames") for primitive in mesh["primitives"]]
    populated = [item for item in names if item]
    if populated:
        assert all(item == populated[0] for item in populated)
        mesh.setdefault("extras", {})["targetNames"] = populated[0]
encoded = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
encoded += b" " * (-len(encoded) % 4)
binary_chunks = raw[20 + length:]
result = struct.pack("<4sII", b"glTF", 2, 20 + len(encoded) + len(binary_chunks))
result += struct.pack("<II", len(encoded), 0x4E4F534A) + encoded + binary_chunks
destination = ROOT / "assets/avatar/ClinicMale.vrm"
destination.write_bytes(result)
provenance = {
    "name": "Sakurada Fumiriya / VRoid Studio beta male sample",
    "license": "CC0-1.0",
    "download_url": "https://raw.githubusercontent.com/madjin/vrm-samples/master/vroid/beta/Sakurada_Fumiriya.vrm",
    "license_reference": "https://vroid.pixiv.help/hc/en-us/articles/360014788554-Sakurada-Fumiriya",
    "embedded_meta": gltf["extensions"]["VRM"]["meta"],
    "original_sha256": hashlib.sha256(raw).hexdigest(),
    "runtime_sha256": hashlib.sha256(result).hexdigest(),
    "modifications": ["Move primitive targetNames into mesh extras for current GLTFLoader",
                      "0.3.4 runtime: PBR materials without toon outlines, reduced eye geometry with transformed morph deltas, widened lower face, short continuous hair, glasses and longer skinned white coat; original rig, hand geometry and skin weights retained"],
}
(ROOT / "assets/avatar/provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"output": str(destination), "sha256": provenance["runtime_sha256"]}))
