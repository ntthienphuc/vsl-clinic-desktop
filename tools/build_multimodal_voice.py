"""Add missing fixed public dictionary labels; no patient text/network at runtime."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_patient_voice_bank import build, CACHE


def main():
    path = ROOT / "assets/patient-voice/manifest.json"
    bank = json.loads(path.read_text("utf8"))
    mapping = json.loads((ROOT / "assets/multimodal100/label_mapping.json").read_text("utf8"))
    by_id = {e["id"]: e for e in bank["entries"]}
    CACHE.mkdir(parents=True, exist_ok=True)
    for row in mapping:
        if row["voice_key"] in by_id:
            continue
        entry = build(dict(id=row["voice_key"], text=row["display_text"]))
        bank["entries"].append(entry)
        by_id[entry["id"]] = entry
        path.write_text(json.dumps(bank, ensure_ascii=False, indent=2), "utf8")
        print("Prepared", entry["id"], entry["text"], flush=True)
    assert all(row["voice_key"] in by_id for row in mapping)
    print("Coverage: 100/100; total bank entries:", len(bank["entries"]))


if __name__ == "__main__":
    main()
