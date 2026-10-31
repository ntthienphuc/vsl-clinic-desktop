"""Export real server timelines for renderer and actual-rig contract checks."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.playback import load_join_profile
from backend.session import ClinicSession
from backend.text_to_sign import TextPlanner

assets = ROOT / "assets"
words = json.loads((assets / "vocabulary.json").read_text(encoding="utf-8"))
catalog = json.loads((assets / "phrases.json").read_text(encoding="utf-8"))
bank = json.loads((assets / "motions/manifest.json").read_text(encoding="utf-8"))
session = ClinicSession(TextPlanner(words, catalog), {item["id"]: item["duration_ms"] for item in bank["entries"]}, load_join_profile(assets))

def timeline(text):
    session.reset()
    session.send(text, "sign")
    result = session.playback
    result["started_at_ms"] = 1000
    result["status"] = "playing"
    return result

result = {"single": {word["id"]: timeline(word["label"]) for word in words},
          "sentences": [timeline(entry["text"]) for entry in session.planner.entries] +
                       [timeline("Bác sĩ uống nước. Bạn có đau không? Cảm ơn.")]}
print(json.dumps(result, ensure_ascii=False))
