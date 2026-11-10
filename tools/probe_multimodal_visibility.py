"""Synthetic occlusion/shake stress, kept separate from natural signer accuracy."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.multimodal_provider import MultimodalProvider
OUT = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/visibility"


def make_cases():
    import cv2
    import numpy as np
    import mediapipe as mp
    cap = cv2.VideoCapture(str(ROOT / "assets/multimodal-samples/W068.mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS)
    writers = {name: cv2.VideoWriter(str(OUT / (name+".mp4")), cv2.VideoWriter_fourcc(*"mp4v"), fps, (1080,1080))
               for name in ["no-face", "covered-mouth", "lower-body-covered", "shake-static-rest"]}
    detector = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=.5)
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        i += 1
        neutral = frame.copy()
        points = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).detections or []
        variants = {name: frame.copy() for name in writers if name != "shake-static-rest"}
        variants["no-face"][190:500,440:720] = 127
        variants["lower-body-covered"][450:,:] = 127
        if points:
            p=points[0].location_data.relative_keypoints
            mouth=p[3]
            width=max(45, round(abs(p[0].x-p[1].x)*1080*1.5))
            x,y=round(mouth.x*1080),round(mouth.y*1080)
            cv2.rectangle(variants["covered-mouth"],(x-width,y-22),(x+width,y+50),(210,200,135),-1)
        for name,value in variants.items():
            writers[name].write(value)
            if i==60:
                cv2.imwrite(str(OUT/(name+".jpg")),value)
    # Only camera-like translations of a frozen rest frame, not real movements.
    for j in range(round(5*fps)):
        matrix=np.float32([[1,0,18*np.sin(j*.2)],[0,1,12*np.cos(j*.3)]])
        writers["shake-static-rest"].write(cv2.warpAffine(neutral,matrix,(1080,1080)))
    cap.release()
    detector.close()
    for writer in writers.values():writer.release()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if "--make" in sys.argv:
        make_cases()
        return
    events=[]
    provider=MultimodalProvider(ROOT/"assets",events.append)
    report={"scope":"Synthetic pixel occlusions and translated static rest; not real mask, drinking, scratching or glasses validation.","cases":[]}
    try:
        for name in ["no-face","covered-mouth","lower-body-covered","shake-static-rest"]:
            events.clear()
            provider.start(str(OUT/(name+".mp4")),"video")
            deadline=time.perf_counter()+110
            while time.perf_counter()<deadline:
                if any(e["type"]=="capture" and e.get("status") in {"ended","error"} for e in events):break
                time.sleep(.05)
            row=dict(case=name,recognition=[e for e in events if e["type"] in {"recognition","recognition_unavailable"}],final=events[-1])
            report["cases"].append(row)
            assert row["final"]["status"]=="ended",row
        report["committed_counts"]={r["case"]:sum(e.get("policy",{}).get("committed",False) for e in r["recognition"]) for r in report["cases"]}
    finally:
        provider.close()
        (OUT/"RESULTS.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
        print(report.get("committed_counts"),flush=True)


if __name__=="__main__":main()
