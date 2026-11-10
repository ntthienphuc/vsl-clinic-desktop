"""Small actual-worker stress probe; prerecorded fixture, no webcam user."""
from pathlib import Path
import json
import sys
import time
import os
import ctypes
from ctypes import wintypes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.multimodal_provider import MultimodalProvider
VERSION = json.loads((ROOT/"package.json").read_text("utf8"))["version"]
FIXTURES = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/stress"
OUT = FIXTURES.with_name("stress-" + VERSION.replace(".", ""))
RES = ROOT.parent / "App" / VERSION / "win-unpacked/resources"


def rss(pid):
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize",
            "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage"]]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x10, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        value = Counters()
        value.cb = ctypes.sizeof(value)
        query = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        assert query(handle, ctypes.byref(value), value.cb)
        return value.WorkingSetSize
    finally:
        kernel.CloseHandle(handle)


def main():
    OUT.mkdir(exist_ok=False)
    events, samples = [], []
    report = dict(scope="Actual private worker, 312-second composed video at real time; no live signer. Static idle is not general non-sign validation.", checks={})
    latest = {}
    def receive(event):
        if event["type"] == "capture":
            latest.clear()
            latest.update(event)
        else:
            events.append(event)
    assets = RES / "assets" if "--packaged" in sys.argv else ROOT / "assets"
    command = None
    if "--packaged" in sys.argv:
        os.environ["PATH"] = os.environ["SystemRoot"] + r"\System32"
        command = [str(RES/"multimodal-runtime/python.exe"), "-B", "-u", "-X", "utf8", str(RES/"multimodal/worker.py"), "--assets", str(assets/"multimodal100")]
    report["packaged_worker"] = command is not None
    provider = MultimodalProvider(assets, receive, command=command)
    def wait_for(predicate, seconds=60):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            if predicate():
                return
            time.sleep(.05)
        raise TimeoutError(str(latest))
    try:
        provider.warmup()
        wait_for(lambda: provider.worker_info.get("status") in {"ready", "error"}, 100)
        assert provider.worker_info["status"] == "ready", provider.worker_info
        report["worker"] = dict(provider.worker_info)
        generation = provider.start(str(FIXTURES / "long-session.mp4"), "video")
        process_id = provider.process.pid
        started = time.perf_counter()
        while time.perf_counter() - started < 340:
            assert latest.get("status") != "error", latest
            samples.append(dict(elapsed_seconds=time.perf_counter()-started,
                rss_bytes=rss(process_id), capture=dict(latest)))
            (OUT / "PROGRESS.json").write_text(json.dumps(samples[-1], ensure_ascii=False, indent=2), "utf8")
            if latest.get("status") == "ended":
                break
            time.sleep(5)
        assert latest.get("status") == "ended", latest
        recognition = [e for e in events if e["type"] in {"recognition", "recognition_unavailable"}]
        assert any(e.get("boundary", {}).get("decision_capture_ms", 0) > 300000 for e in recognition)
        assert len({e["segment_id"] for e in recognition}) == len(recognition)
        assert max(s["capture"].get("buffer_frames", 0) for s in samples) <= 271
        assert max(s["capture"].get("queued_segments", 0) for s in samples) <= 2
        assert max(s["capture"].get("inflight_segments", 0) for s in samples) <= 3
        report.update(long_recognition=recognition, samples=samples, long_final=dict(latest))
        report["checks"]["crosses_five_minutes_bounded_without_reset"] = True
        report["checks"]["repeated_words_keep_unique_segment_identity"] = True
        # Real source replacement while processing; the old generation is fenced.
        g = provider.start(str(assets / "multimodal-samples/W069.mp4"), "video")
        wait_for(lambda: latest.get("status") == "signing")
        provider.stop()
        at = len(events)
        new = provider.start(str(assets / "multimodal-samples/W068.mp4"), "video")
        wait_for(lambda: latest.get("status") in {"ended", "error"})
        assert latest["status"] == "ended"
        assert all(e.get("generation") == new for e in events[at:])
        report["checks"]["source_change_fences_prior_generation"] = True
        # A crashed child cannot kill the Clinic caller; next Start recreates it.
        old = provider.process
        old.kill()
        old.wait(timeout=5)
        wait_for(lambda: provider.worker_info.get("status") == "error")
        provider.start(str(assets / "multimodal-samples/W068.mp4"), "video")
        wait_for(lambda: latest.get("status") in {"ended", "error"}, 110)
        assert latest["status"] == "ended", list(provider.last_errors)
        assert provider.process.pid != old.pid
        report["checks"]["worker_crash_then_restart"] = True
        provider.start(str(assets / "multimodal-samples/W068.mp4"), "video")
        wait_for(lambda: latest.get("status") == "signing")
        dying = provider.process
        provider.stop()
        at = len(events)
        provider.close()
        assert dying.poll() is not None and len(events) == at
        report["checks"]["end_joins_child_without_late_words"] = True
        report["passed"] = True
    except Exception as exc:
        report.update(error=repr(exc), worker_errors=list(provider.last_errors), passed=False,
                      samples=samples, last_capture=dict(latest), events=events)
        raise
    finally:
        provider.close()
        (OUT / "LIFECYCLE.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
        print(json.dumps(dict(passed=report.get("passed"), checks=report["checks"])), flush=True)


if __name__ == "__main__":
    main()
