"""Add local consensus candidates without replacing the existing vocabulary."""
from __future__ import annotations

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
    source = ROOT.parent
    catalog = json.loads((ROOT / "assets/catalog.json").read_text(encoding="utf-8"))
    metadata = json.loads((source / "All_cam1/All_cam1_metadata.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "research/source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vocabulary_path = ROOT / "assets/vocabulary.json"
    vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    existing = {word["label"] for word in vocabulary}
    added = []
    for category, labels in GROUPS.items():
        for label in labels:
            if label in existing:
                continue
            word = next(row for row in catalog["words"] if row["label"] == label)
            samples = []
            for row in metadata:
                path = source / "All_cam1/All_cam1" / f"{row['video_id']}.mp4"
                if row["gloss"] == label and path.is_file():
                    samples.append({**row, "path": str(path), "sha256": digest(path)})
            held = next((row for row in samples if row["video_id"] == word["video_id"]), samples[0])
            references = [row for row in samples if row["video_id"] != held["video_id"]]
            if len({row["signer_id"] for row in references}) < 3:
                raise ValueError(f"Insufficient independent signer groups: {label}")
            copy_verified(Path(held["path"]), ROOT / f"assets/samples/{word['model_id']:03d}.mp4")
            public = {"id": str(word["model_id"]), "label": label, "model_id": word["model_id"],
                      "category": category, "demo": f"/assets/samples/{word['model_id']:03d}.mp4",
                      "source_kind": "local-consensus"}
            vocabulary.append(public)
            manifest["words"].append({**public, "demo_source": held, "references": references})
            added.append(label)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    vocabulary_path.write_text(json.dumps(vocabulary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"added": added, "total": len(vocabulary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
