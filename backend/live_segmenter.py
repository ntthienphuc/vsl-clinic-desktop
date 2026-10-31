"""Hand-motion endpoints for the existing isolated-word recognizer.

Raised static hands alone never start repeated words. A short stable hold or a
lowered hand ends one word; the conversation layer waits longer to end a turn.
This is a temporal gate, not a continuous-sign language model.
"""
from collections import deque

import numpy as np

from .recognition import Segmenter


class LiveSegmenter:
    HOLD_MS = 700
    MIN_WORD_MS = 500

    def __init__(self):
        self.base = Segmenter()
        self.previous = None
        self.last_motion_ms = None
        self.motion_epoch_ms = None
        self.await_motion = False
        self.armed = False
        self.votes = deque(maxlen=4)
        self.moving = False
        self.last_observed_ms = None

    @property
    def frames(self):
        return self.base.frames if self.armed else []

    def geometry(self, result):
        pose = result.pose_landmarks
        if pose is None:
            return None
        points = pose.landmark
        if min(points[i].visibility for i in (11, 12, 13, 14, 15, 16)) < .5:
            return None
        scale = max(.08, np.linalg.norm([points[11].x - points[12].x, points[11].y - points[12].y]))
        center = np.array([(points[11].x + points[12].x) / 2, (points[11].y + points[12].y) / 2])
        coordinates = [np.array([points[i].x, points[i].y]) for i in (13, 14, 15, 16)]
        for hand in (result.left_hand_landmarks, result.right_hand_landmarks):
            # Fingertips matter for signs with little wrist displacement.
            coordinates.extend([np.array([hand.landmark[i].x, hand.landmark[i].y]) if hand else np.array([np.nan, np.nan])
                                for i in (4, 8, 12, 16, 20)])
        return (np.asarray(coordinates) - center) / scale

    def consume(self, result, timestamp_ms, captured_epoch_ms):
        geometry = self.geometry(result)
        dt = (timestamp_ms - self.last_observed_ms) / 1000 if self.last_observed_ms is not None else 0
        self.moving = False
        if geometry is not None and self.previous is not None and .005 <= dt <= .25:
            distance = np.linalg.norm(geometry - self.previous, axis=1)
            finite = distance[np.isfinite(distance)]
            self.moving = bool(len(finite) and np.percentile(finite, 75) / dt > .32)
        self.previous = geometry
        self.last_observed_ms = timestamp_ms
        self.votes.append(self.moving)
        if self.moving:
            self.last_motion_ms = timestamp_ms
            self.motion_epoch_ms = captured_epoch_ms
        # Missing tracking is unknown. Do not turn an occlusion into a word.
        if geometry is None:
            if self.base.last_timestamp is not None and timestamp_ms - self.base.last_timestamp > 800:
                self.base.reset()
                self.armed = False
                self.votes.clear()
            return None
        if self.await_motion:
            if sum(self.votes) < 3:
                return None
            self.await_motion = False
            self.base.reset()
        if sum(self.votes) >= 2:
            self.armed = True
        segment = self.base.consume(result, timestamp_ms, captured_epoch_ms)
        if segment is not None:
            if not self.armed:
                return None
            self.armed = False
            self.await_motion = True
            self.votes.clear()
            return segment
        if not self.armed and len(self.base.frames) > 12:
            self.base.frames = self.base.frames[-12:]
            self.base.start_source_ms = timestamp_ms
        start = self.base.start_source_ms
        duration = timestamp_ms - (start if start is not None else timestamp_ms)
        quiet = timestamp_ms - (self.last_motion_ms if self.last_motion_ms is not None else timestamp_ms)
        if self.armed and self.base.frames and duration >= self.MIN_WORD_MS and quiet >= self.HOLD_MS:
            segment = self.base.flush()
            self.armed = False
            self.await_motion = True
            self.votes.clear()
            if segment:
                segment["last_active_epoch_ms"] = self.motion_epoch_ms
                segment["boundary"] = "stable_hand_hold"
            return segment
        return None

    def flush(self):
        segment = self.base.flush() if self.armed else None
        self.armed = False
        return segment
