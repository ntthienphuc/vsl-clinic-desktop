"""One camera owner with bounded capture, preprocessing and inference queues."""
from dataclasses import dataclass, field
import base64
from pathlib import Path
import queue
import threading
import time
import uuid

import cv2

from .preprocessing import MemoryProcessor
from .policy import recognition_event
from .boundaries import make_gate, extend_context


@dataclass
class Run:
    generation: int
    source: str | int
    source_kind: str
    stream_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cancel: threading.Event = field(default_factory=threading.Event)
    reader_done: threading.Event = field(default_factory=threading.Event)
    detector_done: threading.Event = field(default_factory=threading.Event)
    detector_ready: threading.Event = field(default_factory=threading.Event)
    frames: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=1))
    segments: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=2))
    lock: threading.Lock = field(default_factory=threading.Lock)
    threads: list = field(default_factory=list)
    captured: int = 0
    processed: int = 0
    dropped: int = 0
    capped: int = 0
    inflight: int = 0
    segment_number: int = 0
    detector_warmup_ms: float = 0.
    started: float = field(default_factory=time.perf_counter)
    state: str = "starting"
    last_activity: dict = field(default_factory=dict)


class MultimodalCapture:
    def __init__(self, engine, root, mapping, emit):
        self.engine, self.root, self.mapping, self.send = engine, Path(root), mapping, emit
        self.current = None
        self.model = dict(contract=engine.manifest["contract"], manifest_sha256=engine.manifest_hash,
                          fusion_sha256=engine.manifest["heads"]["fusion"]["sha256"])

    def emit(self, run, event):
        if self.current is run and not run.cancel.is_set():
            self.send(dict(event, generation=run.generation, stream_id=run.stream_id))

    def start(self, source, source_kind, generation):
        self.stop()
        run = Run(generation, source, source_kind)
        self.current = run
        self.emit(run, dict(type="capture", status="starting", source_kind=source_kind,
                            message="Đang chuẩn bị nhận dạng tay và môi…"))
        for name, target in [("infer", self._infer), ("detect", self._detect), ("read", self._read)]:
            thread = threading.Thread(target=target, args=(run,), name=f"mm100-{name}", daemon=True)
            run.threads.append(thread)
            thread.start()

    def stop(self):
        run = self.current
        if run is None:
            return
        run.cancel.set()
        # Do not share model ownership with a new run until CUDA has drained.
        for thread in run.threads:
            thread.join(timeout=10)
        if any(t.is_alive() for t in run.threads):
            raise RuntimeError("worker_did_not_drain")
        self.current = None
        while not run.frames.empty():
            run.frames.get_nowait()
        while not run.segments.empty():
            run.segments.get_nowait()

    def _error(self, run, reason):
        self.emit(run, dict(type="capture", status="error", error_code=reason,
                           message="Nguồn hình hoặc bộ nhận dạng đã dừng. Bấm Bắt đầu để thử lại; bạn vẫn có thể dùng chữ."))
        run.cancel.set()

    def _read(self, run):
        cap = None
        try:
            # Opening a camera after kernel warmup also avoids buffering stale
            # device frames while the detector is still preparing.
            while not run.detector_ready.wait(.05):
                if run.cancel.is_set():
                    return
            if run.cancel.is_set():
                return
            if isinstance(run.source, int):
                cap = cv2.VideoCapture(run.source, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                cap = cv2.VideoCapture(run.source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
            if not cap.isOpened():
                raise ValueError("capture_open_failed")
            fps = cap.get(cv2.CAP_PROP_FPS)
            fps = fps if 1 <= fps <= 240 else 30.
            run.started = base = time.perf_counter()
            preview_at, next_due = -1e6, 0.
            while not run.cancel.is_set():
                ok, bgr = cap.read()
                if not ok:
                    if run.source_kind == "camera" and not run.cancel.is_set():
                        self._error(run, "camera_disconnected")
                    break
                if run.source_kind != "camera":
                    run.cancel.wait(max(0, base + run.captured / fps - time.perf_counter()))
                    capture_ms = run.captured * 1000 / fps
                else:
                    capture_ms = (time.perf_counter() - base) * 1000
                if run.cancel.is_set():
                    break
                stamp = time.perf_counter() * 1000
                run.captured += 1
                # Preview has a separate low-resolution copy, never fed to the model.
                if stamp - preview_at >= 100:
                    h, w = bgr.shape[:2]
                    preview = cv2.resize(bgr, (round(w * min(1., 640 / w)), round(h * min(1., 640 / w))))
                    success, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 78])
                    if success:
                        self.emit(run, dict(type="preview", jpeg=base64.b64encode(encoded).decode("ascii")))
                    preview_at = stamp
                if capture_ms + .01 < next_due:
                    run.capped += 1
                    continue
                next_due = (int(capture_ms / 40) + 1) * 40
                item = (bgr, run.captured, capture_ms, stamp)
                try:
                    run.frames.put_nowait(item)
                except queue.Full:
                    try:
                        run.frames.get_nowait()
                        run.dropped += 1
                    except queue.Empty:
                        pass
                    run.frames.put_nowait(item)
        except Exception as exc:
            self._error(run, type(exc).__name__ + ": " + str(exc))
        finally:
            if cap is not None:
                cap.release()
            run.reader_done.set()

    def _activity(self, run, **extra):
        with run.lock:
            inflight = run.inflight
        self.emit(run, dict(type="capture", status=run.state, source_kind=run.source_kind,
            captured=run.captured, processed=run.processed, dropped=run.dropped, fps_cap_drops=run.capped,
            processed_fps=run.processed / max(.001, time.perf_counter() - run.started),
            detector_warmup_ms=run.detector_warmup_ms,
            inflight_segments=inflight, queued_segments=run.segments.qsize(),
            **run.last_activity, **extra))

    def _enqueue(self, run, processor, boundary):
        if boundary is None or run.cancel.is_set():
            return
        boundary = extend_context(boundary, [f.meta() for f in processor.frames])
        boundary["decision_captured_monotonic_ms"] = processor.frames[-1].captured_monotonic_ms
        run.segment_number += 1
        sid = f"{run.stream_id}:{run.segment_number}"
        frozen = processor.snapshot(boundary["selected_frame_ids"])
        if len(frozen.frames) < 6 or boundary["reason"] in {"gesture_duration_limit", "insufficient_segment_frames"}:
            self.emit(run, dict(type="recognition_unavailable", segment_id=sid,
                quality_warning="Ký từng từ rồi đưa tay về tư thế nghỉ để ứng dụng nhận đủ từ.",
                policy=dict(disposition="unavailable", committed=False, reasons=[boundary["reason"]])))
            return
        with run.lock:
            run.inflight += 1
        try:
            run.segments.put_nowait((sid, frozen, boundary, time.perf_counter() * 1000))
        except queue.Full:
            with run.lock:
                run.inflight -= 1
            self.emit(run, dict(type="recognition_unavailable", segment_id=sid,
                quality_warning="Máy đang xử lý chậm. Bạn chờ một chút rồi ký lại từ vừa rồi.",
                policy=dict(disposition="unavailable", committed=False, reasons=["inference_queue_full"])))
        self._activity(run)

    def _detect(self, run):
        processor = None
        try:
            processor = MemoryProcessor(self.root)
            run.detector_warmup_ms = processor.warmup()
            gate = make_gate(self.engine.manifest)
            run.detector_ready.set()
            last_notice = 0.
            while not run.cancel.is_set():
                try:
                    bgr, fid, capture_ms, stamp = run.frames.get(timeout=.1)
                except queue.Empty:
                    if run.reader_done.is_set():
                        # EOF can flush for review, but End cancellation never commits a tail.
                        self._enqueue(run, processor, gate.flush())
                        break
                    continue
                frame = processor.append(bgr, fid, capture_ms, stamp)
                run.processed += 1
                boundary = gate.feed(frame.pose, capture_ms, fid)
                has_pose = bool((frame.pose[:33, 3] >= .5).any())
                run.state = ("signing" if gate.state in {"signing", "waiting_for_boundary", "priming"}
                             else "ready" if has_pose else "no_person")
                run.last_activity = dict(has_pose=has_pose,
                    hand_count=int((frame.pose[33:54, 3] > 0).any()) + int((frame.pose[54:, 3] > 0).any()),
                    has_face=frame.faces == 1, boundary_state=gate.state,
                    detect_ms=frame.preprocess_ms, frame_age_ms=time.perf_counter() * 1000 - stamp,
                    face_ms=frame.face_ms, pose_hands_ms=frame.pose_hands_ms,
                    source_width=frame.source_width, source_height=frame.source_height,
                    buffer_frames=len(processor.frames))
                self._enqueue(run, processor, boundary)
                processor.prune(capture_ms)
                now = time.perf_counter()
                if now - last_notice >= .2:
                    self._activity(run)
                    last_notice = now
        except Exception as exc:
            self._error(run, type(exc).__name__ + ": " + str(exc))
        finally:
            if processor is not None:
                processor.close()
            run.detector_done.set()

    def _infer(self, run):
        while not run.cancel.is_set():
            try:
                sid, frozen, boundary, queued_ms = run.segments.get(timeout=.1)
            except queue.Empty:
                if run.detector_done.is_set():
                    run.state = "ended"
                    self._activity(run)
                    break
                continue
            try:
                started = time.perf_counter() * 1000
                pose, mouth, info = frozen.finish()
                if pose is None or mouth is None:
                    result = dict(status="unavailable", reason="fusion_requires_both", mode="fusion")
                    timing = {}
                else:
                    sign, lip, timing = self.engine.features(pose, mouth)
                    result = self.engine.predict(sign, lip, "fusion")
                finished = time.perf_counter() * 1000
                timing.update(queue_ms=started - queued_ms, inference_wall_ms=finished - started,
                    decision_to_result_ms=finished - queued_ms,
                    decision_capture_to_result_ms=finished - boundary["decision_captured_monotonic_ms"],
                    last_selected_capture_to_result_ms=finished - frozen.frames[-1].captured_monotonic_ms,
                    emitted_monotonic_ms=finished, clock="python_performance_counter_ms_same_host")
                last_active = next((f for f in reversed(frozen.frames)
                    if f.capture_ms == boundary.get("last_active_capture_ms")), None)
                if last_active is not None:
                    timing["last_active_capture_to_result_ms"] = finished - last_active.captured_monotonic_ms
                event = recognition_event(result, info, boundary, self.mapping, self.model, sid, timing)
                self.emit(run, event)
            except Exception as exc:
                self._error(run, type(exc).__name__ + ": " + str(exc))
            finally:
                with run.lock:
                    run.inflight -= 1
                self._activity(run)
                # Release shared image references before waiting on the next item.
                del frozen
