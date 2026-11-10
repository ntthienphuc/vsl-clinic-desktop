"""Concise measured 0.5.2 evidence, including failed attempts and inheritance."""
import json
from pathlib import Path
from summarize_multimodal_r3 import ui_summary

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09"
OUT = ROOT.parent / "Organization/ModesPilot_2026-11-10"


def read(name):
    return json.loads((QA / name / "REPORT.json").read_text("utf8"))


def compact(name, full=False):
    report = read(name)
    result = ui_summary(report) if full else dict(passed=report["passed"], checks=report["checks"])
    repeat = report.get("repeat", {})
    result.update(evidence=name, functional_checks_passed=report["passed"],
        passed=report["passed"] and report.get("desktopExit") == 0 and not report.get("shutdownForced"),
        desktop_exit=report.get("desktopExit"),
        shutdown_forced=report.get("shutdownForced", False),
        engine_graceful_exit=report.get("engineGracefulExit"), worker_exited=report.get("workerExited"),
        shutdown_ms=report.get("shutdownMs"),
        mode_switch=report.get("modeSwitch"),
        legacy=dict(text=report.get("legacyWord", {}).get("word", {}).get("text"),
                    reviewed=report.get("legacyWord", {}).get("reviewed")),
        repeat=dict(review_confirmations=repeat.get("qaConfirmations"),
                    original=[dict(text=w["text"], uncertain=w["uncertain"]) for w in repeat.get("originalDecisions", [])]),
        speech_negative=report.get("speechNegative"), error=report.get("error"))
    return result


def main():
    source = compact("source-ui-final-minimal-052-r2", True)
    source_final = compact("source-ui-final-minimal-final-052")
    packaged = compact("packaged-ui-12-minimal-reviewed-052", True)
    assert source_final["passed"] and packaged["passed"]
    assert source_final["checks"]["cleanDesktopEngineAndWorkerExit"]
    assert packaged["checks"]["cleanDesktopEngineAndWorkerExit"]
    report = dict(version="0.5.2", scope="Fixed prerecorded VSL100 and legacy clips, synthetic sound and bundled speech fixture. No live person/device or clinical accuracy claim.",
        ui=dict(default="Ký hiệu + khẩu hình", alternative="Chỉ ký hiệu", vocabularies=[100, 400], quick_phrases=24),
        tests=dict(python=404, javascript=23), source_12=source, source_final=source_final, packaged=packaged,
        isolation_before_switch=compact("packaged-ui-fusion-isolation-052"),
        isolation_after_switch=compact("packaged-ui-mode-isolation-052"),
        earlier_attempts=[dict(evidence=name, passed=read(name)["passed"],
            checks=read(name)["checks"], error=read(name).get("error"),
            processed_clips=len(read(name).get("trials", [])),
            automatic=sum(not t["word"]["uncertain"] for t in read(name).get("trials", [])))
            for name in ["packaged-ui-12-modes-052", "packaged-ui-12-modes-052-r2", "packaged-ui-12-modes-052-bounded", "source-ui-final-minimal-052", "packaged-ui-12-minimal-final-052"]],
        inherited_051=dict(scope="Unchanged fusion core only; retained historical evidence, not fresh 0.5.2 measurements.",
            artifacts=["fusion_explore/clinic-r3-parity/REPORT.json", "stress-051/LIFECYCLE.json", "cpu-051/REPORT.json", "visibility-051/REPORT.json", "oov3-051/REPORT.json"]),
        limits=["Tiny fixed examples; temporal sampling and closed-set predictions vary under load.",
                "The earlier bounded EXE run committed only 1/12; successful later runs do not erase that failure.",
                "No speaker identity model: clear bystander speech may be transcribed.",
                "AV-HuBERT restricts this artifact to non-commercial research; no production hospital release."])
    (OUT / "SUMMARY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
    print(json.dumps(dict(source=source["automatic"], packaged=packaged["automatic"],
        packaged_wrong=packaged["wrong_automatic"], packaged_review=packaged["review"],
        packaged_latency=packaged["latency"], source_final=source_final["passed"], packaged_passed=packaged["passed"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
