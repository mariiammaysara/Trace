"""GET /analytics -- one bundled response combining several of Section 11's
query functions for the requested camera/time-range filter (see
AnalyticsSummary's docstring for why it's one endpoint, not eight)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from analytics import queries
from api.deps import get_db
from api.schemas import AnalyticsSummary

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsSummary)
def get_analytics(
    camera_id: Optional[str] = Query(default=None),
    start_time: Optional[float] = Query(default=None),
    end_time: Optional[float] = Query(default=None),
    session: Session = Depends(get_db),
) -> AnalyticsSummary:
    filters = dict(camera_id=camera_id, start_time=start_time, end_time=end_time)
    return AnalyticsSummary(
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        object_count=queries.object_count(session, **filters),
        line_crossing_count=queries.line_crossing_count(session, **filters),
        zone_violation_count=queries.zone_violation_count(session, **filters),
        average_dwell_time=queries.average_dwell_time(session, **filters),
        traffic_volume=queries.traffic_volume(session, **filters),
        event_frequency=queries.event_frequency(session, **filters),
        per_class_stats=queries.per_class_stats(session, **filters),
    )
