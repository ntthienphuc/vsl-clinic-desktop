"""Six explicitly labeled, unchanged local prerecorded demo files, not a benchmark."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"E:\\Paper\MultiModel Paper\Data_Labeling_20261104\delivery\VSL100_REVIEWED_20261106_r3")
SPLIT = Path(r"E:\\Paper\MultiModel Paper\VSL100_R3_20261106\training_inputs\r3_loso_01.json")


def main():
    rows = json.loads(SPLIT.read_text("utf8"))
    out = ROOT / "assets/multimodal-samples"
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for cid in ["W066", "W068", "W069", "W072", "W082", "W093"]:
        row = next(r for r in rows if r["split"] == "test" and r["class_id"] == cid and
                   r["take_id"] == 1 and r["camera_id"] == "1")
        source = DATA / row["video_path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["sha256"]
        shutil.copy2(source, out / f"{cid}.mp4")
        entries.append(dict(id=f"mm100:{cid}", label=row["gloss"], model_id=None,
                            category="Video mẫu bộ 100 từ", demo=f"/assets/multimodal-samples/{cid}.mp4",
                            class_id=cid, file=f"{cid}.mp4", provenance=row))
    (out / "manifest.json").write_text(json.dumps(dict(
        scope="Local prerecorded examples. Chosen by class/T01/C1 before integration results; some require review.",
        entries=entries), ensure_ascii=False, indent=2), "utf8")
    print("Staged", len(entries), "unchanged local samples")


if __name__ == "__main__":
    main()
