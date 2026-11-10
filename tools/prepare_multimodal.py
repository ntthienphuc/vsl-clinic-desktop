"""Stage the pinned research contract; never modify the research application.

Large immutable weights may share NTFS file data through hard links. All paths
resolve inside Clinic; deleting/moving the research folder does not break them.
Never write an existing staged weight in place.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"E:\Project\VSL Projects\vsl-translator-multimodal-v2")
DEST = ROOT / "assets/multimodal100"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def stage(source, target, expected=None):
    checksum = digest(source)
    if expected and checksum != expected:
        raise ValueError(f"Source hash mismatch: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError(f"Refusing to overwrite staged asset: {target}")
    elif source.stat().st_size > 10_000_000 and source.drive == target.drive:
        os.link(source, target)
    else:
        shutil.copy2(source, target)
    return dict(path=target.relative_to(DEST).as_posix(), sha256=checksum, bytes=target.stat().st_size)


def prepare():
    manifest = json.loads((SOURCE / "models/MODEL_MANIFEST.json").read_text("utf8"))
    records = []
    for record in manifest["files"]:
        relative = Path(record["path"])
        records.append(stage(SOURCE / relative, DEST / relative, record["sha256"]))
    for relative in ["models/MODEL_MANIFEST.json", "server/engine.py", "server/preprocess.py",
                     "server/segmentation.py", "server/vendor/legacy_arm_utils.py",
                     "server/requirements.lock.txt", "packaging/windows_server/ASSET_NOTICES.md"]:
        records.append(stage(SOURCE / relative, DEST / relative))
    for relative in ["server/__init__.py", "server/vendor/__init__.py"]:
        source = SOURCE / relative
        if source.exists():
            records.append(stage(source, DEST / relative))
        else:
            (DEST / relative).touch(exist_ok=True)
    foundations = {}
    for name, rec in manifest["foundations"].items():
        relative = "models/foundations/" + name
        records.append(stage(Path(rec["path"]), DEST / relative, rec["sha256"]))
        foundations[name] = relative
    labels = json.loads((DEST / "models/classes.json").read_text("utf8"))
    voice = json.loads((ROOT / "assets/patient-voice/manifest.json").read_text("utf8"))
    normalize = lambda s: " ".join(unicodedata.normalize("NFC", s).casefold().split())
    by_text = {normalize(e["text"]): e for e in voice["entries"]}
    with (ROOT / "assets/gloss.csv").open(encoding="utf-8-sig", newline="") as f:
        legacy = {normalize(text): int(index) for index, text in csv.reader(f)}
    mapping = []
    for index, label in enumerate(labels):
        gloss = label["gloss"]
        entry = by_text.get(normalize(gloss))
        mapping.append(dict(class_id=label["class_id"], class_index=index,
            original_gloss=gloss, display_text=gloss,
            canonical_concept_id="mm100:" + label["class_id"],
            legacy_label_candidate=legacy.get(normalize(gloss)),
            mapping_scope="exact lexical label only; no motion equivalence asserted",
            voice_key=entry["id"] if entry else "mm100-" + label["class_id"],
            voice_file=entry["file"] if entry else "mm100-" + label["class_id"] + ".wav"))
    (DEST / "label_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), "utf8")
    deployment = dict(schema="clinic-mm100-deployment-v1", contract=manifest["contract"],
        source_manifest_sha256=digest(DEST / "models/MODEL_MANIFEST.json"),
        foundations=foundations, files=records,
        storage_policy="No camera frames, keypoints, mouth pixels or conversation are persisted at runtime.",
        runtime_policy="Dedicated stdio worker; one camera owner; fusion only; no automatic 400-class fallback.")
    (DEST / "DEPLOYMENT.json").write_text(json.dumps(deployment, ensure_ascii=False, indent=2), "utf8")
    print(json.dumps(dict(verified_records=len(records), labels=len(mapping),
                         existing_voices=sum(m["voice_key"].isdigit() for m in mapping)), indent=2))


if __name__ == "__main__":
    prepare()
