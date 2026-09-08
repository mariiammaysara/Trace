"""Repository layer: the only place in this codebase that talks to the
database directly via SQL/ORM. Pure data access, no business logic -- per
Section 10's layering, this exists so Phase 9's API can reuse it directly
instead of duplicating queries in route handlers.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Alert, Camera, Event, Line, PendingAction, TrackedObject, TrackPoint, Video, Zone
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


def create_pending_video(session: Session, camera: Camera, path: str, total_frames: Optional[int]) -> Video:
    """The upload flow's entry point (POST /videos/upload) -- status="pending"
    so scripts/upload_worker.py's poll loop picks it up; total_frames is real,
    read from the uploaded file itself via cv2.VideoCapture before this is
    called, never estimated."""
    video = Video(camera_id=camera.id, path=path, status="pending", total_frames=total_frames, frames_processed=0)
    session.add(video)
    session.flush()
    return video


def claim_next_pending_video(session: Session) -> Optional[Video]:
    """Atomically claims the oldest still-pending video for processing --
    SELECT ... FOR UPDATE SKIP LOCKED so two worker processes (there's only
    ever one by design, but this makes that an actual guarantee rather than
    an assumption) can never both claim the same row. Commits immediately so
    the "processing" status is visible to GET /videos/{id}/status right away,
    not just when the whole run finishes."""
    video = session.execute(
        select(Video).where(Video.status == "pending").order_by(Video.id).limit(1).with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if video is not None:
        video.status = "processing"
        video.processing_started_at = dt.datetime.utcnow()
        session.commit()
    return video


def update_video_progress(session: Session, video: Video, frames_processed: int, current_fps: Optional[float]) -> None:
    video.frames_processed = frames_processed
    video.current_fps = current_fps
    session.commit()


def mark_video_done(session: Session, video: Video) -> None:
    video.status = "done"
    session.commit()


def mark_video_failed(session: Session, video: Video, error_message: str) -> None:
    video.status = "failed"
    video.error_message = error_message
    session.commit()


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
    session: Session,
    tracked_object: TrackedObject,
    frame_id: int,
    timestamp: float,
    x: float,
    y: float,
    *,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> TrackPoint:
    """bbox, if given, is xyxy (x_min, y_min, x_max, y_max) -- Section 1.3/2
    convention, same as Detection.bbox/Track.bbox. Optional so existing
    callers that only ever needed the centroid keep working unchanged."""
    x_min, y_min, x_max, y_max = bbox if bbox is not None else (None, None, None, None)
    point = TrackPoint(
        object_id=tracked_object.id, frame_id=frame_id, timestamp=timestamp, x=x, y=y,
        x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max,
    )
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

    row = add_event(session, camera, tracked_object, event, zone=zone, line=line)

    # Section 13's real-time alerting: synchronous, deterministic, no LLM/
    # agent involved -- matches Section 7's event engine being pure/
    # rule-based. flush() first so row.id exists for the Alert's event_id FK.
    from alerts.rules import should_alert

    if should_alert(event.event_type):
        session.flush()
        create_alert(
            session,
            camera,
            event_type=event.event_type,
            message=f"{event.event_type} detected for object {event.object_id} on camera {camera.camera_id!r}",
            channel="dashboard",
            event=row,
        )

    return row


def get_events_for_object(session: Session, tracked_object: TrackedObject) -> List[Event]:
    return list(
        session.execute(select(Event).where(Event.object_id == tracked_object.id).order_by(Event.timestamp)).scalars()
    )


def total_dwell_time_for_object(session: Session, tracked_object: TrackedObject) -> float:
    """Cumulative zone dwell time for one object -- Section 4/Phase 6's
    dwell definition (sum of entry->exit visit durations, across every
    zone visit), computed here by pairing the object's own real, already
    -stored ZONE_ENTERED/ZONE_EXITED events in timestamp order. This is
    the exact same open/close pairing trajectories.dwell.DwellTracker.update()
    performs live, re-derived from persisted events instead of a live
    per-frame stream -- no new zone-membership or tracking logic, purely a
    presentation-time sum over data the pipeline already wrote.

    A visit still open when tracking ended (a ZONE_ENTERED with no matching
    ZONE_EXITED) counts through the object's last_seen, mirroring
    DwellTracker.total_dwell_time(include_open=True)'s live "duration so
    far" -- last_seen is the last real moment this object is known to
    exist, the offline equivalent of "now".
    """
    events = get_events_for_object(session, tracked_object)
    zone_events = [e for e in events if e.event_type in ("ZONE_ENTERED", "ZONE_EXITED") and e.zone_id is not None]

    open_entries: Dict[int, float] = {}
    total = 0.0
    for event in zone_events:
        if event.event_type == "ZONE_ENTERED":
            open_entries.setdefault(event.zone_id, event.timestamp)
        elif event.event_type == "ZONE_EXITED" and event.zone_id in open_entries:
            total += event.timestamp - open_entries.pop(event.zone_id)

    for entry_timestamp in open_entries.values():
        total += max(tracked_object.last_seen - entry_timestamp, 0.0)

    return total


def get_track_points_for_object(session: Session, tracked_object: TrackedObject) -> List[TrackPoint]:
    return list(
        session.execute(
            select(TrackPoint).where(TrackPoint.object_id == tracked_object.id).order_by(TrackPoint.timestamp)
        ).scalars()
    )


# --- read-only lookups added in Phase 9 for the API layer, so route handlers
# never need a raw ORM query of their own (Section 10: no raw SQL in routes) ---


def get_camera(session: Session, camera_id: str) -> Optional[Camera]:
    return session.execute(select(Camera).where(Camera.camera_id == camera_id)).scalar_one_or_none()


def list_cameras(session: Session) -> List[Camera]:
    return list(session.execute(select(Camera).order_by(Camera.camera_id)).scalars())


def list_zones_for_camera(session: Session, camera: Camera) -> List[Zone]:
    """Phase 10.1 needs this to overlay configured zones on the Live/Video
    view -- Phase 9's original endpoint table only had POST /zones, no way
    to list what's configured for a camera."""
    return list(session.execute(select(Zone).where(Zone.camera_id == camera.id).order_by(Zone.zone_id)).scalars())


def list_lines_for_camera(session: Session, camera: Camera) -> List[Line]:
    """Same gap as list_zones_for_camera, for lines."""
    return list(session.execute(select(Line).where(Line.camera_id == camera.id).order_by(Line.line_id)).scalars())


def list_objects_for_camera(session: Session, camera: Camera) -> List[TrackedObject]:
    """Every TrackedObject seen on one camera -- Phase 10.1 needs this to know
    which objects exist to overlay on a video; Phase 9's original endpoint
    table had no per-camera object listing, only single-object lookup by id."""
    return list(
        session.execute(
            select(TrackedObject).where(TrackedObject.camera_id == camera.id).order_by(TrackedObject.first_seen)
        ).scalars()
    )


def list_videos(session: Session, *, camera_id: Optional[str] = None) -> List[Video]:
    query = select(Video)
    if camera_id is not None:
        query = query.join(Video.camera).where(Camera.camera_id == camera_id)
    return list(session.execute(query.order_by(Video.id)).scalars())


def get_video(session: Session, id: int) -> Optional[Video]:  # noqa: A002 -- matches the REST resource id
    return session.get(Video, id)


def get_object(session: Session, id: int) -> Optional[TrackedObject]:  # noqa: A002 -- matches the REST resource id
    return session.get(TrackedObject, id)


def list_events_for_camera(
    session: Session,
    camera: Camera,
    *,
    event_type: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> List[Event]:
    query = select(Event).where(Event.camera_id == camera.id)
    if event_type is not None:
        query = query.where(Event.event_type == event_type)
    if start_time is not None:
        query = query.where(Event.timestamp >= start_time)
    if end_time is not None:
        query = query.where(Event.timestamp <= end_time)
    return list(session.execute(query.order_by(Event.timestamp)).scalars())


# --- read-only lookups added in Phase 11 for the Vision Agent's tools
# (src/agent/tools.py) -- same "no raw ORM query outside the repository
# layer" rule Phase 9's API additions followed. ---


def get_zone(session: Session, camera: Camera, zone_id: str) -> Optional[Zone]:
    return session.execute(select(Zone).where(Zone.camera_id == camera.id, Zone.zone_id == zone_id)).scalar_one_or_none()


def get_line(session: Session, camera: Camera, line_id: str) -> Optional[Line]:
    return session.execute(select(Line).where(Line.camera_id == camera.id, Line.line_id == line_id)).scalar_one_or_none()


def list_events_for_zone(session: Session, zone: Zone) -> List[Event]:
    return list(session.execute(select(Event).where(Event.zone_id == zone.id).order_by(Event.timestamp)).scalars())


def list_events_for_line(session: Session, line: Line) -> List[Event]:
    return list(session.execute(select(Event).where(Event.line_id == line.id).order_by(Event.timestamp)).scalars())


def get_event(session: Session, id: int) -> Optional[Event]:  # noqa: A002 -- matches the REST resource id
    return session.get(Event, id)


# --- Section 13: alerts + the agent's propose/approve gate (Phase 12) ---


def create_alert(
    session: Session,
    camera: Camera,
    *,
    event_type: str,
    message: str,
    channel: str = "dashboard",
    event: Optional[Event] = None,
) -> Alert:
    alert = Alert(
        camera_id=camera.id,
        event_id=event.id if event is not None else None,
        event_type=event_type,
        message=message,
        channel=channel,
    )
    session.add(alert)
    session.flush()
    return alert


def list_alerts_for_camera(session: Session, camera: Camera) -> List[Alert]:
    return list(session.execute(select(Alert).where(Alert.camera_id == camera.id).order_by(Alert.created_at)).scalars())


def get_alert(session: Session, id: int) -> Optional[Alert]:  # noqa: A002 -- matches the REST resource id
    return session.get(Alert, id)


def create_pending_action(session: Session, action_type: str, parameters: dict, summary: str) -> PendingAction:
    action = PendingAction(action_type=action_type, parameters=parameters, summary=summary, status="pending")
    session.add(action)
    session.flush()
    return action


def get_pending_action(session: Session, id: int) -> Optional[PendingAction]:  # noqa: A002 -- matches the REST resource id
    return session.get(PendingAction, id)
