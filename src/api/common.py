"""Small helpers shared across routers -- kept out of the routers themselves
so each route handler stays a thin translation from HTTP to a repository
call, per Section 10's "route handlers should be thin" principle.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import repository
from database.models import Camera


def get_camera_or_404(session: Session, camera_id: str) -> Camera:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail=f"no camera with camera_id={camera_id!r}")
    return camera
