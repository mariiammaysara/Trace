"""POST /cameras, GET /cameras, GET /cameras/{camera_id}/objects, GET /cameras/{camera_id}/events."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import AlertRead, CameraCreate, CameraRead, EventRead, LineRead, TrackedObjectRead, ZoneRead
from database import repository

router = APIRouter(tags=["cameras"])


@router.get("/cameras", response_model=List[CameraRead])
def list_cameras(session: Session = Depends(get_db)) -> List[CameraRead]:
    return [CameraRead.model_validate(camera) for camera in repository.list_cameras(session)]


@router.post("/cameras", response_model=CameraRead, status_code=201)
def create_camera(payload: CameraCreate, session: Session = Depends(get_db)) -> CameraRead:
    """Idempotent by camera_id: posting the same camera_id twice returns/updates
    the same row rather than erroring, matching repository.get_or_create_camera."""
    camera = repository.get_or_create_camera(
        session, payload.camera_id, name=payload.name, location=payload.location,
        calibration_reference=payload.calibration_reference,
    )
    session.commit()
    return CameraRead.model_validate(camera)


@router.get("/cameras/{camera_id}/zones", response_model=List[ZoneRead])
def list_camera_zones(camera_id: str, session: Session = Depends(get_db)) -> List[ZoneRead]:
    camera = get_camera_or_404(session, camera_id)
    return [ZoneRead(id=z.id, zone_id=z.zone_id, polygon=z.polygon) for z in repository.list_zones_for_camera(session, camera)]


@router.get("/cameras/{camera_id}/lines", response_model=List[LineRead])
def list_camera_lines(camera_id: str, session: Session = Depends(get_db)) -> List[LineRead]:
    camera = get_camera_or_404(session, camera_id)
    return [
        LineRead(id=line.id, line_id=line.line_id, start=(line.start_x, line.start_y), end=(line.end_x, line.end_y))
        for line in repository.list_lines_for_camera(session, camera)
    ]


@router.get("/cameras/{camera_id}/objects", response_model=List[TrackedObjectRead])
def list_camera_objects(camera_id: str, session: Session = Depends(get_db)) -> List[TrackedObjectRead]:
    camera = get_camera_or_404(session, camera_id)
    return [TrackedObjectRead.model_validate(obj) for obj in repository.list_objects_for_camera(session, camera)]


@router.get("/cameras/{camera_id}/events", response_model=List[EventRead])
def list_camera_events(
    camera_id: str,
    event_type: Optional[str] = Query(default=None),
    start_time: Optional[float] = Query(default=None),
    end_time: Optional[float] = Query(default=None),
    session: Session = Depends(get_db),
) -> List[EventRead]:
    camera = get_camera_or_404(session, camera_id)
    events = repository.list_events_for_camera(
        session, camera, event_type=event_type, start_time=start_time, end_time=end_time
    )
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


@router.get("/cameras/{camera_id}/alerts", response_model=List[AlertRead])
def list_camera_alerts(camera_id: str, session: Session = Depends(get_db)) -> List[AlertRead]:
    """Section 13's "dashboard/API" delivery channel: an alert is "delivered"
    by existing here, queryable -- this is what a dashboard would poll."""
    camera = get_camera_or_404(session, camera_id)
    return [
        AlertRead(
            id=alert.id,
            camera_id=camera_id,
            event_id=alert.event_id,
            event_type=alert.event_type,
            message=alert.message,
            channel=alert.channel,
            created_at=alert.created_at,
        )
        for alert in repository.list_alerts_for_camera(session, camera)
    ]
