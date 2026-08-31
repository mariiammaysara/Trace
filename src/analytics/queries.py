"""Section 11 analytics: real SQL queries against the database persisted by
Phase 8's repository layer. Every number here comes from an actual query --
nothing hardcoded or mocked. All functions take a SQLAlchemy Session as the
first argument and filter with plain keyword arguments (camera_id is the
human-readable string id, e.g. "demo" -- resolved to the internal integer PK
internally, never exposed to callers).
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Camera, Event, TrackedObject


def _camera_pk(session: Session, camera_id: Optional[str]) -> Optional[int]:
    """Resolve a human-readable camera_id string to its internal integer PK.
    Returns None if camera_id is None (no filter wanted) or -1 if a specific
    camera_id was given but doesn't exist (so filters correctly match
    nothing instead of raising or silently ignoring the filter)."""
    if camera_id is None:
        return None
    pk = session.execute(select(Camera.id).where(Camera.camera_id == camera_id)).scalar_one_or_none()
    return pk if pk is not None else -1


def object_count(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    class_name: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> int:
    """Count of distinct tracked objects (rows in `objects`), optionally
    filtered by camera, class, and a [start_time, end_time] window on
    first_seen."""
    query = select(func.count(TrackedObject.id))
    camera_pk = _camera_pk(session, camera_id)
    if camera_pk is not None:
        query = query.where(TrackedObject.camera_id == camera_pk)
    if class_name is not None:
        query = query.where(TrackedObject.class_name == class_name)
    if start_time is not None:
        query = query.where(TrackedObject.first_seen >= start_time)
    if end_time is not None:
        query = query.where(TrackedObject.first_seen <= end_time)
    return session.execute(query).scalar_one()


def line_crossing_count(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    line_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> int:
    """Raw count of LINE_CROSSED events -- every crossing counts, including
    the same object crossing more than once. See traffic_volume() for the
    distinct-objects variant."""
    return _event_count(session, event_type="LINE_CROSSED", camera_id=camera_id, start_time=start_time, end_time=end_time, line_id=line_id)


def zone_violation_count(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> int:
    """Count of ZONE_ENTERED events. "Violation" here means entering any
    configured/tracked zone -- the domain framing Section 0 uses
    (ZONE_ENTERED on a restricted zone), not a distinct event_type of its
    own; TRACE doesn't currently distinguish "restricted" zones from any
    other configured zone, so every ZONE_ENTERED counts."""
    return _event_count(session, event_type="ZONE_ENTERED", camera_id=camera_id, start_time=start_time, end_time=end_time, zone_id=zone_id)


def average_dwell_time(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> float:
    """Average duration of completed zone visits, computed directly from
    stored ZONE_ENTERED/ZONE_EXITED event pairs (per object, per zone,
    matched in timestamp order) -- not from LOITERING events, since those
    only fire once a threshold is crossed and wouldn't cover every visit.
    Returns 0.0 if there are no completed visits in range (never raises a
    division error)."""
    camera_pk = _camera_pk(session, camera_id)

    query = select(Event).where(Event.event_type.in_(["ZONE_ENTERED", "ZONE_EXITED"]))
    if camera_pk is not None:
        query = query.where(Event.camera_id == camera_pk)
    if zone_id is not None:
        query = query.join(Event.zone).where(Event.zone.has(zone_id=zone_id))
    if start_time is not None:
        query = query.where(Event.timestamp >= start_time)
    if end_time is not None:
        query = query.where(Event.timestamp <= end_time)
    query = query.order_by(Event.object_id, Event.zone_id, Event.timestamp)

    rows = session.execute(query).scalars().all()

    open_entries: Dict[Tuple[int, Optional[int]], float] = {}
    durations: List[float] = []
    for row in rows:
        key = (row.object_id, row.zone_id)
        if row.event_type == "ZONE_ENTERED":
            open_entries[key] = row.timestamp
        elif row.event_type == "ZONE_EXITED" and key in open_entries:
            durations.append(row.timestamp - open_entries.pop(key))

    if not durations:
        return 0.0
    return sum(durations) / len(durations)


def traffic_volume(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    line_id: Optional[str] = None,
    class_name: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> int:
    """Count of *distinct objects* that produced at least one LINE_CROSSED
    event -- the classic "how many vehicles/pedestrians passed" traffic
    metric, as opposed to line_crossing_count()'s raw event count (which
    double-counts an object crossing more than once)."""
    camera_pk = _camera_pk(session, camera_id)
    query = select(func.count(func.distinct(Event.object_id))).where(Event.event_type == "LINE_CROSSED")
    if camera_pk is not None:
        query = query.where(Event.camera_id == camera_pk)
    if line_id is not None:
        query = query.join(Event.line).where(Event.line.has(line_id=line_id))
    if class_name is not None:
        query = query.where(Event.class_name == class_name)
    if start_time is not None:
        query = query.where(Event.timestamp >= start_time)
    if end_time is not None:
        query = query.where(Event.timestamp <= end_time)
    return session.execute(query).scalar_one()


def busiest_hours(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    event_type: Optional[str] = None,
    top_n: int = 5,
) -> List[Tuple[dt.datetime, int]]:
    """Hour buckets with the most events, busiest first.

    IMPORTANT, documented limitation: this treats Event.timestamp as Unix
    epoch seconds (UTC). That's exactly correct for live-camera-sourced
    events (Phase 1: FrameSource uses time.time() for camera sources), but
    file-based sources use *video-relative* timestamps (Phase 1: seconds
    from the file's own position) -- for those, the "hour" this buckets by
    is not a real calendar hour, just an artifact of when the file's own
    clock reads that value. There's no anchor stored yet to convert a
    file-relative timestamp to wall-clock time (Video.started_at exists in
    the schema but isn't wired to this function) -- treat this function's
    output as meaningful only for live-camera data until that's built.
    """
    camera_pk = _camera_pk(session, camera_id)
    query = select(Event.timestamp)
    if camera_pk is not None:
        query = query.where(Event.camera_id == camera_pk)
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    timestamps = session.execute(query).scalars().all()
    counts: Dict[dt.datetime, int] = defaultdict(int)
    for ts in timestamps:
        hour_bucket = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
        counts[hour_bucket] += 1

    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top_n]


def event_frequency(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Dict[str, int]:
    """Event count grouped by event_type."""
    camera_pk = _camera_pk(session, camera_id)
    query = select(Event.event_type, func.count(Event.id)).group_by(Event.event_type)
    if camera_pk is not None:
        query = query.where(Event.camera_id == camera_pk)
    if start_time is not None:
        query = query.where(Event.timestamp >= start_time)
    if end_time is not None:
        query = query.where(Event.timestamp <= end_time)
    return {event_type: count for event_type, count in session.execute(query).all()}


def per_class_stats(
    session: Session,
    *,
    camera_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Dict[str, Dict[str, int]]:
    """Per detected class: distinct object count (from `objects`, filtered by
    first_seen) and event count (from `events`, filtered by timestamp),
    merged into one dict keyed by class_name."""
    camera_pk = _camera_pk(session, camera_id)

    object_query = select(TrackedObject.class_name, func.count(TrackedObject.id)).group_by(TrackedObject.class_name)
    if camera_pk is not None:
        object_query = object_query.where(TrackedObject.camera_id == camera_pk)
    if start_time is not None:
        object_query = object_query.where(TrackedObject.first_seen >= start_time)
    if end_time is not None:
        object_query = object_query.where(TrackedObject.first_seen <= end_time)
    object_counts = dict(session.execute(object_query).all())

    event_query = select(Event.class_name, func.count(Event.id)).group_by(Event.class_name)
    if camera_pk is not None:
        event_query = event_query.where(Event.camera_id == camera_pk)
    if start_time is not None:
        event_query = event_query.where(Event.timestamp >= start_time)
    if end_time is not None:
        event_query = event_query.where(Event.timestamp <= end_time)
    event_counts = dict(session.execute(event_query).all())

    stats: Dict[str, Dict[str, int]] = {}
    for class_name in set(object_counts) | set(event_counts):
        stats[class_name] = {
            "object_count": object_counts.get(class_name, 0),
            "event_count": event_counts.get(class_name, 0),
        }
    return stats


def _event_count(
    session: Session,
    *,
    event_type: str,
    camera_id: Optional[str],
    start_time: Optional[float],
    end_time: Optional[float],
    zone_id: Optional[str] = None,
    line_id: Optional[str] = None,
) -> int:
    camera_pk = _camera_pk(session, camera_id)
    query = select(func.count(Event.id)).where(Event.event_type == event_type)
    if camera_pk is not None:
        query = query.where(Event.camera_id == camera_pk)
    if zone_id is not None:
        query = query.select_from(Event).join(Event.zone).where(Event.zone.has(zone_id=zone_id))
    if line_id is not None:
        query = query.select_from(Event).join(Event.line).where(Event.line.has(line_id=line_id))
    if start_time is not None:
        query = query.where(Event.timestamp >= start_time)
    if end_time is not None:
        query = query.where(Event.timestamp <= end_time)
    return session.execute(query).scalar_one()
