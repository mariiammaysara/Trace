"""POST /videos, GET /videos, GET /videos/{id}, GET /videos/{id}/stream.

The GET endpoints (list/detail/stream) were added in Phase 10.1 -- the
Live/Video dashboard view needs a real video source to play back, and
Section 10's original endpoint table only specified POST /videos (register a
file for offline processing), leaving no way to actually list or fetch one
back. Without this, "pull real video data from the API, no mock data" was
not actually satisfiable.

/stream serves the file bytes {id} resolves to via the database (Video.path,
populated only through POST /videos or persist_video.py) -- the client only
ever supplies an integer id, never a path, so this isn't a path-traversal
vector the way serving a client-supplied path string would be.
"""

from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import VideoCreate, VideoRead
from database import repository

router = APIRouter(tags=["videos"])


@router.get("/videos", response_model=List[VideoRead])
def list_videos(camera_id: Optional[str] = Query(default=None), session: Session = Depends(get_db)) -> List[VideoRead]:
    return [VideoRead.model_validate(video) for video in repository.list_videos(session, camera_id=camera_id)]


@router.get("/videos/{id}", response_model=VideoRead)
def get_video(id: int, session: Session = Depends(get_db)) -> VideoRead:  # noqa: A002
    video = repository.get_video(session, id)
    if video is None:
        raise HTTPException(status_code=404, detail=f"no video with id={id}")
    return VideoRead.model_validate(video)


@router.get("/videos/{id}/stream")
def stream_video(id: int, session: Session = Depends(get_db)) -> FileResponse:  # noqa: A002
    video = repository.get_video(session, id)
    if video is None:
        raise HTTPException(status_code=404, detail=f"no video with id={id}")
    if not os.path.isfile(video.path):
        raise HTTPException(status_code=404, detail=f"video id={id} has no file on disk at its registered path")
    return FileResponse(video.path, media_type="video/mp4")


@router.post("/videos", response_model=VideoRead, status_code=201)
def create_video(payload: VideoCreate, session: Session = Depends(get_db)) -> VideoRead:
    camera = get_camera_or_404(session, payload.camera_id)
    video = repository.create_video(session, camera, payload.path, payload.started_at)
    session.commit()
    return VideoRead.model_validate(video)
