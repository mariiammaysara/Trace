"""POST /cameras, GET /cameras/{camera_id}/events."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import CameraCreate, CameraRead, EventRead
from database import repository

router = APIRouter(tags=["cameras"])


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
