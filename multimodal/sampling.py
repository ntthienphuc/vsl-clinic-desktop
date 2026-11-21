"""Bounded detector cadence and provenance of actual scheduled observations."""

DETECTOR_FPS = 25
# At the fixed 25-fps cadence this holds up to 480 ms of scheduled video.
# It covers short CPU bursts, then loses old frames explicitly under overload.
FRAME_QUEUE_CAPACITY = 12


def observation_continuity(sequences):
    """Intentional cadence limiting is distinct from frames lost to overload.

    Sequence IDs are assigned before enqueue, so replacing an old queued frame
    leaves a detectable hole. Missing provenance cannot certify continuity.
    """
    if not sequences or any(type(s) is not int or s < 1 for s in sequences):
        return dict(sampling_complete=None, dropped_scheduled_frames=None)
    gaps = [b - a for a, b in zip(sequences, sequences[1:])]
    if any(gap < 1 for gap in gaps):
        return dict(sampling_complete=False, dropped_scheduled_frames=None)
    missing = sum(gap - 1 for gap in gaps)
    return dict(sampling_complete=missing == 0, dropped_scheduled_frames=missing)
