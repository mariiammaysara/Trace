"""Tests for events.stopped.StoppedRule."""

from __future__ import annotations

import pytest

from events.stopped import StoppedRule
from tracking.tracker import Track
from trajectories.trajectory import MotionStep, TrajectoryManager


def _track(timestamp=0.0, frame_id=0, object_id=1, bbox=(0.0, 0.0, 10.0, 10.0)):
    return Track(object_id=object_id, class_name="person", bbox=bbox, confidence=0.9, timestamp=timestamp, frame_id=frame_id)


def _step(is_stationary, timestamp, frame_id=0, object_id=1, speed=0.0):
    return MotionStep(
        object_id=object_id, frame_id=frame_id, timestamp=timestamp, position=(0.0, 0.0),
        displacement=(0.0, 0.0), velocity=(0.0, 0.0), speed=speed, direction=0.0,
        acceleration=None, is_stationary=is_stationary,
    )


def test_no_step_produces_no_event():
    rule = StoppedRule(min_stationary_seconds=2.0)
    assert rule.update(_track(), None) is None


def test_fires_once_after_sustained_stationary_duration():
    rule = StoppedRule(min_stationary_seconds=2.0)
    timestamps = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    fired = []
    for t in timestamps:
        event = rule.update(_track(timestamp=t), _step(is_stationary=True, timestamp=t))
        if event is not None:
            fired.append(event)
    assert len(fired) == 1
    assert fired[0].event_type == "STOPPED"
    assert fired[0].metadata["stationary_duration_seconds"] == pytest.approx(2.0)


def test_does_not_fire_before_duration_threshold_is_reached():
    rule = StoppedRule(min_stationary_seconds=5.0)
    timestamps = [0.0, 0.5, 1.0, 1.5, 2.0]
    fired = [rule.update(_track(timestamp=t), _step(is_stationary=True, timestamp=t)) for t in timestamps]
    assert [e for e in fired if e is not None] == []


def test_a_single_moving_step_resets_the_streak():
    # stationary for 1.5s (not enough), moves for one step, then stationary
    # again -- the earlier stationary time must not carry over into the
    # fresh streak, which needs its own full 2.0s.
    rule = StoppedRule(min_stationary_seconds=2.0)
    sequence = [
        (0.0, True), (1.0, True), (1.5, True),
        (1.6, False),
        (1.7, True), (2.7, True), (3.7, True),
    ]
    fired = []
    for t, stationary in sequence:
        event = rule.update(_track(timestamp=t), _step(is_stationary=stationary, timestamp=t))
        if event is not None:
            fired.append(event)

    assert len(fired) == 1
    assert fired[0].timestamp == pytest.approx(3.7)


def test_jittery_but_effectively_stationary_object_still_fires_stopped():
    # real Trajectory/TrajectoryManager driving StoppedRule with the same
    # jitter sequence Phase 4 used to prove is_stationary tolerates noise --
    # confirming that tolerance survives through to an actual STOPPED event.
    trajectory_manager = TrajectoryManager(stationary_speed_threshold=150.0)
    rule = StoppedRule(min_stationary_seconds=0.15)
    dt = 1.0 / 30.0
    jitter_offsets = [0.0, 1.0, -1.0, 2.0, -2.0, 0.5, -1.5, 0.0]

    fired = []
    for i, offset in enumerate(jitter_offsets):
        t = i * dt
        track = _track(timestamp=t, frame_id=i, bbox=(100.0 + offset - 10.0, 90.0, 100.0 + offset + 10.0, 110.0))
        steps = trajectory_manager.update([track])
        step = steps[0] if steps else None
        event = rule.update(track, step)
        if event is not None:
            fired.append(event)

    assert len(fired) == 1
    assert fired[0].event_type == "STOPPED"


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        StoppedRule(min_stationary_seconds=0)
