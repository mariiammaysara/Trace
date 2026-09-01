"""POST /alerts -- Section 13. A direct alert creation, bypassing the
agent's propose/approve gate (see AlertCreate's docstring): a real human/
system POSTing here is already the "real confirmation" that gate exists to
require for the LLM's own autonomous tool-calling."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import AlertCreate, AlertRead
from database import repository

router = APIRouter(tags=["alerts"])


@router.post("/alerts", response_model=AlertRead, status_code=201)
def create_alert(payload: AlertCreate, session: Session = Depends(get_db)) -> AlertRead:
    camera = get_camera_or_404(session, payload.camera_id)
    alert = repository.create_alert(
        session, camera, event_type=payload.event_type, message=payload.message, channel=payload.channel
    )
    session.commit()
    return AlertRead(
        id=alert.id,
        camera_id=payload.camera_id,
        event_id=alert.event_id,
        event_type=alert.event_type,
        message=alert.message,
        channel=alert.channel,
        created_at=alert.created_at,
    )
