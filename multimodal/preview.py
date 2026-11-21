"""Bounded display-only encoder, independent of detector and model sampling."""
import queue
import threading
import time

import cv2


class LatestPreview:
    def __init__(self, publish, cancel, reader_done, fps=30):
        self.publish, self.cancel, self.reader_done = publish, cancel, reader_done
        self.period = 1 / fps
        self.frames = queue.Queue(maxsize=1)
        self.sent = self.dropped = self.errors = 0
        self.last_age_ms = 0.
        self.thread = threading.Thread(target=self._run, name='clinic-preview', daemon=True)

    def offer(self, frame, captured_ms):
        # The reader only offers a reference. Resize/JPEG/transport never hold
        # up capture; old preview frames may be discarded, never model frames.
        try:
            self.frames.put_nowait((frame, captured_ms))
        except queue.Full:
            try:
                self.frames.get_nowait()
                self.dropped += 1
            except queue.Empty:
                pass
            self.frames.put_nowait((frame, captured_ms))

    def _run(self):
        due = time.perf_counter()
        while not self.cancel.is_set():
            if self.cancel.wait(max(0., due - time.perf_counter())):
                return
            try:
                frame, captured_ms = self.frames.get(timeout=.05)
            except queue.Empty:
                if self.reader_done.is_set():
                    return
                continue
            try:
                h, w = frame.shape[:2]
                ratio = min(1., 640 / max(w, h))
                preview = cv2.resize(frame, (round(w * ratio), round(h * ratio))) if ratio < 1 else frame
                ok, encoded = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ok and not self.cancel.is_set():
                    self.publish(encoded.tobytes())
                    self.sent += 1
                    self.last_age_ms = time.perf_counter() * 1000 - captured_ms
            except (cv2.error, OSError):
                self.errors += 1
            # Preserve the cadence without catch-up bursts after a slow frame.
            due = max(due + self.period, time.perf_counter())

    def stats(self):
        return dict(preview_frames=self.sent, preview_dropped=self.dropped,
                    preview_errors=self.errors, preview_age_ms=self.last_age_ms,
                    preview_target_fps=round(1/self.period))
