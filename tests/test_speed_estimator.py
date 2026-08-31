"""Tests for geometry.speed: real-world estimated_speed from tracked positions."""

from __future__ import annotations

import dataclasses

import pytest

from geometry.homography import GroundPlaneHomography
from geometry.speed import EstimatedSpeedSample, SpeedEstimator
from tracking.tracker import Track

# Same uniform 20px = 1m ground plane as test_homography.py.
PIXEL_POINTS = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
WORLD_POINTS = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]


def _track(object_id, x_center, frame_id, timestamp, y_bottom=60.0):
    # bbox chosen so ground_contact_point (bottom-center) == (x_center, y_bottom)
    return Track(
        object_id=object_id,
        class_name="person",
        bbox=(x_center - 10.0, y_bottom - 20.0, x_center + 10.0, y_bottom),
        confidence=0.9,
        timestamp=timestamp,
        frame_id=frame_id,
    )


def test_estimated_speed_field_name_is_the_documented_convention():
    # Section 6's convention is explicit: this value is always "estimated_speed",
    # never bare "speed" -- enforce the dataclass actually says so.
    field_names = {f.name for f in dataclasses.fields(EstimatedSpeedSample)}
    assert "estimated_speed" in field_names
    assert "speed" not in field_names


def test_first_track_for_an_object_produces_no_sample():
    estimator = SpeedEstimator(GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS))
    samples = estimator.update([_track(1, x_center=0.0, frame_id=0, timestamp=0.0)])
    assert samples == []


def test_known_real_world_speed_is_recovered_within_tolerance():
    estimator = SpeedEstimator(GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS))

    # 20px/s in pixel space -> 1m/s in world space at this calibration's scale.
    estimator.update([_track(1, x_center=0.0, frame_id=0, timestamp=0.0)])
    samples = estimator.update([_track(1, x_center=20.0, frame_id=1, timestamp=1.0)])

    assert len(samples) == 1
    sample = samples[0]
    assert sample.estimated_speed == pytest.approx(1.0, rel=1e-3)
    assert sample.world_position[0] == pytest.approx(1.0, abs=1e-6)
    assert sample.object_id == 1
    assert sample.frame_id == 1
    assert sample.timestamp == 1.0


def test_uses_real_elapsed_time_not_assumed_fps():
    # same pixel displacement, twice the elapsed time -> half the estimated_speed.
    estimator = SpeedEstimator(GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS))
    estimator.update([_track(1, x_center=0.0, frame_id=0, timestamp=0.0)])
    samples = estimator.update([_track(1, x_center=20.0, frame_id=1, timestamp=2.0)])

    assert samples[0].estimated_speed == pytest.approx(0.5, rel=1e-3)


def test_stationary_object_has_zero_estimated_speed():
    estimator = SpeedEstimator(GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS))
    estimator.update([_track(1, x_center=50.0, frame_id=0, timestamp=0.0)])
    samples = estimator.update([_track(1, x_center=50.0, frame_id=1, timestamp=1.0)])

    assert samples[0].estimated_speed == pytest.approx(0.0, abs=1e-9)


def test_multiple_objects_are_tracked_independently():
    estimator = SpeedEstimator(GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS))
    estimator.update(
        [
            _track(1, x_center=0.0, frame_id=0, timestamp=0.0),
            _track(2, x_center=0.0, frame_id=0, timestamp=0.0),
        ]
    )
    samples = estimator.update(
        [
            _track(1, x_center=20.0, frame_id=1, timestamp=1.0),  # 1 m/s
            _track(2, x_center=40.0, frame_id=1, timestamp=1.0),  # 2 m/s
        ]
    )

    speed_by_id = {s.object_id: s.estimated_speed for s in samples}
    assert speed_by_id[1] == pytest.approx(1.0, rel=1e-3)
    assert speed_by_id[2] == pytest.approx(2.0, rel=1e-3)
