"""Repository layer: the only place in this codebase that talks to the
database directly via SQL/ORM. Pure data access, no business logic -- per
Section 10's layering, this exists so Phase 9's API can reuse it directly
instead of duplicating queries in route handlers.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Camera, Event, Line, TrackedObject, TrackPoint, Video, Zone
from events.event import Event as PipelineEvent


def get_or_create_camera(
    session: Session,
    camera_id: str,
    *,
    name: Optional[str] = None,
    location: Optional[str] = None,
    calibration_reference: Optional[str] = None,
) -> Camera:
    camera = session.execute(select(Camera).where(Camera.camera_id == camera_id)).scalar_one_or_none()
    if camera is None:
        camera = Camera(camera_id=camera_id, name=name, location=location, calibration_reference=calibration_reference)
        session.add(camera)
        session.flush()
    return camera


def create_video(session: Session, camera: Camera, path: str, started_at: Optional[dt.datetime] = None) -> Video:
    video = Video(camera_id=camera.id, path=path, started_at=started_at)
    session.add(video)
    session.flush()
    return video


def get_or_create_zone(session: Session, camera: Camera, zone_id: str, polygon: Sequence[Tuple[float, float]]) -> Zone:
    zone = session.execute(
        select(Zone).where(Zone.camera_id == camera.id, Zone.zone_id == zone_id)
    ).scalar_one_or_none()
    if zone is None:
        zone = Zone(camera_id=camera.id, zone_id=zone_id, polygon=[list(p) for p in polygon])
        session.add(zone)
        session.flush()
    return zone


def get_or_create_line(
    session: Session, camera: Camera, line_id: str, start: Tuple[float, float], end: Tuple[float, float]
) -> Line:
    line = session.execute(
        select(Line).where(Line.camera_id == camera.id, Line.line_id == line_id)
    ).scalar_one_or_none()
    if line is None:
        line = Line(camera_id=camera.id, line_id=line_id, start_x=start[0], start_y=start[1], end_x=end[0], end_y=end[1])
        session.add(line)
        session.flush()
    return line


def get_or_create_object(
    session: Session, camera: Camera, object_id: int, class_name: str, timestamp: float
) -> TrackedObject:
    """Find-or-create the row for (camera, object_id), updating last_seen and
    class_name on every call.

    Known limitation (documented, not hidden): object_id is the Tracker's own
    per-camera id (Section 3), which restarts from 1 on every new ByteTracker
    instance. Within one continuous pipeline run this is a stable key; across
    a process restart, a reused object_id=1 will be merged into the same
    existing row instead of starting a fresh one. See TrackedObject's
    docstring in models.py.
    """
    obj = session.execute(
        select(TrackedObject).where(TrackedObject.camera_id == camera.id, TrackedObject.object_id == object_id)
    ).scalar_one_or_none()
    if obj is None:
        obj = TrackedObject(
            camera_id=camera.id, object_id=object_id, class_name=class_name,
            first_seen=timestamp, last_seen=timestamp,
        )
        session.add(obj)
        session.flush()
    else:
        obj.last_seen = max(obj.last_seen, timestamp)
        obj.class_name = class_name
    return obj


def add_track_point(
    session: Session, tracked_object: TrackedObject, frame_id: int, timestamp: float, x: float, y: float
) -> TrackPoint:
    point = TrackPoint(object_id=tracked_object.id, frame_id=frame_id, timestamp=timestamp, x=x, y=y)
    session.add(point)
    return point


def add_event(
    session: Session,
    camera: Camera,
    tracked_object: TrackedObject,
    event: PipelineEvent,
    *,
    zone: Optional[Zone] = None,
    line: Optional[Line] = None,
) -> Event:
    row = Event(
        object_id=tracked_object.id,
        camera_id=camera.id,
        zone_id=zone.id if zone is not None else None,
        line_id=line.id if line is not None else None,
        event_type=event.event_type,
        class_name=event.class_name,
        timestamp=event.timestamp,
        confidence=event.confidence,
        event_metadata=dict(event.metadata),
    )
    session.add(row)
    return row


def add_event_from_pipeline(session: Session, camera: Camera, event: PipelineEvent) -> Event:
    """Persist one events.event.Event, resolving its zone/line foreign keys
    automatically from event.metadata (LINE_CROSSED/ZONE_ENTERED/ZONE_EXITED
    carry "line_id"/"zone_id" there -- Phase 7's schema).

    The camera and the tracked object it belongs to must already exist --
    call get_or_create_camera()/get_or_create_object() for this frame's
    tracks before persisting its events, since object creation needs the
    current Track (class_name, timestamp), not just the Event.
    """
    tracked_object = session.execute(
        select(TrackedObject).where(TrackedObject.camera_id == camera.id, TrackedObject.object_id == event.object_id)
    ).scalar_one_or_none()
    if tracked_object is None:
        raise ValueError(
            f"no TrackedObject row for camera_id={camera.camera_id!r} object_id={event.object_id} -- "
            "call get_or_create_object() for this frame's tracks before persisting its events"
        )

    zone = None
    zone_id = event.metadata.get("zone_id")
    if zone_id is not None:
        zone = session.execute(
            select(Zone).where(Zone.camera_id == camera.id, Zone.zone_id == zone_id)
        ).scalar_one_or_none()

    line = None
    line_id = event.metadata.get("line_id")
    if line_id is not None:
        line = session.execute(
            select(Line).where(Line.camera_id == camera.id, Line.line_id == line_id)
        ).scalar_one_or_none()

    return add_event(session, camera, tracked_object, event, zone=zone, line=line)


def get_events_for_object(session: Session, tracked_object: TrackedObject) -> List[Event]:
    return list(
        session.execute(select(Event).where(Event.object_id == tracked_object.id).order_by(Event.timestamp)).scalars()
    )


def get_track_points_for_object(session: Session, tracked_object: TrackedObject) -> List[TrackPoint]:
    return list(
        session.execute(
            select(TrackPoint).where(TrackPoint.object_id == tracked_object.id).order_by(TrackPoint.timestamp)
        ).scalars()
    )
