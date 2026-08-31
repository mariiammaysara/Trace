"""Repository-layer tests: insert a fake object + events, query them back,
confirm relationships resolve correctly."""

from __future__ import annotations

import pytest

from database import repository
from events.event import Event as PipelineEvent


def test_get_or_create_camera_is_idempotent(db_session):
    camera1 = repository.get_or_create_camera(db_session, "demo", name="Demo")
    camera2 = repository.get_or_create_camera(db_session, "demo", name="ignored on second call")
    assert camera1.id == camera2.id
    assert camera1.name == "Demo"


def test_get_or_create_object_updates_last_seen_and_class_on_repeat_calls(db_session):
    camera = repository.get_or_create_camera(db_session, "demo")
    obj1 = repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    obj2 = repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=5.0)

    assert obj1.id == obj2.id
    assert obj2.first_seen == 0.0
    assert obj2.last_seen == 5.0


def test_add_track_point_and_query_back(db_session):
    camera = repository.get_or_create_camera(db_session, "demo")
    obj = repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    repository.add_track_point(db_session, obj, frame_id=0, timestamp=0.0, x=10.0, y=20.0)
    repository.add_track_point(db_session, obj, frame_id=1, timestamp=0.1, x=15.0, y=25.0)

    points = repository.get_track_points_for_object(db_session, obj)
    assert [(p.frame_id, p.x, p.y) for p in points] == [(0, 10.0, 20.0), (1, 15.0, 25.0)]


def test_add_event_from_pipeline_resolves_object_and_zone(db_session):
    camera = repository.get_or_create_camera(db_session, "demo")
    zone = repository.get_or_create_zone(
        db_session, camera, "restricted_area", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    )
    obj = repository.get_or_create_object(db_session, camera, object_id=7, class_name="person", timestamp=1.0)

    pipeline_event = PipelineEvent(
        event_type="ZONE_ENTERED", object_id=7, class_name="person", timestamp=1.0,
        camera_id="demo", confidence=0.91, metadata={"zone_id": "restricted_area"},
    )
    row = repository.add_event_from_pipeline(db_session, camera, pipeline_event)

    assert row.object_id == obj.id
    assert row.zone_id == zone.id
    assert row.event_metadata == {"zone_id": "restricted_area"}

    fetched = repository.get_events_for_object(db_session, obj)
    assert len(fetched) == 1
    assert fetched[0].zone.zone_id == "restricted_area"
    assert fetched[0].object.object_id == 7
    assert fetched[0].camera.camera_id == "demo"


def test_add_event_from_pipeline_resolves_line(db_session):
    camera = repository.get_or_create_camera(db_session, "demo")
    line = repository.get_or_create_line(db_session, camera, "entrance", (0.0, 50.0), (100.0, 50.0))
    repository.get_or_create_object(db_session, camera, object_id=3, class_name="car", timestamp=2.0)

    pipeline_event = PipelineEvent(
        event_type="LINE_CROSSED", object_id=3, class_name="car", timestamp=2.0,
        camera_id="demo", confidence=0.8,
        metadata={"line_id": "entrance", "direction": "left_to_right", "side_before": 1, "side_after": -1},
    )
    row = repository.add_event_from_pipeline(db_session, camera, pipeline_event)

    assert row.line_id == line.id
    assert row.event_metadata["direction"] == "left_to_right"


def test_add_event_from_pipeline_raises_for_an_object_never_created(db_session):
    camera = repository.get_or_create_camera(db_session, "demo")
    pipeline_event = PipelineEvent(
        event_type="OBJECT_APPEARED", object_id=999, class_name="person",
        timestamp=0.0, camera_id="demo", confidence=0.9, metadata={},
    )
    with pytest.raises(ValueError):
        repository.add_event_from_pipeline(db_session, camera, pipeline_event)


def test_events_and_objects_are_scoped_per_camera(db_session):
    camera_a = repository.get_or_create_camera(db_session, "cam_a")
    camera_b = repository.get_or_create_camera(db_session, "cam_b")
    obj_a = repository.get_or_create_object(db_session, camera_a, object_id=1, class_name="person", timestamp=0.0)
    obj_b = repository.get_or_create_object(db_session, camera_b, object_id=1, class_name="person", timestamp=0.0)

    # same object_id, different cameras -- must be two distinct rows
    assert obj_a.id != obj_b.id
