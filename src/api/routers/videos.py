"""POST /videos."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import VideoCreate, VideoRead
from database import repository

router = APIRouter(tags=["videos"])


@router.post("/videos", response_model=VideoRead, status_code=201)
def create_video(payload: VideoCreate, session: Session = Depends(get_db)) -> VideoRead:
    camera = get_camera_or_404(session, payload.camera_id)
    video = repository.create_video(session, camera, payload.path, payload.started_at)
    session.commit()
    return VideoRead.model_validate(video)
