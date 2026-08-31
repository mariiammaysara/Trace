"""Tests for events.loitering.LoiteringRule."""

from __future__ import annotations

import pytest

from events.loitering import LoiteringRule
from tracking.tracker import Track
from trajectories.dwell import DwellTracker


def _track(timestamp=0.0, frame_id=0, object_id=1):
    return Track(object_id=object_id, class_name="person", bbox=(0.0, 0.0, 10.0, 10.0), confidence=0.9, timestamp=timestamp, frame_id=frame_id)


def test_fires_once_when_cumulative_dwell_crosses_threshold():
    dwell_tracker = DwellTracker()
    rule = LoiteringRule(min_dwell_seconds=5.0)

    dwell_tracker.update(1, "zone", is_inside=True, timestamp=0.0)
    fired = []
    for t in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]:
        dwell_tracker.update(1, "zone", is_inside=True, timestamp=t)
        event = rule.update(_track(timestamp=t), "zone", dwell_tracker, timestamp=t)
        if event is not None:
            fired.append(event)

    assert len(fired) == 1
    assert fired[0].event_type == "LOITERING"
    assert fired[0].metadata["zone_id"] == "zone"
    assert fired[0].metadata["dwell_seconds"] >= 5.0


def test_does_not_fire_before_threshold():
    dwell_tracker = DwellTracker()
    rule = LoiteringRule(min_dwell_seconds=10.0)
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=0.0)
    fired = []
    for t in [1.0, 2.0, 3.0]:
        dwell_tracker.update(1, "zone", is_inside=True, timestamp=t)
        event = rule.update(_track(timestamp=t), "zone", dwell_tracker, timestamp=t)
        if event is not None:
            fired.append(event)
    assert fired == []


def test_cumulative_dwell_across_multiple_visits_still_fires():
    dwell_tracker = DwellTracker()
    rule = LoiteringRule(min_dwell_seconds=4.0)

    # visit 1: 2 seconds -- not enough on its own
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=0.0)
    dwell_tracker.update(1, "zone", is_inside=False, timestamp=2.0)
    assert rule.update(_track(timestamp=2.0), "zone", dwell_tracker, timestamp=2.0) is None

    # visit 2: another 2 seconds -> cumulative 4.0, should now fire
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=10.0)
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=12.0)
    event = rule.update(_track(timestamp=12.0), "zone", dwell_tracker, timestamp=12.0)
    assert event is not None
    assert event.metadata["dwell_seconds"] == pytest.approx(4.0)


def test_does_not_fire_twice_for_the_same_object_zone_pair():
    dwell_tracker = DwellTracker()
    rule = LoiteringRule(min_dwell_seconds=1.0)
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=0.0)
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=2.0)

    first = rule.update(_track(timestamp=2.0), "zone", dwell_tracker, timestamp=2.0)
    dwell_tracker.update(1, "zone", is_inside=True, timestamp=3.0)
    second = rule.update(_track(timestamp=3.0), "zone", dwell_tracker, timestamp=3.0)

    assert first is not None
    assert second is None


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        LoiteringRule(min_dwell_seconds=0)
