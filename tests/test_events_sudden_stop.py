"""Tests for events.sudden_stop.SuddenStopRule."""

from __future__ import annotations

import pytest

from events.sudden_stop import SuddenStopRule
from tracking.tracker import Track
from trajectories.trajectory import MotionStep


def _track(timestamp=0.0, frame_id=0, object_id=1):
    return Track(object_id=object_id, class_name="person", bbox=(0.0, 0.0, 10.0, 10.0), confidence=0.9, timestamp=timestamp, frame_id=frame_id)


def _step(speed, acceleration, timestamp, frame_id=0, object_id=1):
    return MotionStep(
        object_id=object_id, frame_id=frame_id, timestamp=timestamp, position=(0.0, 0.0),
        displacement=(0.0, 0.0), velocity=(speed, 0.0), speed=speed, direction=0.0,
        acceleration=acceleration, is_stationary=(speed == 0.0),
    )


def test_no_step_produces_no_event():
    rule = SuddenStopRule(min_deceleration_magnitude=500.0)
    assert rule.update(_track(), None) is None


def test_first_step_never_fires_no_prior_speed_to_compare():
    rule = SuddenStopRule(min_deceleration_magnitude=500.0)
    step = _step(speed=0.0, acceleration=(-5000.0, 0.0), timestamp=0.1)
    assert rule.update(_track(timestamp=0.1), step) is None


def test_sharp_deceleration_fires():
    rule = SuddenStopRule(min_deceleration_magnitude=500.0)
    rule.update(_track(timestamp=0.0), _step(speed=500.0, acceleration=None, timestamp=0.0))
    event = rule.update(_track(timestamp=0.1), _step(speed=0.0, acceleration=(-5000.0, 0.0), timestamp=0.1))

    assert event is not None
    assert event.event_type == "SUDDEN_STOP"
    assert event.metadata["speed_before"] == 500.0
    assert event.metadata["speed_after"] == 0.0


def test_gentle_deceleration_below_threshold_does_not_fire():
    rule = SuddenStopRule(min_deceleration_magnitude=500.0)
    rule.update(_track(timestamp=0.0), _step(speed=100.0, acceleration=None, timestamp=0.0))
    event = rule.update(_track(timestamp=0.1), _step(speed=90.0, acceleration=(-100.0, 0.0), timestamp=0.1))
    assert event is None


def test_large_acceleration_while_speeding_up_does_not_fire():
    # big acceleration magnitude, but speed increased -- not a stop.
    rule = SuddenStopRule(min_deceleration_magnitude=500.0)
    rule.update(_track(timestamp=0.0), _step(speed=0.0, acceleration=None, timestamp=0.0))
    event = rule.update(_track(timestamp=0.1), _step(speed=500.0, acceleration=(5000.0, 0.0), timestamp=0.1))
    assert event is None


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        SuddenStopRule(min_deceleration_magnitude=0)
