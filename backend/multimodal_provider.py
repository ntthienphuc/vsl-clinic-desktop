"""Lightweight Clinic adapter. Torch/vendor code never enters the ASR process."""
from collections import deque
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


class MultimodalProvider:
    def __init__(self, assets, publish, *, command=None):
        self.assets, self.publish = Path(assets), publish
        root = Path(__file__).resolve().parents[1]
        if command is None:
            resources = self.assets.parent
            runtime = Path(os.environ.get("CLINIC_MM_RUNTIME", str(root / "build/multimodal-runtime")))
            worker = root / "multimodal/worker.py"
            if getattr(sys, "frozen", False):
                runtime = resources / "multimodal-runtime"
                worker = resources / "multimodal/worker.py"
            command = [str(runtime / "python.exe"), "-B", "-u", "-X", "utf8", str(worker),
                       "--assets", str(self.assets / "multimodal100")]
        self.command = command
        manifest = json.loads((self.assets / "multimodal100/models/MODEL_MANIFEST.json").read_text("utf8"))
        self.manifest = manifest
        self.generation = 0
        self.process = None
        self.active_generation = None
        self.preview = None
        self.preview_version = 0
        self.preview_lock = threading.Lock()
        self.lock = threading.RLock()
        self.writer_lock = threading.Lock()
        self.ready = threading.Event()
        self.stopped = threading.Event()
        self.stop_generation = None
        self.worker_info = dict(status="not_started")
        self.last_errors = deque(maxlen=6)
        self.closing = False
        self.reader = None
        self.stderr_reader = None

    def info(self):
        return dict(name="Tay và môi · 100 từ", labels=100, family="multimodal100",
                    sha256=self.manifest["heads"]["fusion"]["sha256"],
                    contract=self.manifest["contract"], capture_profile=(
                        "clinic-mm100-ram-r3-v1" if self.manifest.get("profile") == "slgcn-avhubert"
                        else "clinic-mm100-ram-v2"),
                    active_head="fusion", worker=dict(self.worker_info))

    def warmup(self):
        """Load weights in the background; this never opens a camera."""
        with self.lock:
            try:
                self._spawn()
            except OSError as exc:
                self.worker_info = dict(status="error", error_code=type(exc).__name__)

    def _send(self, event):
        with self.writer_lock:
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError("multimodal_worker_not_running")
            self.process.stdin.write(json.dumps(event) + "\n")
            self.process.stdin.flush()

    def _spawn(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.ready.clear()
        self.closing = False
        self.worker_info = dict(status="loading")
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                   OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", TF_CPP_MIN_LOG_LEVEL="2")
        # A frozen parent must not make its child load ClinicEngine's DLLs.
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf8", bufsize=1, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        process = self.process
        self.reader = threading.Thread(target=self._read, args=(process,), name="clinic-mm100-events", daemon=True)
        self.stderr_reader = threading.Thread(target=self._stderr, args=(process,), name="clinic-mm100-stderr", daemon=True)
        self.reader.start()
        self.stderr_reader.start()

    def _stderr(self, process):
        # Do not persist third-party diagnostics or patient content.
        for line in process.stderr:
            self.last_errors.append(line.strip()[:500])

    def _read(self, process):
        try:
            for line in process.stdout:
                if process is not self.process:
                    return
                event = json.loads(line)
                kind = event["type"]
                if kind == "worker_ready":
                    self.worker_info = dict(event, status="ready")
                    self.ready.set()
                    continue
                if kind == "worker_error":
                    self.worker_info = dict(status="error", error_code=event.get("error_code"))
                    self.ready.set()
                    continue
                if kind == "worker_stopped":
                    if event.get("generation") == self.stop_generation:
                        self.stopped.set()
                    continue
                generation = event.get("generation")
                if process is not self.process or generation != self.active_generation:
                    continue
                if kind == "preview":
                    with self.preview_lock:
                        self.preview = base64.b64decode(event["jpeg"])
                        self.preview_version += 1
                else:
                    if event.get("timing"):
                        event["timing"]["worker_to_backend_ms"] = max(
                            0, time.perf_counter() * 1000 - event["timing"]["emitted_monotonic_ms"])
                        event["timing"]["backend_received_epoch_ms"] = time.time() * 1000
                    self.publish(event)
        except Exception as exc:
            self.last_errors.append(type(exc).__name__ + ": " + str(exc))
        finally:
            if process is self.process:
                self.ready.set()
            if process is self.process and not self.closing:
                self.worker_info = dict(status="error", error_code="worker_disconnected")
                generation = self.active_generation
                if generation is not None:
                    self.publish(dict(type="capture", status="error", generation=generation,
                        message="Bộ nhận dạng tay và môi đã dừng. Bấm Bắt đầu để thử lại; luồng bác sĩ vẫn dùng được."))

    def start(self, source, source_kind):
        with self.lock:
            self.stop()
            self.generation += 1
            generation = self.generation
            self.active_generation = generation
            self.publish(dict(type="capture", status="starting", generation=generation,
                              source_kind=source_kind, message="Đang chuẩn bị nhận dạng tay và môi…"))
            try:
                self._spawn()
            except Exception:
                self.publish(dict(type="capture", status="error", generation=generation,
                    message="Thiếu bộ chạy nhận dạng tay và môi. Kiểm tra đầy đủ thư mục ứng dụng."))
                return generation
            # Keep the API and doctor conversation responsive during cold model load.
            def begin():
                if not self.ready.wait(90):
                    status = "timeout"
                else:
                    status = self.worker_info.get("status")
                with self.lock:
                    if self.active_generation != generation:
                        return
                    if status != "ready":
                        self.publish(dict(type="capture", status="error", generation=generation,
                            message="Chưa khởi động được nhận dạng tay và môi. Bạn có thể kết thúc phiên rồi thử lại."))
                        return
                    try:
                        self._send(dict(action="start", source=source, source_kind=source_kind, generation=generation))
                    except (OSError, RuntimeError):
                        self.publish(dict(type="capture", status="error", generation=generation,
                            message="Bộ nhận dạng đã ngắt. Bấm Bắt đầu để thử lại."))
            threading.Thread(target=begin, name="clinic-mm100-start", daemon=True).start()
            return generation

    def stop(self):
        with self.lock:
            previous = self.active_generation
            self.active_generation = None  # Fence callbacks before waiting on the GPU.
            with self.preview_lock:
                self.preview = None
                self.preview_version += 1
            if previous is not None and self.process is not None and self.process.poll() is None:
                try:
                    self.stop_generation = previous
                    self.stopped.clear()
                    self._send(dict(action="stop", generation=previous))
                except (OSError, RuntimeError):
                    pass

    def stop_and_wait(self):
        """Release camera before another provider can open it; retain warm weights."""
        self.stop()
        if self.stop_generation is not None and not self.stopped.wait(12):
            # A wedged child must release its device before changing providers.
            self.close()
        self.stop_generation = None

    def close(self):
        with self.lock:
            self.closing = True
            self.stop()
            process = self.process
            if process is None:
                return
            try:
                self._send(dict(action="shutdown"))
                process.stdin.close()
                process.wait(timeout=12)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
            for thread in (self.reader, self.stderr_reader):
                if thread and thread is not threading.current_thread():
                    thread.join(timeout=2)
            self.process = None

    def preview_frame(self):
        with self.preview_lock:
            return self.preview_version, self.preview
