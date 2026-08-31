"""Schema tests for src/database/models.py: tables and foreign-key
relationships match Section 9, and constraints are actually enforced by the
database, not just documented."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from database.models import Camera, Event, TrackedObject, TrackPoint


def test_create_all_creates_every_section_9_table(db_engine):
    inspector = inspect(db_engine)
    tables = set(inspector.get_table_names())
    assert {"cameras", "videos", "zones", "lines", "objects", "track_points", "events"} <= tables


def test_events_table_has_foreign_keys_to_objects_camera_zone_and_line(db_engine):
    inspector = inspect(db_engine)
    fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("events")}
    assert fk_targets == {"objects", "cameras", "zones", "lines"}


def test_objects_table_has_foreign_key_to_cameras(db_engine):
    inspector = inspect(db_engine)
    fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("objects")}
    assert fk_targets == {"cameras"}


def test_track_points_table_has_foreign_key_to_objects(db_engine):
    inspector = inspect(db_engine)
    fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("track_points")}
    assert fk_targets == {"objects"}


def test_camera_camera_id_unique_constraint_is_enforced(db_session):
    db_session.add(Camera(camera_id="dup"))
    db_session.flush()
    db_session.add(Camera(camera_id="dup"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_object_camera_object_id_unique_constraint_is_enforced(db_session):
    camera = Camera(camera_id="cam_a")
    db_session.add(camera)
    db_session.flush()

    db_session.add(TrackedObject(camera_id=camera.id, object_id=1, class_name="person", first_seen=0.0, last_seen=0.0))
    db_session.flush()

    db_session.add(TrackedObject(camera_id=camera.id, object_id=1, class_name="person", first_seen=1.0, last_seen=1.0))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_relationships_resolve_camera_to_objects_to_track_points_and_events(db_session):
    camera = Camera(camera_id="cam_b")
    db_session.add(camera)
    db_session.flush()

    obj = TrackedObject(camera_id=camera.id, object_id=1, class_name="car", first_seen=0.0, last_seen=1.0)
    db_session.add(obj)
    db_session.flush()

    db_session.add(TrackPoint(object_id=obj.id, frame_id=0, timestamp=0.0, x=1.0, y=2.0))
    db_session.add(
        Event(
            object_id=obj.id, camera_id=camera.id, event_type="OBJECT_APPEARED",
            class_name="car", timestamp=0.0, confidence=0.9, event_metadata={},
        )
    )
    db_session.flush()

    assert camera.objects == [obj]
    assert len(obj.track_points) == 1
    assert obj.track_points[0].x == 1.0
    assert len(obj.events) == 1
    assert obj.events[0].event_type == "OBJECT_APPEARED"
    assert obj.events[0].event_metadata == {}
