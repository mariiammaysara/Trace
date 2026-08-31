"""Tests for trajectories.trajectory: per-step motion analysis and per-object tracking."""

from __future__ import annotations

import math

import pytest

from tracking.tracker import Track
from trajectories.trajectory import Trajectory, TrajectoryManager


def test_first_point_produces_no_motion_step():
    trajectory = Trajectory(object_id=1)
    step = trajectory.update((0.0, 0.0), timestamp=0.0, frame_id=0)
    assert step is None


def test_constant_velocity_gives_consistent_speed_direction_and_zero_acceleration():
    trajectory = Trajectory(object_id=1, stationary_speed_threshold=30.0)
    dt = 0.1
    steps = []
    for i in range(5):
        x = i * 50.0  # 500 px/s along +x
        step = trajectory.update((x, 0.0), timestamp=i * dt, frame_id=i)
        if step is not None:
            steps.append(step)

    assert len(steps) == 4
    for step in steps:
        assert step.velocity == pytest.approx((500.0, 0.0))
        assert step.speed == pytest.approx(500.0)
        assert step.direction == pytest.approx(0.0, abs=1e-9)
        assert step.is_stationary is False

    # first step has no prior velocity to diff against; every step after does,
    # and since velocity never changes, acceleration should be ~0.
    assert steps[0].acceleration is None
    for step in steps[1:]:
        assert step.acceleration == pytest.approx((0.0, 0.0), abs=1e-6)


def test_a_stop_produces_a_large_deceleration_then_reads_stationary():
    trajectory = Trajectory(object_id=1, stationary_speed_threshold=30.0)
    dt = 0.1

    trajectory.update((0.0, 0.0), timestamp=0.0, frame_id=0)
    moving_step = trajectory.update((50.0, 0.0), timestamp=dt, frame_id=1)  # v = (500, 0)
    still_moving_step = trajectory.update((100.0, 0.0), timestamp=2 * dt, frame_id=2)  # v = (500, 0), a = 0
    stop_step = trajectory.update((100.0, 0.0), timestamp=3 * dt, frame_id=3)  # v = (0, 0), a = (-5000, 0)
    settled_step = trajectory.update((100.0, 0.0), timestamp=4 * dt, frame_id=4)  # v = (0, 0), a = 0

    assert moving_step.is_stationary is False
    assert still_moving_step.is_stationary is False
    assert still_moving_step.acceleration == pytest.approx((0.0, 0.0), abs=1e-6)

    assert stop_step.speed == pytest.approx(0.0)
    assert stop_step.is_stationary is True
    assert stop_step.acceleration[0] < -1000.0  # sharp deceleration -- the SUDDEN_STOP signal Phase 7 will use

    assert settled_step.is_stationary is True
    assert settled_step.acceleration == pytest.approx((0.0, 0.0), abs=1e-6)


def test_direction_change_is_reflected_in_the_angle():
    trajectory = Trajectory(object_id=1, stationary_speed_threshold=30.0)
    dt = 0.1

    trajectory.update((0.0, 0.0), timestamp=0.0, frame_id=0)
    rightward_step = trajectory.update((50.0, 0.0), timestamp=dt, frame_id=1)  # moving +x
    trajectory.update((50.0, 50.0), timestamp=2 * dt, frame_id=2)  # transition point
    downward_step = trajectory.update((50.0, 100.0), timestamp=3 * dt, frame_id=3)  # moving +y (down, image coords)

    assert rightward_step.direction == pytest.approx(0.0, abs=1e-9)
    assert downward_step.direction == pytest.approx(math.pi / 2, abs=1e-9)


def test_jitter_around_a_stationary_point_reads_stationary_despite_noise():
    # ~30fps, up to +/-2px jitter (so up to ~4px frame-to-frame swing) around a
    # fixed point -- realistic detector/tracker noise for a genuinely
    # stationary object. threshold is tuned for this frame rate/jitter
    # combination (see DEFAULT_STATIONARY_SPEED_THRESHOLD's docstring:
    # there's no one true default, it's a per-deployment setting).
    trajectory = Trajectory(object_id=1, stationary_speed_threshold=150.0)
    dt = 1.0 / 30.0
    jitter_offsets = [0.0, 1.0, -1.0, 2.0, -2.0, 0.5, -1.5, 0.0]

    steps = []
    for i, offset in enumerate(jitter_offsets):
        step = trajectory.update((100.0 + offset, 100.0), timestamp=i * dt, frame_id=i)
        if step is not None:
            steps.append(step)

    assert len(steps) == len(jitter_offsets) - 1
    assert all(step.is_stationary for step in steps)
    # jitter genuinely produces nonzero speed readings -- this is tolerance of
    # real noise, not just a degenerate "speed is always exactly 0" check.
    assert any(step.speed > 0.0 for step in steps)


def test_trajectory_manager_routes_tracks_to_per_object_trajectories_via_centroid():
    manager = TrajectoryManager(stationary_speed_threshold=30.0)

    def track(object_id, x_min, y_min, x_max, y_max, frame_id, timestamp):
        return Track(
            object_id=object_id,
            class_name="person",
            bbox=(x_min, y_min, x_max, y_max),
            confidence=0.9,
            timestamp=timestamp,
            frame_id=frame_id,
        )

    frame1_tracks = [
        track(1, 0.0, 0.0, 20.0, 20.0, frame_id=0, timestamp=0.0),  # centroid (10, 10)
        track(2, 100.0, 100.0, 120.0, 120.0, frame_id=0, timestamp=0.0),  # centroid (110, 110)
    ]
    steps1 = manager.update(frame1_tracks)
    assert steps1 == []  # first point for both objects -- nothing to diff against yet

    frame2_tracks = [
        track(1, 40.0, 0.0, 60.0, 20.0, frame_id=1, timestamp=0.1),  # centroid (50, 10)
        track(2, 100.0, 100.0, 120.0, 120.0, frame_id=1, timestamp=0.1),  # unchanged
    ]
    steps2 = manager.update(frame2_tracks)
    assert len(steps2) == 2

    step_obj1 = next(s for s in steps2 if s.object_id == 1)
    step_obj2 = next(s for s in steps2 if s.object_id == 2)
    assert step_obj1.speed == pytest.approx(400.0)  # (50-10)/0.1
    assert step_obj2.is_stationary is True

    assert manager.get_path(1) == [(10.0, 10.0), (50.0, 10.0)]
    assert manager.get_path(2) == [(110.0, 110.0), (110.0, 110.0)]
    assert manager.get_path(999) == []
