"""Tests for geometry.zone: point-in-polygon zone containment with debounce."""

from __future__ import annotations

import pytest

from geometry.zone import Zone, ZoneDetector, load_camera_zones, point_in_polygon

SQUARE = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]


def test_point_in_polygon_inside():
    assert point_in_polygon(SQUARE, (50.0, 50.0)) is True


def test_point_in_polygon_outside():
    assert point_in_polygon(SQUARE, (200.0, 200.0)) is False


def test_point_in_polygon_on_edge_counts_as_inside():
    assert point_in_polygon(SQUARE, (10.0, 50.0)) is True


def test_invalid_debounce_frames_raises():
    with pytest.raises(ValueError):
        ZoneDetector([Zone(id="z1", polygon=SQUARE)], debounce_frames=0)


def test_entry_is_confirmed_only_after_debounce_frames_consecutive_inside_reads():
    zone = Zone(id="z1", polygon=SQUARE)
    detector = ZoneDetector([zone], debounce_frames=3)
    inside_point = (50.0, 50.0)

    assert detector.update(1, inside_point, timestamp=0.0, frame_id=0) == []
    assert detector.update(1, inside_point, timestamp=1.0, frame_id=1) == []  # 2 in a row, not yet 3

    transitions = detector.update(1, inside_point, timestamp=2.0, frame_id=2)  # 3rd in a row
    assert len(transitions) == 1
    assert transitions[0].transition == "entered"
    assert transitions[0].zone_id == "z1"
    assert transitions[0].object_id == 1


def test_exit_is_confirmed_only_after_debounce_frames_consecutive_outside_reads():
    zone = Zone(id="z1", polygon=SQUARE)
    detector = ZoneDetector([zone], debounce_frames=2)
    inside_point = (50.0, 50.0)
    outside_point = (200.0, 200.0)

    detector.update(1, inside_point, timestamp=0.0, frame_id=0)
    entered = detector.update(1, inside_point, timestamp=1.0, frame_id=1)
    assert len(entered) == 1 and entered[0].transition == "entered"

    assert detector.update(1, outside_point, timestamp=2.0, frame_id=2) == []  # 1st outside read
    exited = detector.update(1, outside_point, timestamp=3.0, frame_id=3)  # 2nd outside read
    assert len(exited) == 1
    assert exited[0].transition == "exited"


def test_flicker_at_the_boundary_is_suppressed_by_debounce():
    zone = Zone(id="z1", polygon=SQUARE)
    detector = ZoneDetector([zone], debounce_frames=3)
    inside_point = (50.0, 50.0)
    outside_point = (200.0, 200.0)

    # rapid single-frame flicker -- never 3 consecutive reads of the same
    # state, so debounce should suppress every transition.
    flicker_sequence = [inside_point, outside_point, inside_point, outside_point, inside_point, outside_point] * 3

    all_transitions = []
    for i, point in enumerate(flicker_sequence):
        all_transitions.extend(detector.update(1, point, timestamp=float(i), frame_id=i))

    assert all_transitions == []


def test_sustained_entry_after_flicker_still_gets_confirmed():
    zone = Zone(id="z1", polygon=SQUARE)
    detector = ZoneDetector([zone], debounce_frames=3)
    inside_point = (50.0, 50.0)
    outside_point = (200.0, 200.0)

    # flicker, ending back outside so no partial "inside" streak carries over
    # into the sustained phase below (an outside read matches the still-
    # unconfirmed-outside state, which resets the pending streak to 0).
    for i, point in enumerate([inside_point, outside_point, inside_point, outside_point]):
        detector.update(1, point, timestamp=float(i), frame_id=i)

    # a genuinely fresh, sustained entry now needs its own debounce_frames
    # consecutive reads -- confirms on the 3rd, not before.
    assert detector.update(1, inside_point, timestamp=10.0, frame_id=10) == []
    assert detector.update(1, inside_point, timestamp=11.0, frame_id=11) == []
    transitions = detector.update(1, inside_point, timestamp=12.0, frame_id=12)

    assert len(transitions) == 1
    assert transitions[0].transition == "entered"


def test_objects_and_zones_tracked_independently():
    zones = [Zone(id="z1", polygon=SQUARE), Zone(id="z2", polygon=[(p[0] + 500, p[1]) for p in SQUARE])]
    detector = ZoneDetector(zones, debounce_frames=1)

    t1 = detector.update(1, (50.0, 50.0), timestamp=0.0, frame_id=0)  # object 1 enters z1
    t2 = detector.update(2, (550.0, 50.0), timestamp=0.0, frame_id=0)  # object 2 enters z2

    assert len(t1) == 1 and t1[0].zone_id == "z1" and t1[0].object_id == 1
    assert len(t2) == 1 and t2[0].zone_id == "z2" and t2[0].object_id == 2


def test_load_camera_zones_reads_the_repo_demo_config():
    zones = load_camera_zones("demo", configs_dir="configs/cameras")
    assert len(zones) == 1
    assert zones[0].id == "restricted_area"
    assert point_in_polygon(zones[0].polygon, (50.0, 50.0)) is True
