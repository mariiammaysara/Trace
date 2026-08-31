"""Tests for events.line_crossed: LINE_CROSSED event construction."""

from __future__ import annotations

from events.event import Event
from events.line_crossed import build_event
from geometry.line_crossing import Line, detect_line_crossing
from tracking.tracker import Track


def _track(object_id=1, class_name="person", confidence=0.9, timestamp=1.0, frame_id=5, bbox=(0.0, 0.0, 10.0, 10.0)):
    return Track(
        object_id=object_id, class_name=class_name, bbox=bbox,
        confidence=confidence, timestamp=timestamp, frame_id=frame_id,
    )


def test_build_event_matches_schema_and_carries_crossing_details():
    line = Line(id="entrance", start=(0.0, 50.0), end=(100.0, 50.0))
    crossing = detect_line_crossing(line, (50.0, 0.0), (50.0, 100.0))
    assert crossing is not None

    track = _track(object_id=7, class_name="car", confidence=0.81, timestamp=3.5, frame_id=12)
    event = build_event(track, crossing, camera_id="cam_1")

    assert isinstance(event, Event)
    assert event.event_type == "LINE_CROSSED"
    assert event.object_id == 7
    assert event.class_name == "car"
    assert event.timestamp == 3.5
    assert event.camera_id == "cam_1"
    assert event.confidence == 0.81
    assert event.metadata["line_id"] == "entrance"
    assert event.metadata["direction"] == crossing.direction
    assert event.metadata["side_before"] == crossing.side_before
    assert event.metadata["side_after"] == crossing.side_after


def test_to_dict_uses_class_key_not_class_name():
    track = _track()
    line = Line(id="l", start=(0.0, 50.0), end=(100.0, 50.0))
    crossing = detect_line_crossing(line, (50.0, 0.0), (50.0, 100.0))
    event = build_event(track, crossing, camera_id="cam_1")

    payload = event.to_dict()
    assert payload["class"] == "person"
    assert "class_name" not in payload
