"""Real Clinic provider on a small prespecified fixture list, paced at source FPS."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.multimodal_provider import MultimodalProvider

DATA = Path(r"E:\\Paper\MultiModel Paper\Data_Labeling_20261104\delivery\VSL100_REVIEWED_20261106_r3")
SPLIT = Path(r"E:\\Paper\MultiModel Paper\VSL100_R3_20261106\training_inputs\r3_loso_01.json")
OUT = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/capture"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = json.loads(SPLIT.read_text("utf8"))
    ids = ["W066", "W068", "W069", "W072", "W082", "W093"]
    chosen = [next(r for r in rows if r["split"] == split and r["class_id"] == cid and
                   r["take_id"] == 1 and r["camera_id"] == "1")
              for split in ["validation", "test"] for cid in ids]
    plan = dict(scope="12 fixed prerecorded clips, 2 signers; natural Clinic boundaries and actual worker, not live webcam accuracy.",
                clips=chosen, checkpoint_selection="fixed original fold01 seed17; no tuning from this probe",
                commit_policy="clinic-fusion-quality-v1, prespecified .8 top score / .25 margin + observation quality")
    (OUT / "PLAN.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), "utf8")
    events = []
    provider = MultimodalProvider(ROOT / "assets", lambda e: events.append(dict(e, received_monotonic_ms=time.perf_counter() * 1000)))
    results = []
    try:
        for row in chosen:
            path = DATA / row["video_path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
            start = time.perf_counter()
            generation = provider.start(str(path), "video")
            deadline = start + 110
            while time.perf_counter() < deadline:
                status = next((e for e in reversed(events) if e.get("generation") == generation and
                               e.get("type") == "capture" and e.get("status") in {"ended", "error"}), None)
                if status:
                    break
                time.sleep(.05)
            else:
                raise TimeoutError(row["clip_id"])
            selected = [e for e in events if e.get("generation") == generation]
            rec = [e for e in selected if e["type"] in {"recognition", "recognition_unavailable"}]
            results.append(dict(clip_id=row["clip_id"], gloss=row["gloss"], expected_class=row["class_id"],
                                elapsed_seconds=time.perf_counter() - start, worker=provider.worker_info,
                                final_capture=status, recognition=rec))
            (OUT / "RESULTS.json").write_text(json.dumps(dict(plan=plan, results=results), ensure_ascii=False, indent=2), "utf8")
            print(row["clip_id"], [(r.get("predictions", [{}])[0].get("gloss"), r.get("policy", {}).get("committed"))
                                   for r in rec], status["status"], flush=True)
            if status["status"] == "error":
                print("Worker diagnostics:", list(provider.last_errors), flush=True)
                raise RuntimeError("capture_error")
            events.clear()
        committed = [r for result in results for r in result["recognition"] if r.get("policy", {}).get("committed")]
        summary = dict(clips=len(results), results=sum(len(r["recognition"]) for r in results),
                       committed=len(committed),
                       errors_among_committed=sum(p["predictions"][0]["class_id"] != r["expected_class"]
                           for r in results for p in r["recognition"] if p.get("policy", {}).get("committed")),
                       clips_without_result=sum(not r["recognition"] for r in results),
                       uncommitted_results=sum(not p.get("policy", {}).get("committed") for r in results for p in r["recognition"]),
                       scope=plan["scope"])
        (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf8")
        print(summary, flush=True)
    finally:
        provider.close()


if __name__ == "__main__":
    main()
