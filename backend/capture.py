"""Paced capture, latest-frame detection and bounded inference on independent workers."""
from __future__ import annotations

from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Callable

import cv2

from .landmarks import LandmarkDetector
from .recognition import Recognizer, Segmenter
from .live_segmenter import LiveSegmenter


@dataclass
class Run:
    generation: int
    source: str | int
    source_kind: str
    cancel: threading.Event = field(default_factory=threading.Event)
    reader_done: threading.Event = field(default_factory=threading.Event)
    detector_ready: threading.Event = field(default_factory=threading.Event)
    detector_done: threading.Event = field(default_factory=threading.Event)
    frames: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=1))
    segments: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=2))
    threads: list = field(default_factory=list)
    captured: int = 0
    processed: int = 0
    dropped: int = 0
    inflight: int = 0
    segment_lock: threading.Lock = field(default_factory=threading.Lock)
    started: float = field(default_factory=time.perf_counter)


class CaptureEngine:
    def __init__(self, recognizer: Recognizer, publish: Callable[[dict], None]):
        self.recognizer = recognizer
        self.publish = publish
        self.current: Run | None = None
        self.preview: bytes | None = None
        self.preview_version = 0
        self.preview_lock = threading.Lock()
        self.control = threading.RLock()
        self.generation = 0

    def emit(self, run: Run, event: dict):
        if self.current is run and not run.cancel.is_set():
            self.publish({**event, "generation": run.generation})

    def start(self, source: str | int, source_kind: str) -> int:
        with self.control:
            self.stop()
            self.generation += 1
            run = Run(self.generation, source, source_kind)
            self.current = run
            with self.preview_lock:
                self.preview = None
                self.preview_version += 1
            self.emit(run, {"type": "capture", "status": "starting", "source_kind": source_kind})
            for name, target in (("inference", self._infer), ("detect", self._detect), ("capture", self._read)):
                thread = threading.Thread(target=target, args=(run,), name=f"clinic-{name}-{run.generation}", daemon=True)
                run.threads.append(thread)
                thread.start()
            return run.generation

    def stop(self):
        with self.control:
            run = self.current
            if run is None:
                return
            run.cancel.set()
            self.current = None
            for thread in run.threads:
                if thread is not threading.current_thread():
                    thread.join(timeout=5)
            survivors = [thread.name for thread in run.threads if thread.is_alive()]
            if survivors:
                raise RuntimeError(f"Capture worker has not stopped: {survivors}")

    def _read(self, run: Run):
        capture = None
        try:
            if isinstance(run.source, int):
                capture = cv2.VideoCapture(run.source, cv2.CAP_DSHOW)
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                capture.set(cv2.CAP_PROP_FPS, 30)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                capture = cv2.VideoCapture(run.source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
            if not capture.isOpened():
                raise RuntimeError("Không mở được camera/video. Kiểm tra nguồn hình rồi thử lại.")
            fps = capture.get(cv2.CAP_PROP_FPS)
            fps = fps if 1 <= fps <= 240 else 30.0
            while not run.detector_ready.wait(timeout=0.05):
                if run.cancel.is_set():
                    return
            base = time.perf_counter()
            run.started = base
            preview_at = 0.0
            while not run.cancel.is_set():
                ok, bgr = capture.read()
                if not ok:
                    break
                if run.source_kind != "camera":
                    target = base + run.captured / fps
                    run.cancel.wait(max(0, target - time.perf_counter()))
                    timestamp_ms = run.captured * 1000.0 / fps
                else:
                    timestamp_ms = (time.perf_counter() - base) * 1000
                if run.cancel.is_set():
                    break
                epoch_ms = time.time() * 1000
                height, width = bgr.shape[:2]
                ratio = min(1.0, 640 / max(height, width))
                if ratio < 1:
                    bgr = cv2.resize(bgr, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
                run.captured += 1
                item = (bgr, timestamp_ms, epoch_ms)
                try:
                    run.frames.put_nowait(item)
                except queue.Full:
                    try:
                        run.frames.get_nowait()
                        run.dropped += 1
                    except queue.Empty:
                        pass
                    run.frames.put_nowait(item)
                now = time.perf_counter()
                if now - preview_at >= 1 / 20:
                    success, encoded = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 78])
                    if success:
                        with self.preview_lock:
                            self.preview = encoded.tobytes()
                            self.preview_version += 1
                    preview_at = now
        except Exception as error:
            self.emit(run, {"type": "capture", "status": "error", "message": str(error)})
            run.cancel.set()
        finally:
            if capture is not None:
                capture.release()
            run.reader_done.set()

    def _queue_segment(self, run: Run, segment):
        if segment is None or run.cancel.is_set():
            return
        try:
            with run.segment_lock:
                run.inflight += 1
            run.segments.put_nowait(segment)
        except queue.Full:
            with run.segment_lock:
                run.inflight -= 1
            self.emit(run, {"type": "capture", "status": "error", "message": "Máy đang quá tải. Vui lòng dừng, chờ xử lý xong rồi thử lại."})
            run.cancel.set()

    def _detect(self, run: Run):
        segmenter = LiveSegmenter()
        last_notice = 0.0
        try:
            with LandmarkDetector(self.recognizer.assets) as detector:
                run.detector_ready.set()
                while not run.cancel.is_set():
                    try:
                        bgr, timestamp_ms, epoch_ms = run.frames.get(timeout=0.15)
                    except queue.Empty:
                        if run.reader_done.is_set():
                            self._queue_segment(run, segmenter.flush())
                            break
                        continue
                    started = time.perf_counter()
                    landmarks = detector.process(bgr, timestamp_ms)
                    # Keep observed timing with the frame, so dropped capture
                    # frames cannot masquerade as a high-confidence clean word.
                    landmarks.clinic_timestamp_ms = timestamp_ms
                    run.processed += 1
                    self._queue_segment(run, segmenter.consume(landmarks, timestamp_ms, epoch_ms))
                    now = time.perf_counter()
                    if now - last_notice >= 0.16:
                        has_pose = landmarks.pose_landmarks is not None
                        hand_count = int(landmarks.left_hand_landmarks is not None) + int(landmarks.right_hand_landmarks is not None)
                        status = "signing" if segmenter.frames else "ready" if has_pose else "no_person"
                        self.emit(run, {
                            "type": "capture", "status": status, "source_kind": run.source_kind,
                            "has_pose": has_pose, "hand_count": hand_count,
                            "captured": run.captured, "processed": run.processed, "dropped": run.dropped,
                            "processed_fps": run.processed / max(now - run.started, 0.001),
                            "detect_ms": (now - started) * 1000,
                            "frame_age_ms": time.time() * 1000 - epoch_ms,
                            "queued_segments": run.segments.qsize(),
                            "inflight_segments": run.inflight,
                            "motion_detected": segmenter.moving,
                            "buffer_frames": len(segmenter.frames),
                        })
                        last_notice = now
        except Exception as error:
            self.emit(run, {"type": "capture", "status": "error", "message": str(error)})
            run.cancel.set()
        finally:
            run.detector_done.set()

    def _infer(self, run: Run):
        while not run.cancel.is_set():
            try:
                segment = run.segments.get(timeout=0.15)
            except queue.Empty:
                if run.detector_done.is_set():
                    self.emit(run, {"type": "capture", "status": "ended", "source_kind": run.source_kind,
                                    "inflight_segments": 0, "queued_segments": 0,
                                    "captured": run.captured, "processed": run.processed, "dropped": run.dropped,
                                    "processed_fps": run.processed / max(time.perf_counter() - run.started, 0.001)})
                    break
                continue
            try:
                result = self.recognizer.predict(segment)
                self.emit(run, {"type": "recognition", **result})
            except Exception as error:
                self.emit(run, {"type": "capture", "status": "error", "message": str(error)})
                run.cancel.set()
            finally:
                with run.segment_lock:
                    run.inflight -= 1

    def preview_frame(self):
        with self.preview_lock:
            return self.preview_version, self.preview
