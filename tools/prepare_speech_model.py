"""Convert a pinned official PhoWhisper checkpoint for offline CPU inference.

Build tool only: torch/transformers never ship inside the desktop runtime.
Run with .model-tools/Scripts/python.exe after installing torch CPU,
transformers==4.53.3, ctranslate2==4.6.2 and huggingface-hub==0.34.4.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import urllib.request

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_XET"] = "1"

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "vinai/PhoWhisper-base"
REVISION = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
DESTINATION = ROOT / "assets/speech/phowhisper-base-int8"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    from ctranslate2.converters import TransformersConverter
    from huggingface_hub import snapshot_download

    receipt_path = DESTINATION / "provenance.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("revision") != REVISION:
            raise RuntimeError("An existing model has another revision; select a new output directory.")
        for relative, digest in receipt["files"].items():
            if sha256(DESTINATION / relative) != digest:
                raise RuntimeError(f"Existing model checksum mismatch: {relative}")
        print("Verified existing offline model.")
        return
    if DESTINATION.exists():
        raise RuntimeError("Incomplete output exists. Inspect it before retrying conversion.")
    source = Path(snapshot_download(
        REPOSITORY,
        revision=REVISION,
        local_dir=ROOT / "research/model-source/PhoWhisper-base",
        allow_patterns=["*.json", "*.txt", "*.bin", "README.md"],
        max_workers=2,
    ))
    print("Converting official checkpoint to CTranslate2 INT8.", flush=True)
    converter = TransformersConverter(str(source), copy_files=["tokenizer.json", "preprocessor_config.json"])
    converter.convert(str(DESTINATION), quantization="int8")
    license_url = "https://raw.githubusercontent.com/VinAIResearch/PhoWhisper/main/LICENSE"
    with urllib.request.urlopen(license_url, timeout=30) as response:
        license_bytes = response.read()
    (DESTINATION / "LICENSE").write_bytes(license_bytes)
    receipt = {
        "schema": "clinic-speech-model-v1",
        "repository": REPOSITORY,
        "revision": REVISION,
        "source_url": f"https://huggingface.co/{REPOSITORY}/tree/{REVISION}",
        "source_checkpoint_sha256": sha256(source / "pytorch_model.bin"),
        "license_url": license_url,
        "license": "BSD-3-Clause",
        "quantization": "int8",
        "language": "vi",
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "ctranslate2", "huggingface-hub")},
        "files": {path.name: sha256(path) for path in sorted(DESTINATION.iterdir()) if path.is_file()},
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(DESTINATION), "bytes": sum(p.stat().st_size for p in DESTINATION.iterdir())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
