"""GET /objects/{id}/trajectory, GET /objects/{id}, GET /objects/{id}/events.

{id} is the object's internal database primary key (TrackedObject.id), not
the Tracker's own per-camera object_id (Section 3) -- that id is only unique
within one camera's tracker instance, so it can't identify a resource
globally the way a REST path parameter needs to. The internal PK is the
correct, unambiguous resource id -- and the same id every event's
EventRead.object_id already carries (Event.object_id is a FK to objects.id),
so a single id from any event or overlay click is enough to open Phase 19's
Object Profile view with no extra camera context required.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import EventRead, ObjectProfileRead, TrackPointRead, TrajectoryRead
from database import repository

router = APIRouter(tags=["objects"])


def _get_object_or_404(session: Session, id: int):  # noqa: A002 -- matches the REST resource id
    tracked_object = repository.get_object(session, id)
    if tracked_object is None:
        raise HTTPException(status_code=404, detail=f"no object with id={id}")
    return tracked_object


@router.get("/objects/{id}/trajectory", response_model=TrajectoryRead)
def get_object_trajectory(id: int, session: Session = Depends(get_db)) -> TrajectoryRead:  # noqa: A002
    tracked_object = _get_object_or_404(session, id)

    points = repository.get_track_points_for_object(session, tracked_object)
    return TrajectoryRead(
        object_id=tracked_object.id,
        camera_id=tracked_object.camera.camera_id,
        class_name=tracked_object.class_name,
        first_seen=tracked_object.first_seen,
        last_seen=tracked_object.last_seen,
        points=[
            TrackPointRead(
                frame_id=p.frame_id, timestamp=p.timestamp, x=p.x, y=p.y,
                x_min=p.x_min, y_min=p.y_min, x_max=p.x_max, y_max=p.y_max,
            )
            for p in points
        ],
    )


@router.get("/objects/{id}", response_model=ObjectProfileRead)
def get_object_profile(id: int, session: Session = Depends(get_db)) -> ObjectProfileRead:  # noqa: A002
    """Phase 19's Object Profile view -- class, lifetime, camera, and real
    aggregates (event count, total zone dwell time) over this one object's
    already-stored rows. No new tracking logic: total_dwell_seconds is a
    presentation-time sum over stored ZONE_ENTERED/ZONE_EXITED events (see
    repository.total_dwell_time_for_object), and event_count is a plain
    count of this object's stored events.
    """
    tracked_object = _get_object_or_404(session, id)
    events = repository.get_events_for_object(session, tracked_object)

    return ObjectProfileRead(
        id=tracked_object.id,
        object_id=tracked_object.object_id,
        class_name=tracked_object.class_name,
        first_seen=tracked_object.first_seen,
        last_seen=tracked_object.last_seen,
        camera_id=tracked_object.camera.camera_id,
        camera_name=tracked_object.camera.name,
        total_dwell_seconds=repository.total_dwell_time_for_object(session, tracked_object),
        event_count=len(events),
    )


@router.get("/objects/{id}/events", response_model=List[EventRead])
def get_object_events(id: int, session: Session = Depends(get_db)) -> List[EventRead]:  # noqa: A002
    """This object's own events, oldest first -- reused by the dashboard's
    Object Profile view via the same EventsView/EventBadge machinery Phase
    10.3/18 already built for a camera's event list, just scoped by object
    instead of by camera."""
    tracked_object = _get_object_or_404(session, id)
    events = repository.get_events_for_object(session, tracked_object)
    return [
        EventRead(
            id=event.id,
            object_id=event.object_id,
            event_type=event.event_type,
            class_name=event.class_name,
            timestamp=event.timestamp,
            confidence=event.confidence,
            metadata=event.event_metadata,
            zone_id=event.zone.zone_id if event.zone is not None else None,
            line_id=event.line.line_id if event.line is not None else None,
        )
        for event in events
    ]
