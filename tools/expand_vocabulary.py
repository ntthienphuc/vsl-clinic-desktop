"""Add local consensus candidates without replacing the existing vocabulary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_assets import ROOT, copy_verified, digest

GROUPS = {
    "Khám bệnh": ["Cảm thấy", "Lạnh", "Nóng", "Nặng", "Nhẹ", "Yếu", "Mạnh", "Rửa tay", "Sạch sẽ", "Giường"],
    "Giao tiếp": ["Có", "Không cần", "Không nên", "Muốn", "Nên", "Chú ý", "Nghe", "Nói", "Nói chuyện", "Gọi", "Tiếp tục", "Thử", "Viết", "Đọc", "Xem", "Sai"],
    "Sinh hoạt": ["Ngon miệng", "Sữa", "Thức dậy", "Đi"],
    "Thời gian": ["Bây giờ", "Buổi sáng", "Buổi trưa", "Buổi chiều", "Buổi tối", "Phút"],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, help='Explicit category-to-label list; only local model labels are accepted.')
    parser.add_argument('--motion-only', action='store_true', help='Keep source video provenance without copying raw videos into the app.')
    args = parser.parse_args()
    groups = json.loads(args.selection.read_text('utf8')) if args.selection else GROUPS
    manifest_path = ROOT / "research/source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata_path = Path(manifest['metadata_path'])
    if digest(metadata_path) != manifest['metadata_sha256']:
        raise ValueError('Original metadata changed')
    source = metadata_path.parent
    catalog = json.loads((ROOT / "assets/catalog.json").read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    vocabulary_path = ROOT / "assets/vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    existing = {word["label"] for word in vocabulary}
    added = []
    for category, labels in groups.items():
        for label in labels:
            if label in existing:
                continue
            word = next(row for row in catalog["words"] if row["label"] == label)
            samples = []
            for row in metadata:
                path = source / "All_cam1" / f"{row['video_id']}.mp4"
                if row["gloss"] == label and path.is_file():
                    samples.append({**row, "path": str(path), "sha256": digest(path)})
            held = next((row for row in samples if row["video_id"] == word["video_id"]), samples[0])
            references = [row for row in samples if row["video_id"] != held["video_id"]]
            if len({row["signer_id"] for row in references}) < 3:
                raise ValueError(f"Insufficient independent signer groups: {label}")
            if not args.motion_only:
                copy_verified(Path(held["path"]), ROOT / f"assets/samples/{word['model_id']:03d}.mp4")
            public = {"id": str(word["model_id"]), "label": label, "model_id": word["model_id"],
                      "category": category, "demo": None if args.motion_only else f"/assets/samples/{word['model_id']:03d}.mp4",
                      "source_kind": "local-consensus"}
            vocabulary.append(public)
            manifest["words"].append({**public, "demo_source": held, "references": references})
            added.append(label)
    for path, value in ((manifest_path, manifest), (vocabulary_path, vocabulary)):
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
        temporary.replace(path)
    print(json.dumps({"added": added, "total": len(vocabulary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
