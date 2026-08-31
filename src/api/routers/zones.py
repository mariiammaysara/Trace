"""POST /zones."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import ZoneCreate, ZoneRead
from database import repository

router = APIRouter(tags=["zones"])


@router.post("/zones", response_model=ZoneRead, status_code=201)
def create_zone(payload: ZoneCreate, session: Session = Depends(get_db)) -> ZoneRead:
    camera = get_camera_or_404(session, payload.camera_id)
    zone = repository.get_or_create_zone(session, camera, payload.zone_id, payload.polygon)
    session.commit()
    return ZoneRead(id=zone.id, zone_id=zone.zone_id, polygon=zone.polygon)
