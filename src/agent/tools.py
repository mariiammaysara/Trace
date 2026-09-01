"""The Vision Agent's tools (Section 12): every function here calls the real
Phase 8 repository/Section 11 analytics layer and returns exactly what the
database has -- never an invented or estimated value the pipeline didn't
already compute. This is what makes the agent's answers "grounded": the LLM
never sees raw SQL or the database directly, only these JSON-serializable
results.

Each tool returns a plain dict. An unresolvable id (unknown camera_id,
zone_id, line_id, object_id, or event id) returns `{"error": "..."}` rather
than raising, so a bad tool call becomes something the LLM can see and
recover from (e.g. by asking a clarifying question or trying another id),
not a crash.

`estimated_speed` values that pass through from event metadata keep that
exact name (Section 6's naming rule: never bare "speed") and are in
meters/second, since that's what the calibrated homography in
configs/cameras/*.json produces -- SYSTEM_PROMPT (prompts.py) tells the
model this explicitly so it converts units correctly when a question uses
km/h or mph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from agent.actions import (
    propose_configure_line,
    propose_configure_zone,
    propose_create_alert,
    propose_generate_report,
    propose_send_notification,
)
from analytics import queries as analytics_queries
from database import repository
from database.models import Event


def _event_to_dict(event: Event) -> Dict[str, Any]:
    return {
        "id": event.id,
        "object_id": event.object_id,
        "camera_id": event.camera.camera_id,
        "event_type": event.event_type,
        "class_name": event.class_name,
        "timestamp": event.timestamp,
        "confidence": event.confidence,
        "metadata": event.event_metadata,
        "zone_id": event.zone.zone_id if event.zone is not None else None,
        "line_id": event.line.line_id if event.line is not None else None,
    }


def get_camera_events(
    session: Session,
    camera_id: str,
    event_type: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Dict[str, Any]:
    """Events on one camera, optionally filtered by type and/or time range."""
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return {"error": f"no camera with camera_id={camera_id!r}"}
    events = repository.list_events_for_camera(
        session, camera, event_type=event_type, start_time=start_time, end_time=end_time
    )
    return {"camera_id": camera_id, "count": len(events), "events": [_event_to_dict(e) for e in events]}


def get_object_stats(session: Session, object_id: int) -> Dict[str, Any]:
    """Identity, lifespan, and event history for one tracked object (the
    internal database id, not the tracker's per-camera object_id -- same
    convention as GET /objects/{id}/trajectory, Section 10)."""
    obj = repository.get_object(session, object_id)
    if obj is None:
        return {"error": f"no tracked object with id={object_id}"}
    events = repository.get_events_for_object(session, obj)
    track_points = repository.get_track_points_for_object(session, obj)
    event_type_counts: Dict[str, int] = {}
    for event in events:
        event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
    return {
        "object_id": obj.id,
        "camera_id": obj.camera.camera_id,
        "class_name": obj.class_name,
        "first_seen": obj.first_seen,
        "last_seen": obj.last_seen,
        "duration_seconds": obj.last_seen - obj.first_seen,
        "track_point_count": len(track_points),
        "event_type_counts": event_type_counts,
        "events": [_event_to_dict(e) for e in events],
    }


def get_zone_events(session: Session, camera_id: str, zone_id: str) -> Dict[str, Any]:
    """Events tied to one configured zone on one camera (ZONE_ENTERED/ZONE_EXITED)."""
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return {"error": f"no camera with camera_id={camera_id!r}"}
    zone = repository.get_zone(session, camera, zone_id)
    if zone is None:
        return {"error": f"no zone with zone_id={zone_id!r} on camera {camera_id!r}"}
    events = repository.list_events_for_zone(session, zone)
    return {"camera_id": camera_id, "zone_id": zone_id, "count": len(events), "events": [_event_to_dict(e) for e in events]}


def get_line_crossings(session: Session, camera_id: str, line_id: str) -> Dict[str, Any]:
    """LINE_CROSSED events tied to one configured line on one camera."""
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return {"error": f"no camera with camera_id={camera_id!r}"}
    line = repository.get_line(session, camera, line_id)
    if line is None:
        return {"error": f"no line with line_id={line_id!r} on camera {camera_id!r}"}
    events = repository.list_events_for_line(session, line)
    return {"camera_id": camera_id, "line_id": line_id, "count": len(events), "events": [_event_to_dict(e) for e in events]}


def get_traffic_stats(
    session: Session,
    camera_id: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Dict[str, Any]:
    """Section 11's traffic metrics for one camera: distinct objects that
    crossed a line (traffic_volume) and the raw crossing count."""
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return {"error": f"no camera with camera_id={camera_id!r}"}
    return {
        "camera_id": camera_id,
        "start_time": start_time,
        "end_time": end_time,
        "traffic_volume": analytics_queries.traffic_volume(session, camera_id=camera_id, start_time=start_time, end_time=end_time),
        "line_crossing_count": analytics_queries.line_crossing_count(
            session, camera_id=camera_id, start_time=start_time, end_time=end_time
        ),
    }


def get_event(session: Session, event_id: int) -> Dict[str, Any]:
    """Full detail for one specific event by its database id."""
    event = repository.get_event(session, event_id)
    if event is None:
        return {"error": f"no event with id={event_id}"}
    return _event_to_dict(event)


def get_video_segment(
    session: Session,
    camera_id: str,
    timestamp: float,
    window_seconds: float = 5.0,
) -> Dict[str, Any]:
    """The video and time window around a moment on one camera -- the tool
    version of the dashboard's Event Investigation click-to-seek (Section 0):
    event -> timestamp -> this video segment -> the relevant frame. Assumes
    one video per camera, same as the rest of this codebase (Section 9's
    documented scope)."""
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return {"error": f"no camera with camera_id={camera_id!r}"}
    videos = repository.list_videos(session, camera_id=camera_id)
    if not videos:
        return {"error": f"no video registered for camera {camera_id!r}"}
    video = videos[0]
    return {
        "camera_id": camera_id,
        "video_id": video.id,
        "path": video.path,
        "start_time": max(0.0, timestamp - window_seconds),
        "end_time": timestamp + window_seconds,
        "stream_url": f"/videos/{video.id}/stream",
    }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Dict[str, Any]]


TOOL_SPECS: List[ToolSpec] = [
    ToolSpec(
        name="get_camera_events",
        description="List events on one camera, optionally filtered by event_type and/or a [start_time, end_time] range (seconds).",
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id, e.g. 'demo'."},
                "event_type": {
                    "type": "string",
                    "description": "Optional. One of LINE_CROSSED, ZONE_ENTERED, ZONE_EXITED, OVERSPEED, STOPPED, SUDDEN_STOP, LOITERING, OBJECT_APPEARED, OBJECT_DISAPPEARED.",
                },
                "start_time": {"type": "number", "description": "Optional. Only events at or after this timestamp (seconds)."},
                "end_time": {"type": "number", "description": "Optional. Only events at or before this timestamp (seconds)."},
            },
            "required": ["camera_id"],
        },
        handler=get_camera_events,
    ),
    ToolSpec(
        name="get_object_stats",
        description="Get identity, lifespan (first_seen/last_seen), and full event history for one tracked object by its internal database id.",
        input_schema={
            "type": "object",
            "properties": {"object_id": {"type": "integer", "description": "The tracked object's internal database id."}},
            "required": ["object_id"],
        },
        handler=get_object_stats,
    ),
    ToolSpec(
        name="get_zone_events",
        description="List ZONE_ENTERED/ZONE_EXITED events for one configured zone on one camera.",
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "zone_id": {"type": "string", "description": "The zone's id, as configured for that camera."},
            },
            "required": ["camera_id", "zone_id"],
        },
        handler=get_zone_events,
    ),
    ToolSpec(
        name="get_line_crossings",
        description="List LINE_CROSSED events for one configured line on one camera.",
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "line_id": {"type": "string", "description": "The line's id, as configured for that camera."},
            },
            "required": ["camera_id", "line_id"],
        },
        handler=get_line_crossings,
    ),
    ToolSpec(
        name="get_traffic_stats",
        description="Get traffic_volume (distinct objects that crossed a line) and line_crossing_count (raw crossing count) for one camera, optionally over a time range.",
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "start_time": {"type": "number", "description": "Optional. Only count crossings at or after this timestamp."},
                "end_time": {"type": "number", "description": "Optional. Only count crossings at or before this timestamp."},
            },
            "required": ["camera_id"],
        },
        handler=get_traffic_stats,
    ),
    ToolSpec(
        name="get_event",
        description="Get full detail for one specific event by its database id.",
        input_schema={
            "type": "object",
            "properties": {"event_id": {"type": "integer", "description": "The event's internal database id."}},
            "required": ["event_id"],
        },
        handler=get_event,
    ),
    ToolSpec(
        name="get_video_segment",
        description="Get the video and a [start_time, end_time] window around a specific moment on one camera, for investigating what happened around an event.",
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "timestamp": {"type": "number", "description": "The moment to center the window on, in seconds."},
                "window_seconds": {
                    "type": "number",
                    "description": "Optional. How many seconds before/after `timestamp` to include. Defaults to 5.",
                },
            },
            "required": ["camera_id", "timestamp"],
        },
        handler=get_video_segment,
    ),
    # --- Section 13: state-changing actions. Every one of these ONLY
    # validates and records a pending action -- see agent/actions.py's
    # module docstring for the real propose -> approve gate. None of them
    # ever mutate cameras/zones/lines/alerts directly, no matter what the
    # model does or doesn't say about confirmation. ---
    ToolSpec(
        name="create_alert",
        description=(
            "Propose creating an alert on a camera for a given event type. Does NOT take effect immediately -- "
            "returns a pending_action_id that a human must approve via POST /agent/actions/{id}/approve before "
            "the alert is actually created."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "event_type": {"type": "string", "description": "One of TRACE's 9 event types, e.g. 'OVERSPEED'."},
                "message": {"type": "string", "description": "The alert message."},
                "channel": {"type": "string", "description": "Delivery channel. 'dashboard' (default) or 'api'."},
            },
            "required": ["camera_id", "event_type", "message"],
        },
        handler=propose_create_alert,
    ),
    ToolSpec(
        name="configure_zone",
        description=(
            "Propose configuring a polygon zone on a camera. Does NOT take effect immediately -- returns a "
            "pending_action_id that a human must approve before the zone is actually created."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "zone_id": {"type": "string", "description": "The zone's id."},
                "polygon": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
                    "description": "At least 3 [x, y] points.",
                },
            },
            "required": ["camera_id", "zone_id", "polygon"],
        },
        handler=propose_configure_zone,
    ),
    ToolSpec(
        name="configure_line",
        description=(
            "Propose configuring a virtual line on a camera. Does NOT take effect immediately -- returns a "
            "pending_action_id that a human must approve before the line is actually created."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "line_id": {"type": "string", "description": "The line's id."},
                "start": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[x, y]"},
                "end": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[x, y]"},
            },
            "required": ["camera_id", "line_id", "start", "end"],
        },
        handler=propose_configure_line,
    ),
    ToolSpec(
        name="generate_report",
        description=(
            "Propose generating an analytics report (Section 11's metrics bundle) for a camera, optionally over "
            "a time range. Does NOT take effect immediately -- returns a pending_action_id that a human must "
            "approve before the report is actually generated."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "start_time": {"type": "number", "description": "Optional."},
                "end_time": {"type": "number", "description": "Optional."},
            },
            "required": ["camera_id"],
        },
        handler=propose_generate_report,
    ),
    ToolSpec(
        name="send_notification",
        description=(
            "Propose sending a notification about a camera via a delivery channel. Does NOT take effect "
            "immediately -- returns a pending_action_id that a human must approve before it's actually sent."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "The camera's human-readable id."},
                "message": {"type": "string", "description": "The notification message."},
                "channel": {"type": "string", "description": "Delivery channel. 'dashboard' (default) or 'api'."},
            },
            "required": ["camera_id", "message"],
        },
        handler=propose_send_notification,
    ),
]

TOOLS_BY_NAME: Dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}


def execute_tool(session: Session, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch one tool call by name -- the only place agent.py needs to
    know about the tool registry. An unknown tool name (a model
    hallucinating a tool that doesn't exist) returns an error dict rather
    than raising, same as an unresolvable id within a real tool."""
    spec = TOOLS_BY_NAME.get(name)
    if spec is None:
        return {"error": f"unknown tool {name!r}"}
    try:
        return spec.handler(session, **arguments)
    except TypeError as exc:
        return {"error": f"invalid arguments for tool {name!r}: {exc}"}
