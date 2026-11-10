"""Bounded paired-frame check; two original clips, no timing/threshold tuning."""
from pathlib import Path
import sys
import json
import time
import zipfile
import hashlib
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.landmarks import LandmarkDetector
from backend.recognition import Recognizer

OUT = ROOT.parent / "Organization/ModesPilot_2026-11-10"
cv2.setNumThreads(1)
original = {}
with zipfile.ZipFile(OUT / "source-before-052.zip") as archive:
    exec(compile(archive.read("backend/landmarks.py"), "preserved-landmarks.py", "exec"), original)


def vector(frame):
    rows = []
    for name, count in [("pose_landmarks", 33), ("left_hand_landmarks", 21), ("right_hand_landmarks", 21)]:
        component = getattr(frame, name)
        rows.extend([[p.x, p.y, p.z, p.visibility] for p in component.landmark] if component else [[0]*4]*count)
    return np.array(rows)


def main():
    report = dict(scope="Identical frames/timestamps from two legacy fixtures; detector/model parity and wall time only.", cases=[])
    recognizer = Recognizer(ROOT / "assets")
    for label in [379, 204]:
        file = ROOT / f"assets/samples/{label:03d}.mp4"
        cap = cv2.VideoCapture(str(file))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            ratio = min(1, 640 / max(frame.shape[:2]))
            frames.append(cv2.resize(frame, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA) if ratio < 1 else frame)
        cap.release()
        arms = []
        for factory in [original["LandmarkDetector"], LandmarkDetector]:
            started = time.perf_counter()
            with factory(ROOT / "assets") as detector:
                keypoints = [detector.process(frame, i*1000/fps) for i, frame in enumerate(frames)]
            elapsed = (time.perf_counter()-started)*1000
            tensor = recognizer.model.preprocess(keypoints)
            logits = recognizer.model.session.run(["logits"], {"poses": tensor})[0]
            arms.append((np.stack([vector(p) for p in keypoints]), tensor, logits, elapsed))
        row = dict(file=str(file), sha256=hashlib.sha256(file.read_bytes()).hexdigest(), frames=len(frames),
                   coordinate_max_abs=float(np.max(np.abs(arms[0][0]-arms[1][0]))),
                   tensor_max_abs=float(np.max(np.abs(arms[0][1]-arms[1][1]))),
                   logit_max_abs=float(np.max(np.abs(arms[0][2]-arms[1][2]))),
                   original_ms=arms[0][3], bounded_ms=arms[1][3])
        report["cases"].append(row)
        print(json.dumps(row), flush=True)
    report["passed"] = all(c["coordinate_max_abs"] == c["tensor_max_abs"] == c["logit_max_abs"] == 0 for c in report["cases"])
    (OUT / "legacy-scheduling-parity.json").write_text(json.dumps(report, indent=2), "utf8")
    assert report["passed"]


if __name__ == "__main__":
    main()
