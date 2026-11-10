"""Summarize actual 0.5.1 evidence, keeping failed attempts and limits visible."""
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.summarize_multimodal_verification import stats
QA=ROOT.parent/"Organization/MultimodalIntegration_2026-11-09"


def read(path):
    return json.loads((QA/path).read_text("utf8"))


def ui_summary(ui):
    trials=ui["trials"]
    paint,audio=[],[]
    for trial in trials:
        w=trial["word"]
        t=w["metrics"]["timing"]
        anchor=t["backend_received_epoch_ms"]
        if trial["paint"]:
            paint.append(t["last_active_capture_to_result_ms"]+t["worker_to_backend_ms"]+
                         trial["paint"][0]["painted_at_ms"]-anchor)
        if not w["uncertain"]:
            a=next(e for e in trial["voice"] if e["type"]=="playing" and e["message_id"]==w["id"])
            audio.append(t["last_active_capture_to_result_ms"]+t["worker_to_backend_ms"]+a["recorded_at_ms"]-anchor)
    return dict(passed=ui["passed"],desktop_exit=ui.get("desktopExit"),checks=ui["checks"],
        clips=len(trials),automatic=sum(not t["word"]["uncertain"] for t in trials),
        wrong_automatic=sum(not t["word"]["uncertain"] and t["word"]["predictions"][0]["class_id"]!=t["expected"] for t in trials),
        review=sum(t["word"]["uncertain"] for t in trials),
        top1_agreement=sum(t["word"]["predictions"][0]["class_id"]==t["expected"] for t in trials),
        omitted_clips=12-len(trials),
        input_fps=[min(t["word"]["metrics"]["quality"]["input_fps"] for t in trials),
                   max(t["word"]["metrics"]["quality"]["input_fps"] for t in trials)],
        latency=dict(last_active_frame_to_paint=stats(paint),last_active_frame_to_audio=stats(audio),
                     inference=stats([t["word"]["metrics"]["timing"]["inference_wall_ms"] for t in trials]),
                     caveat="Software timestamps, not photon/acoustic latency; tiny fixed sample, descriptive p95."),
        repeat=ui.get("repeat",{}))


def main():
    package=read("packaged-ui-12-r3-051-policy/REPORT.json")
    source=read("source-ui-final-r3-context/REPORT.json")
    long=read("stress-051/LIFECYCLE.json")
    cpu=read("cpu-051/REPORT.json")
    visibility=read("visibility-051/REPORT.json")
    parity=read("fusion_explore/clinic-r3-parity/REPORT.json")
    original_repeat=read("packaged-ui-r3-051-original-repeat/REPORT.json")
    oov=read("oov3-051/REPORT.json")
    portable=read("release-051/PORTABLE.json")
    preservation=read("release-051/PRESERVATION.json")
    for run in [package,source]:
        assert run["passed"] and run.get("desktopExit")==0 and not run.get("shutdownForced")
    assert long["passed"] and cpu["passed"] and parity["passed"]
    assert visibility["execution_passed"] and visibility["no_face_suppresses_speech"]
    assert original_repeat["passed"] and original_repeat.get("desktopExit")==0
    assert oov["summary"]["functional_run_completed"] and oov["worker_joined"]
    assert portable["passed"] and preservation["passed"]
    samples=long["samples"]
    result=dict(scope="0.5.1 local integration accepted for the requested VSL100 fixture scope; no live webcam, real-mask/incidental-action, clean-machine or clinical accuracy claim.",
        contract=json.loads((ROOT/"assets/multimodal100/models/MODEL_MANIFEST.json").read_text("utf8"))["contract"],
        model="SL-GCN + AV-HuBERT cross-attention, fixed R3 fold01 seed17",
        research_macro_f1_percent=97.39068848300708,research_accuracy_percent=97.50617283950618,
        research_scope="Existing 5400 VSL100 videos, 6 folds x 3 seeds; not measured Clinic accuracy.",
        tests=dict(python_project=396,javascript=23),
        source=ui_summary(source),packaged=ui_summary(package),
        prior_packaged_attempt=ui_summary(read("packaged-ui-12-r3-051/REPORT.json")),
        original_pixel_repeat=dict(checks=original_repeat["checks"],
            confirmations=original_repeat["repeat"]["qaConfirmations"],
            raw_decisions=original_repeat["repeat"]["originalDecisions"],
            pixel_receipt=read("fusion_explore/REPEAT_ORIGINAL_PIXELS.json")),
        parity=parity,
        long_session=dict(checks=long["checks"],duration_seconds=samples[-1]["elapsed_seconds"],
            results=len(long["long_recognition"]),
            automatic=sum(bool(e.get("policy",{}).get("committed")) for e in long["long_recognition"]),
            rss_min_mb=min(s["rss_bytes"] for s in samples)/1e6,
            rss_max_mb=max(s["rss_bytes"] for s in samples)/1e6,
            peak_buffer_frames=max(s["capture"].get("buffer_frames",0) for s in samples),
            peak_queue=max(s["capture"].get("queued_segments",0) for s in samples),
            static_idle_false_words=sum(24000<e.get("boundary",{}).get("decision_capture_ms",0)<285000 for e in long["long_recognition"]),
            static_idle_minutes=261/60,negative_scope="Repeated static neutral frame only"),
        cpu=dict(passed=cpu["passed"],worker=cpu["worker"],
                 results=[e for e in cpu["events"] if e["type"] in {"recognition","recognition_unavailable"}]),
        synthetic_visibility=visibility,
        outside_vocabulary=oov,
        package_inventory=portable,
        preservation=dict(passed=preservation["passed"],files=len(preservation["files"])),
        limits=["Fixed clips are an engineering check, not independent new accuracy after the context adjustment.",
                "Closed-set confidence does not guarantee OOV or non-sign rejection.",
                "Real mask and incidental action behavior is unvalidated.",
                "Microphone tests use synthetic PCM; no physical acoustic echo test.",
                "AV-HuBERT license restricts this artifact to non-commercial research."])
    (QA/"SUMMARY_051.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),"utf8")
    evidence=["SUMMARY_051.json","source-ui-final-r3-source/REPORT.json","source-ui-final-r3-context/REPORT.json",
        "packaged-ui-12-r3-051/REPORT.json","packaged-ui-12-r3-051-policy/REPORT.json",
        "packaged-ui-r3-051-original-repeat/REPORT.json","fusion_explore/REPEAT_ORIGINAL_PIXELS.json",
        "stress-051/LIFECYCLE.json","cpu-051/REPORT.json","visibility-051/REPORT.json",
        "oov3-051/PLAN.json","oov3-051/REPORT.json",
        "release-051/PORTABLE.json","release-051/PRESERVATION.json",
        "release-051/BASELINE_041.json","release-051/PREVIOUS_050.json",
        "fusion_explore/PLAN.json","fusion_explore/EXISTING_METHOD_RANKING.json",
        "fusion_explore/TEMPORAL_DIAGNOSIS.json","fusion_explore/R3_PRESERVATION.json",
        "fusion_explore/clinic-r3-parity/REPORT.json","fusion_explore/avhubert_cuda/REPORT.json",
        "fusion_explore/slgcn_cuda/REPORT.json","fusion_explore/slgcn_cpu/REPORT.json",
        "fusion_explore/current_cuda/REPORT.json","fusion_explore/python-tests-051.log",
        "fusion_explore/python-tests-051-project.log","fusion_explore/javascript-tests-051.log"]
    for name in evidence:
        shutil.copy2(QA/name,ROOT/"docs/evidence"/("multimodal-051-"+name.replace("/","-")))
    print(json.dumps({k:result[k] for k in ["model","tests","long_session"]},ensure_ascii=True,indent=2))
    print(json.dumps({k:{a:b for a,b in result[k].items() if a!="repeat"} for k in ["source","packaged"]},ensure_ascii=True,indent=2))


if __name__=="__main__":
    main()
