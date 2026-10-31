"""Copy explicit local inputs into the new app; never modifies a source project."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
GLOSSES = [
    "Bác sĩ", "Y tá", "Bệnh viện", "Khám bệnh", "Đau", "Mệt", "Khỏe", "Ốm",
    "Ăn", "Uống", "Nước", "Nghỉ ngơi", "Ngủ", "Cần", "Giúp đỡ", "Dừng lại",
    "Cảm ơn", "Xin lỗi", "Đúng", "Đồng ý",
]


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def copy_verified(source: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and digest(destination) != digest(source):
        raise RuntimeError(f"Refusing to replace a different asset: {destination}")
    if not destination.exists():
        shutil.copy2(source, destination)
    return {"path": destination.relative_to(ROOT).as_posix(), "sha256": digest(destination), "source": str(source)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--translator", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    source = args.translator.resolve()
    catalog = json.loads((source / "vsl_server/dictionary_manifest.json").read_text(encoding="utf-8"))
    metadata_path = source / "All_cam1/All_cam1_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = []
    for relative, target in [
        ("vsl_server/models/slgcn_bone_all_cams.onnx", "assets/models/slgcn_bone_all_cams.onnx"),
        ("vsl_server/gloss.csv", "assets/gloss.csv"),
        ("android/app/src/main/assets/pose_landmarker_lite.task", "assets/models/pose_landmarker_lite.task"),
        ("android/app/src/main/assets/hand_landmarker.task", "assets/models/hand_landmarker.task"),
        ("assets/fonts/Nunito-Regular.ttf", "public/fonts/Nunito-Regular.ttf"),
        ("assets/fonts/Nunito-Bold.ttf", "public/fonts/Nunito-Bold.ttf"),
    ]:
        records.append(copy_verified(source / relative, ROOT / target))
    selected = []
    for label in GLOSSES:
        word = next(word for word in catalog["words"] if word["label"] == label)
        rows = [row for row in metadata if row["gloss"] == label]
        samples = []
        for row in rows:
            video = source / "All_cam1/All_cam1" / f"{row['video_id']}.mp4"
            if video.is_file():
                samples.append({**row, "path": str(video), "sha256": digest(video)})
        if len(samples) < 3:
            raise RuntimeError(f"Not enough reference recordings for {label}")
        # Reserve one recording before reference selection. No label-based inference shortcut.
        held_out = next((row for row in samples if row["video_id"] == word["video_id"]), samples[0])
        demo_path = ROOT / "assets/samples" / f"{word['model_id']:03d}.mp4"
        records.append(copy_verified(Path(held_out["path"]), demo_path))
        selected.append({
            "id": str(word["model_id"]),
            "label": label,
            "model_id": word["model_id"],
            "category": "Khám bệnh" if label in GLOSSES[:8] else "Giao tiếp",
            "demo": f"/assets/samples/{word['model_id']:03d}.mp4",
            "demo_source": held_out,
            "references": [row for row in samples if row["video_id"] != held_out["video_id"]],
        })
    (ROOT / "assets/catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "assets/vocabulary.json").write_text(json.dumps([
        {key: value for key, value in row.items() if key not in {"references", "demo_source"}}
        for row in selected
    ], ensure_ascii=False, indent=2), encoding="utf-8")
    research = ROOT / "research"
    research.mkdir(exist_ok=True)
    (research / "source-manifest.json").write_text(json.dumps({
        "schema": "clinic-reference-sources-v1",
        "metadata_path": str(metadata_path),
        "metadata_sha256": digest(metadata_path),
        "scope": "User's local development data; no external upload or publication.",
        "signer_identity": "Declared source metadata, not independently verified.",
        "words": selected,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (research / "asset-provenance.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(catalog['words'])} labels, {len(selected)} demo words and {sum(len(w['references']) for w in selected)} candidate references.")


if __name__ == "__main__":
    main()
