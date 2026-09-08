"""POST /videos, GET /videos, GET /videos/{id}, GET /videos/{id}/stream,
POST /videos/upload, GET /videos/{id}/status.

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

/upload and /status are the upload feature's entry/exit points: /upload
saves the file and creates a "pending" Video row for scripts/upload_worker.py
to pick up (it does NOT run the pipeline itself -- see src/pipeline.py's
module docstring for why that split exists); /status reports real,
stored-column-derived progress for the frontend to poll, never a simulated
number.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List, Optional

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.common import get_camera_or_404
from api.deps import get_db
from api.schemas import VideoCreate, VideoRead, VideoStatusRead
from database import repository

router = APIRouter(tags=["videos"])

# 200MB -- generous for a portfolio-scale deployment's CPU pipeline (a video
# much larger than this would take a very long time at 5-16 FPS anyway)
# while still bounding disk usage and upload time. Overridable via env for
# a deployment that wants a different cap, and by tests that want a tiny
# cap to exercise the rejection path without writing 200MB to disk.
ALLOWED_UPLOAD_EXTENSIONS = {".mp4", ".mov"}
UPLOAD_CHUNK_BYTES = 1024 * 1024

# Same reasoning as src/pipeline.py's process_video progress_callback: an
# FPS/ETA estimate from a handful of frames is noise dressed up as a number,
# not a real estimate -- withheld until this many frames have actually been
# measured.
MIN_FRAMES_FOR_ETA_ESTIMATE = 20


def _max_upload_bytes() -> int:
    return int(os.environ.get("TRACE_UPLOAD_MAX_BYTES", 200 * 1024 * 1024))


def _upload_dir() -> Path:
    return Path(os.environ.get("TRACE_UPLOAD_DIR", "data/uploads"))


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


@router.post("/videos/upload", response_model=VideoRead, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    camera_id: str = Form(..., min_length=1),
    camera_name: Optional[str] = Form(default=None),
    session: Session = Depends(get_db),
) -> VideoRead:
    """Accepts a video file + camera_id, saves it to disk, and registers a
    "pending" Video row -- scripts/upload_worker.py's poll loop is what
    actually runs the pipeline over it (Step 1's chosen design: this request
    returns as soon as the file is validated and saved, not after minutes of
    CPU-bound inference). camera_id is created if it doesn't already exist
    (repository.get_or_create_camera), attached to if it does.
    """
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported video format {extension or '(none)'!r} -- allowed: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}",
        )

    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = upload_dir / f"{uuid.uuid4().hex}{extension}"
    max_bytes = _max_upload_bytes()

    size = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"file exceeds the {max_bytes // (1024 * 1024)}MB upload limit",
                    )
                out.write(chunk)
    except HTTPException:
        dest_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    capture = cv2.VideoCapture(str(dest_path))
    try:
        opened = capture.isOpened()
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if opened else 0
    finally:
        capture.release()
    if not opened or total_frames <= 0:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="could not read this file as a video -- it may be corrupt or use an unsupported codec",
        )

    camera = repository.get_or_create_camera(session, camera_id, name=camera_name)
    video = repository.create_pending_video(session, camera, str(dest_path), total_frames)
    session.commit()
    return VideoRead.model_validate(video)


@router.get("/videos/{id}/status", response_model=VideoStatusRead)
def get_video_status(id: int, session: Session = Depends(get_db)) -> VideoStatusRead:  # noqa: A002
    video = repository.get_video(session, id)
    if video is None:
        raise HTTPException(status_code=404, detail=f"no video with id={id}")

    percent = None
    if video.total_frames:
        percent = min(100.0, 100.0 * video.frames_processed / video.total_frames)

    eta_seconds = None
    if (
        video.status == "processing"
        and video.current_fps
        and video.total_frames is not None
        and video.frames_processed >= MIN_FRAMES_FOR_ETA_ESTIMATE
    ):
        eta_seconds = max(0.0, video.total_frames - video.frames_processed) / video.current_fps

    return VideoStatusRead(
        id=video.id,
        status=video.status,
        total_frames=video.total_frames,
        frames_processed=video.frames_processed,
        percent=percent,
        current_fps=video.current_fps,
        eta_seconds=eta_seconds,
        error_message=video.error_message,
    )
