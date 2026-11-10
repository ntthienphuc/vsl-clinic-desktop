"""Deterministic local QA composition. No new person/camera recording.

Uses the already staged Huy fixtures; repeated frozen rest is NOT a natural
non-sign recording. Occlusion/camera-shake variants are synthetic stress cases.
"""
from pathlib import Path
import hashlib
import json
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/stress"


def load(cid):
    path = ROOT / "assets/multimodal-samples" / f"{cid}.mp4"
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    chosen = np.arange(0, len(frames) / fps, 1 / 25) * fps
    return [frames[min(len(frames)-1, round(i))] for i in chosen]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    clips = {cid: load(cid) for cid in ["W068", "W069", "W072", "W093", "W082"]}
    neutral = clips["W068"][-1]
    h, w = neutral.shape[:2]
    # Prespecified placements, including one word spanning the 300-second mark.
    slots = [(1, "W068"), (7, "W068"), (14, "W069"), (21, "W072"),
             (285, "W093"), (291, "W082"), (298, "W068"), (305, "W068")]
    schedule = {round(sec*25): (cid, clips[cid]) for sec, cid in slots}
    path = OUT / "long-session.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (w, h))
    assert writer.isOpened()
    current, at = None, 0
    for i in range(312*25):
        if i in schedule:
            _, current = schedule[i]
            at = 0
        frame = current[at] if current is not None and at < len(current) else neutral
        writer.write(frame)
        at += 1
    writer.release()
    report = dict(scope="Composed prerecorded fixture; not natural continuous signing or incidental-motion validation.",
                  fps=25, duration_seconds=312, slots=slots,
                  idle="Repeated last neutral frame of W068; static-rest negative only",
                  file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT / "PLAN.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
    # Frame for visual QA and designing explicitly synthetic occlusions.
    cv2.imwrite(str(OUT / "fixture-frame.jpg"), clips["W068"][25])
    print(json.dumps(report), flush=True)


def short_repeat():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = load("W068")
    path = OUT / "repeat-two-fever.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (1080,1080))
    assert writer.isOpened()
    for _ in range(2):
        for frame in frames:
            writer.write(frame)
    writer.release()
    (OUT / "REPEAT_PLAN.json").write_text(json.dumps(dict(
        scope="Two copies of the fixed W068 clip, nearest 25fps composition; not two independent signer observations.",
        expected=["W068","W068"],duration_seconds=len(frames)*2/25,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2),"utf8")


if __name__ == "__main__":
    short_repeat() if "--short" in sys.argv else main()
