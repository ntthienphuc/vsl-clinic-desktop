"""Build compact, reproducible evidence from actual runs; no invented pass gates."""
from pathlib import Path
import hashlib
import json
import shutil
import statistics

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/"Organization/MultimodalIntegration_2026-11-09"
DOC=ROOT/"docs/evidence"


def read(name):return json.loads((OUT/name).read_text("utf8"))
def percentile(values,q):
    values=sorted(values)
    if not values:return None
    index=(len(values)-1)*q
    lo=int(index);hi=min(lo+1,len(values)-1)
    return round(values[lo]+(values[hi]-values[lo])*(index-lo),2)
def stats(values):return dict(n=len(values),p50_ms=percentile(values,.5),p95_ms=percentile(values,.95),min_ms=round(min(values),2) if values else None,max_ms=round(max(values),2) if values else None)


def main():
    ui=read("packaged-ui-12/REPORT.json")
    assert ui["passed"] and ui.get("desktopExit")==0 and not ui.get("shutdownForced")
    long=read("stress/LIFECYCLE.json")
    assert long["passed"] and long["packaged_worker"]
    assert read("parity/PARITY.json")["passed"]
    assert read("cpu/REPORT.json")["passed"]
    assert read("FINAL_CHECK_PROGRESS.json")["status"]=="complete"
    trials=ui["trials"]
    assert len(trials)==12
    timing=[t["word"]["metrics"]["timing"] for t in trials]
    render=[];active_paint=[];active_audio=[];audio_queue=[]
    for trial in trials:
        word=trial["word"];clock=word["metrics"]["timing"]
        anchor=clock["backend_received_epoch_ms"]
        for paint in trial["paint"][:1]:
            render.append(paint["painted_at_ms"]-anchor)
            active_paint.append(clock["last_active_capture_to_result_ms"]+clock["worker_to_backend_ms"]+paint["painted_at_ms"]-anchor)
        if not word["uncertain"]:
            audio=next(e for e in trial["voice"] if e["type"]=="playing" and e["message_id"]==word["id"])
            audio_queue.append(audio["latency_ms"])
            active_audio.append(clock["last_active_capture_to_result_ms"]+clock["worker_to_backend_ms"]+audio["recorded_at_ms"]-anchor)
    samples=long["samples"]
    visibility=read("visibility/RESULTS.json")
    summary=dict(scope="Local fixture verification of 0.5.0. Model scores uncalibrated; no webcam signer, natural mask/non-sign, clean-machine or clinical validation.",
        acceptance=dict(engineering_fixture_checks="passed",full_product_robustness="not_accepted",
            open_items=["7 of 12 EXE clips need review initially; 5 of the same 12 in the repeat after Lip was closed", "covered-mouth synthetic fixture still commits; face detection does not prove usable mouth cues", "no natural incidental-gesture or real mask fixtures; three OOV cases do not establish general OOV robustness", "live hardware and acoustic behavior not tested by user choice"]),
        contract="vsl100-r3-spoter-vlr-f01-s17-v2.0",tests=dict(python=397,javascript=23),
        packaged_checks=ui["checks"],ui_quality=dict(unique_fixed_clips=len(trials),committed=ui["counts"]["autoWords"],
            wrong_committed=sum(not t["word"]["uncertain"] and t["word"]["predictions"][0]["class_id"]!=t["expected"] for t in trials),
            review=sum(t["word"]["uncertain"] for t in trials),
            top1_matching_fixed_label=sum(t["word"]["predictions"][0]["class_id"]==t["expected"] for t in trials),
            deliberate_repeat=dict(words=len(ui["repeat"]["words"]),independent_trials=False)),
        latency=dict(inference=stats([t["inference_wall_ms"] for t in timing]),
            decision_to_result=stats([t["decision_to_result_ms"] for t in timing]),
            backend_to_paint=stats(render),last_active_frame_to_paint=stats(active_paint),
            last_active_frame_to_audio=stats(active_audio),frontend_queue_to_audio=stats(audio_queue),
            caveat="Same-host timestamps; React plus two animation frames and Audio.onplaying, not photon/acoustic measurements. Twelve clips, only committed words contribute audio; descriptive p95 with tiny n."),
        fps_range=[min(t["word"]["metrics"]["quality"]["input_fps"] for t in trials),max(t["word"]["metrics"]["quality"]["input_fps"] for t in trials)],
        long_session=dict(checks=long["checks"],duration_seconds=samples[-1]["elapsed_seconds"],
            rss_min_mb=min(s["rss_bytes"] for s in samples)/1e6,rss_max_mb=max(s["rss_bytes"] for s in samples)/1e6,
            peak_buffer_frames=max(s["capture"].get("buffer_frames",0) for s in samples),
            peak_queued=max(s["capture"].get("queued_segments",0) for s in samples),
            results=len(long["long_recognition"]),
            static_idle_false_words=sum(24000<e.get("boundary",{}).get("decision_capture_ms",0)<285000 for e in long["long_recognition"]),
            static_idle_minutes=261/60,negative_scope="Repeated static rest only; not general non-sign detection."),
        capture12=read("capture/SUMMARY.json"),synthetic_visibility=visibility["committed_counts"],
        synthetic_visibility_interpretation="Covered-mouth yields one committed Sốt (matching original positive clip), so this is a failed occlusion-rejection expectation, not proof that masks are handled. Other three synthetic cases have no committed words. No real non-sign false-emission rate is available.",
        graphics=ui["graphics"],worker=ui["worker"],packaged_shutdown_exit=ui["desktopExit"],
        repeat_after_lip_closed=read("AFTER_LIP_CLOSED_COMPARISON.json"),
        three_oov_clips=read("oov3/REPORT.json")["summary"])
    (OUT/"SUMMARY_FINAL.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),"utf8")
    evidence=["SUMMARY_FINAL.json","parity/PARITY.json","capture/PLAN.json","capture/RESULTS.json","capture/SUMMARY.json",
        "stress/PLAN.json","stress/REPEAT_PLAN.json","stress/LIFECYCLE.json","visibility/RESULTS.json","cpu/REPORT.json",
        "source-ui-final/REPORT-before-graph-overlap.json","packaged-ui/REPORT.json","packaged-ui-12/REPORT.json","baseline/RECHECK.json",
        "python-tests-final.log","javascript-tests-final.log","FINAL_CHECK_PROGRESS.json",
        "PRESERVATION_FINAL.json","baseline/PORTABLE_RECHECK.json",
        "AFTER_LIP_CLOSED_COMPARISON.json","packaged-ui-12-after-lip-closed/REPORT.json",
        "oov3/PLAN.json","oov3/REPORT.json"]
    for relative in evidence:
        source=OUT/relative
        shutil.copy2(source,DOC/("multimodal-050-"+relative.replace("/","-")))
    for folder in ["source-ui","source-ui-final","packaged-ui"]:
        for source in (OUT/folder).glob("REPORT-*.json"):
            value=json.loads(source.read_text("utf8"))
            if value.get("passed") is False:
                shutil.copy2(source,DOC/("multimodal-050-failed-"+folder+"-"+source.name))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
