from types import SimpleNamespace as NS

from backend.live_segmenter import LiveSegmenter


def observation(offset=0.0, visible=True):
    points = [NS(x=.5, y=.5, visibility=1.0) for _ in range(33)]
    for shoulder, elbow, wrist, hip, x in [(11, 13, 15, 23, .35), (12, 14, 16, 24, .65)]:
        points[shoulder] = NS(x=x, y=.3, visibility=1.0)
        points[elbow] = NS(x=x, y=.6, visibility=1.0)
        points[wrist] = NS(x=x + offset, y=.4, visibility=1.0)
        points[hip] = NS(x=x, y=.8, visibility=1.0)
    hand = NS(landmark=[NS(x=.5 + offset, y=.4, visibility=1.0) for _ in range(21)])
    return NS(pose_landmarks=NS(landmark=points) if visible else None,
              left_hand_landmarks=hand if visible else None,
              right_hand_landmarks=hand if visible else None)


def test_static_raised_hands_never_emit_repeated_words():
    gate = LiveSegmenter()
    for timestamp in range(0, 5000, 50):
        assert gate.consume(observation(), timestamp, timestamp + 10000) is None
    assert gate.flush() is None
    assert not gate.frames


def test_motion_then_hold_emits_once_and_requires_new_motion():
    gate = LiveSegmenter()
    segments = []
    for timestamp in range(0, 4000, 50):
        offset = (timestamp % 200) / 1000 if timestamp < 1000 else .1
        result = gate.consume(observation(offset), timestamp, timestamp + 10000)
        if result:
            segments.append(result)
    assert len(segments) == 1
    assert segments[0]["boundary"] == "stable_hand_hold"
    assert len(segments[0]["frames"]) >= 6
    for timestamp in range(4000, 6000, 50):
        offset = (timestamp % 200) / 1000 if timestamp < 4800 else .1
        result = gate.consume(observation(offset), timestamp, timestamp + 10000)
        if result:
            segments.append(result)
    assert len(segments) == 2


def test_occlusion_discards_partial_gesture_instead_of_emitting_a_word():
    gate = LiveSegmenter()
    for timestamp in range(0, 1000, 50):
        gate.consume(observation((timestamp % 200) / 1000), timestamp, timestamp + 10000)
    assert gate.frames
    for timestamp in range(1000, 2100, 50):
        assert gate.consume(observation(visible=False), timestamp, timestamp + 10000) is None
    assert gate.flush() is None


def test_timestamp_zero_is_valid_for_hold_duration():
    gate = LiveSegmenter()
    gate.base.start_source_ms = 0
    gate.base.frames = [observation()] * 6
    gate.armed = True
    gate.last_motion_ms = 0
    gate.motion_epoch_ms = 10000
    # Keep the base arm state active so the hold endpoint is exercised.
    gate.base.left.is_up = True
    gate.base.right.is_up = True
    result = gate.consume(observation(), 750, 10750)
    assert result and result["boundary"] == "stable_hand_hold"
