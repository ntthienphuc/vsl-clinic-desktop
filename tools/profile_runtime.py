"""Component timing on this machine; no substituted recognitions or UI clocks."""
from pathlib import Path
import json
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.landmarks import LandmarkDetector

cv2.setNumThreads(1)
report = {}
images = []
for threads in [1, 0]:
    capture = cv2.VideoCapture(str(ROOT / "assets/samples/011.mp4"), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, threads])
    measures = []
    while True:
        start = time.perf_counter()
        ok, bgr = capture.read()
        decoded = time.perf_counter()
        if not ok:
            break
        bgr = cv2.resize(bgr, (540, 540))
        resized = time.perf_counter()
        cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 78])
        encoded = time.perf_counter()
        measures.append([1000 * (decoded - start), 1000 * (resized - decoded), 1000 * (encoded - resized)])
        if threads == 1:
            images.append(bgr)
    capture.release()
    report[f"reader_threads_{threads}_median_ms"] = np.median(measures, axis=0).tolist()
    print(json.dumps(report), flush=True)
with LandmarkDetector(ROOT / "assets") as detector:
    measures = []
    for index, bgr in enumerate(images[:40]):
        start = time.perf_counter()
        result = detector.process(bgr, index * 33.37)
        measures.append(1000 * (time.perf_counter() - start))
    report["landmark_ms"] = {"median": float(np.median(measures[3:])), "p95": float(np.percentile(measures[3:], 95))}
    print(json.dumps(report), flush=True)
data = np.random.default_rng(7).normal(size=(1, 3, 150, 27, 1)).astype(np.float32)
for threads in [1, 2, 4]:
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    session = ort.InferenceSession(str(ROOT / "assets/models/slgcn_bone_all_cams.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    measures = []
    for _ in range(7):
        start = time.perf_counter()
        session.run(None, {"poses": data})
        measures.append(1000 * (time.perf_counter() - start))
    report[f"onnx_threads_{threads}_ms"] = {"median": float(np.median(measures[1:])), "p95": float(np.percentile(measures[1:], 95))}
    del session
    print(json.dumps(report), flush=True)
(ROOT / "research/component-profile.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
