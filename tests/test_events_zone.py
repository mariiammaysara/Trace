"""Tests for events.zone_entered / events.zone_exited (pure event builders),
plus end-to-end zone-flicker suppression through EventEngine."""

from __future__ import annotations

import pytest

from events.engine import EventEngine
from events.zone_entered import build_event as build_entered_event
from events.zone_exited import build_event as build_exited_event
from geometry.homography import GroundPlaneHomography
from geometry.zone import Zone, ZoneTransition
from tracking.tracker import Track

PIXEL_POINTS = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
WORLD_POINTS = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]
SQUARE = [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)]


def _track(object_id, x, y, timestamp, frame_id, w=20.0, confidence=0.9, class_name="person"):
    return Track(
        object_id=object_id, class_name=class_name,
        bbox=(x - w / 2, y - w / 2, x + w / 2, y + w / 2),
        confidence=confidence, timestamp=timestamp, frame_id=frame_id,
    )


def test_build_entered_event_requires_an_entered_transition():
    track = _track(1, 50, 50, 0.0, 0)
    exited = ZoneTransition(zone_id="z1", object_id=1, transition="exited", timestamp=0.0, frame_id=0)
    with pytest.raises(ValueError):
        build_entered_event(track, exited, camera_id="cam_1")


def test_build_entered_event_matches_schema():
    track = _track(1, 50, 50, 2.5, 10, confidence=0.7, class_name="car")
    transition = ZoneTransition(zone_id="restricted_area", object_id=1, transition="entered", timestamp=2.5, frame_id=10)
    event = build_entered_event(track, transition, camera_id="cam_1")

    assert event.event_type == "ZONE_ENTERED"
    assert event.metadata == {"zone_id": "restricted_area"}
    assert event.class_name == "car"
    assert event.confidence == 0.7
    assert event.timestamp == 2.5


def test_build_exited_event_matches_schema():
    track = _track(1, 200, 200, 3.0, 20)
    transition = ZoneTransition(zone_id="restricted_area", object_id=1, transition="exited", timestamp=3.0, frame_id=20)
    event = build_exited_event(track, transition, camera_id="cam_1")
    assert event.event_type == "ZONE_EXITED"
    assert event.metadata == {"zone_id": "restricted_area"}


def test_build_exited_event_requires_an_exited_transition():
    track = _track(1, 50, 50, 0.0, 0)
    entered = ZoneTransition(zone_id="z1", object_id=1, transition="entered", timestamp=0.0, frame_id=0)
    with pytest.raises(ValueError):
        build_exited_event(track, entered, camera_id="cam_1")


def _engine(debounce_frames=3):
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    zone = Zone(id="restricted_area", polygon=SQUARE)
    return EventEngine("cam_1", homography, zones=[zone], zone_debounce_frames=debounce_frames)


def test_flicker_at_zone_boundary_produces_no_spurious_events_through_the_engine():
    engine = _engine(debounce_frames=3)
    inside = (50.0, 50.0)
    outside = (200.0, 200.0)
    flicker = [inside, outside, inside, outside, inside, outside] * 3

    zone_events = []
    for i, point in enumerate(flicker):
        track = _track(1, point[0], point[1], timestamp=float(i), frame_id=i)
        events = engine.update([track], timestamp=float(i))
        zone_events += [e for e in events if e.event_type in ("ZONE_ENTERED", "ZONE_EXITED")]

    assert zone_events == []


def test_sustained_zone_entry_and_exit_each_produce_exactly_one_event_through_the_engine():
    engine = _engine(debounce_frames=2)
    points_and_times = [
        ((50.0, 50.0), 0.0), ((50.0, 50.0), 1.0),  # 2 consecutive inside -> ZONE_ENTERED
        ((200.0, 200.0), 2.0), ((200.0, 200.0), 3.0),  # 2 consecutive outside -> ZONE_EXITED
    ]
    all_events = []
    for i, (point, t) in enumerate(points_and_times):
        track = _track(1, point[0], point[1], timestamp=t, frame_id=i)
        all_events += engine.update([track], timestamp=t)

    zone_events = [e for e in all_events if e.event_type in ("ZONE_ENTERED", "ZONE_EXITED")]
    assert [e.event_type for e in zone_events] == ["ZONE_ENTERED", "ZONE_EXITED"]
