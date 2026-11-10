"""Reversible conversational hold while a visible patient is signing.

This grants processing time before a word is known. It never commits a label.
No accepted word -> resume after the activity/queue settles. Accepted word ->
the existing patient_reply pause remains until the doctor chooses Continue.
"""
class PatientHandover:
    def __init__(self):
        self.owner = None
        self.last_active = 0.
        self.suppressed = False

    def observe(self, playback, capture, automatic, elapsed, now):
        active = (capture.get("status") == "signing" and
                  capture.get("boundary_state") in {"signing", "waiting_for_boundary"} and
                  capture.get("has_face") and capture.get("hand_count", 0) > 0)
        if not active:
            self.suppressed = False
            return False
        self.last_active = now
        if automatic and not self.suppressed and playback and playback["status"] == "playing":
            playback.update(elapsed_ms=elapsed(), status="paused", pause_reason="patient_activity")
            self.owner = playback["id"]
            return True
        return False

    def settle(self, playback, capture, now):
        if not playback or playback.get("status") != "paused" or playback.get("id") != self.owner or playback.get("pause_reason") != "patient_activity":
            return False
        busy = capture.get("status") == "signing" or capture.get("inflight_segments", 0) or capture.get("queued_segments", 0)
        if capture.get("status") in {"error", "idle", "ended"}:
            busy = False
        if busy or now-self.last_active < 1200:
            return False
        playback.update(status="playing", started_at_ms=now)
        playback.pop("pause_reason", None)
        self.owner = None
        return True

    def manual(self):
        self.owner = None
        self.suppressed = True
