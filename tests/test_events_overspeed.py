"""Tests for events.overspeed.OverspeedRule."""

from __future__ import annotations

import pytest

from events.overspeed import OverspeedRule
from geometry.speed import EstimatedSpeedSample
from tracking.tracker import Track


def _track(object_id=1, timestamp=0.0, frame_id=0):
    return Track(object_id=object_id, class_name="car", bbox=(0.0, 0.0, 10.0, 10.0), confidence=0.9, timestamp=timestamp, frame_id=frame_id)


def _sample(object_id, speed, timestamp, frame_id):
    return EstimatedSpeedSample(object_id=object_id, frame_id=frame_id, timestamp=timestamp, world_position=(0.0, 0.0), estimated_speed=speed)


def test_no_sample_produces_no_event():
    rule = OverspeedRule(speed_limit=5.0)
    assert rule.update(_track(), None) is None


def test_single_noisy_spike_does_not_fire_due_to_smoothing():
    # a lone 20.0 spike averaged into a window of 3 normal-speed readings
    # stays at or under the limit (max (2+2+20)/3 = 8.0 <= 10.0), even though
    # the raw spike itself (20.0) is well above it -- smoothing is actually
    # suppressing something here, not just padding an already-harmless value.
    rule = OverspeedRule(speed_limit=10.0, window=3)
    speeds = [2.0, 2.0, 20.0, 2.0, 2.0]
    events = [
        rule.update(_track(timestamp=float(i), frame_id=i), _sample(1, s, timestamp=float(i), frame_id=i))
        for i, s in enumerate(speeds)
    ]
    assert [e for e in events if e is not None] == []


def test_sustained_overspeed_fires_exactly_once():
    rule = OverspeedRule(speed_limit=5.0, window=3)
    speeds = [10.0, 10.0, 10.0, 10.0, 10.0]
    fired = [
        rule.update(_track(timestamp=float(i), frame_id=i), _sample(1, s, timestamp=float(i), frame_id=i))
        for i, s in enumerate(speeds)
    ]
    fired = [e for e in fired if e is not None]
    assert len(fired) == 1
    assert fired[0].event_type == "OVERSPEED"
    assert fired[0].metadata["limit"] == 5.0
    assert fired[0].metadata["estimated_speed"] == 10.0


def test_fires_again_after_dropping_back_under_the_limit():
    rule = OverspeedRule(speed_limit=5.0, window=1)  # window=1 -> no smoothing, immediate response
    speeds = [10.0, 10.0, 1.0, 1.0, 10.0, 10.0]
    fire_count = 0
    for i, s in enumerate(speeds):
        if rule.update(_track(timestamp=float(i), frame_id=i), _sample(1, s, timestamp=float(i), frame_id=i)) is not None:
            fire_count += 1
    assert fire_count == 2


def test_invalid_speed_limit_raises():
    with pytest.raises(ValueError):
        OverspeedRule(speed_limit=0)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        OverspeedRule(speed_limit=5.0, window=0)
