"""Tests for geometry.homography: ground-plane calibration and pixel->world mapping."""

from __future__ import annotations

import pytest

from geometry.homography import GroundPlaneHomography, ground_contact_point, load_camera_homography

# A uniform 20px = 1m ground plane, easy to hand-verify: pixel (x, y) -> world (x/20, y/20).
PIXEL_POINTS = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
WORLD_POINTS = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]


def test_ground_contact_point_is_bottom_center_not_centroid():
    assert ground_contact_point((10.0, 20.0, 30.0, 60.0)) == (20.0, 60.0)


def test_pixel_to_world_recovers_known_point_within_tolerance():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)

    x, y = homography.pixel_to_world((50.0, 50.0))
    assert x == pytest.approx(2.5, abs=1e-6)
    assert y == pytest.approx(2.5, abs=1e-6)

    # a point not in the calibration set, still on the plane
    x, y = homography.pixel_to_world((20.0, 80.0))
    assert x == pytest.approx(1.0, abs=1e-6)
    assert y == pytest.approx(4.0, abs=1e-6)


def test_pixel_to_world_recovers_the_calibration_points_themselves():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    for pixel, expected_world in zip(PIXEL_POINTS, WORLD_POINTS):
        x, y = homography.pixel_to_world(pixel)
        assert x == pytest.approx(expected_world[0], abs=1e-6)
        assert y == pytest.approx(expected_world[1], abs=1e-6)


def test_at_least_four_correspondences_are_required():
    with pytest.raises(ValueError):
        GroundPlaneHomography(PIXEL_POINTS[:3], WORLD_POINTS[:3])


def test_mismatched_point_counts_raise():
    with pytest.raises(ValueError):
        GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS[:3])


def test_from_config_matches_direct_construction(tmp_path):
    config_path = tmp_path / "demo.json"
    config_path.write_text(
        '{"camera_id": "demo", "correspondences": ['
        '{"pixel": [0, 0], "world": [0, 0]},'
        '{"pixel": [100, 0], "world": [5, 0]},'
        '{"pixel": [100, 100], "world": [5, 5]},'
        '{"pixel": [0, 100], "world": [0, 5]}'
        "]}"
    )
    homography = GroundPlaneHomography.from_config(config_path)
    x, y = homography.pixel_to_world((50.0, 50.0))
    assert x == pytest.approx(2.5, abs=1e-6)
    assert y == pytest.approx(2.5, abs=1e-6)


def test_load_camera_homography_reads_the_repo_demo_config():
    # configs/cameras/demo.json is an illustrative example shipped in the repo,
    # using the same 20px = 1m scale as the synthetic tests above.
    homography = load_camera_homography("demo", configs_dir="configs/cameras")
    x, y = homography.pixel_to_world((50.0, 50.0))
    assert x == pytest.approx(2.5, abs=1e-6)
    assert y == pytest.approx(2.5, abs=1e-6)
