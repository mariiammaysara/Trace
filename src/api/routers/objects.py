"""GET /objects/{id}/trajectory.

{id} is the object's internal database primary key (TrackedObject.id), not
the Tracker's own per-camera object_id (Section 3) -- that id is only unique
within one camera's tracker instance, so it can't identify a resource
globally the way a REST path parameter needs to. The internal PK is the
correct, unambiguous resource id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import TrackPointRead, TrajectoryRead
from database import repository

router = APIRouter(tags=["objects"])


@router.get("/objects/{id}/trajectory", response_model=TrajectoryRead)
def get_object_trajectory(id: int, session: Session = Depends(get_db)) -> TrajectoryRead:  # noqa: A002
    tracked_object = repository.get_object(session, id)
    if tracked_object is None:
        raise HTTPException(status_code=404, detail=f"no object with id={id}")

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
