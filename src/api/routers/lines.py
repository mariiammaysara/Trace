"""POST /lines."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import LineCreate, LineRead
from database import repository

router = APIRouter(tags=["lines"])


@router.post("/lines", response_model=LineRead, status_code=201)
def create_line(payload: LineCreate, session: Session = Depends(get_db)) -> LineRead:
    camera = get_camera_or_404(session, payload.camera_id)
    line = repository.get_or_create_line(session, camera, payload.line_id, payload.start, payload.end)
    session.commit()
    return LineRead(id=line.id, line_id=line.line_id, start=(line.start_x, line.start_y), end=(line.end_x, line.end_y))
