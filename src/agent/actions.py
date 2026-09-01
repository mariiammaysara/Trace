"""State-changing agent actions (Section 13): create_alert, configure_zone,
configure_line, generate_report, send_notification.

Every one of these goes through a real propose -> approve gate, enforced in
code, not by a prompt instruction:

1. The agent (or anything) calls one of the `propose_*` functions below.
   Each validates its arguments and, if valid, inserts a `PendingAction` row
   (status="pending") describing exactly what it wants to do -- it NEVER
   touches cameras/zones/lines/alerts itself. These are the functions
   registered as agent tools (see tools.py's ACTION_TOOL_SPECS).
2. `execute_pending_action(session, action_id)` is the ONLY function that
   actually performs the real mutation. It re-checks the row's status is
   still "pending" (so double-approval or approving an already-executed
   action is a no-op error, not a double-execution), dispatches to the
   matching `_execute_*` handler, and marks the row "executed" with its
   result.

`execute_pending_action` is called from exactly one place in this codebase:
`POST /agent/actions/{id}/approve` (api/routers/agent.py). It is
deliberately NOT registered as an agent tool -- there is no way for the LLM,
within its own tool-calling loop, to approve an action it just proposed. If
approval were itself just another tool, a single conversation turn could
call propose-then-approve back to back with no real human step in between,
which would defeat the point of having an approval gate at all. Approval
only happens through a separate REST call representing a genuine
out-of-band human action (e.g. a dashboard "Approve" button).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from analytics import queries as analytics_queries
from database import repository
from events.line_crossed import EVENT_TYPE as LINE_CROSSED
from events.loitering import EVENT_TYPE as LOITERING
from events.object_appeared import EVENT_TYPE as OBJECT_APPEARED
from events.object_disappeared import EVENT_TYPE as OBJECT_DISAPPEARED
from events.overspeed import EVENT_TYPE as OVERSPEED
from events.stopped import EVENT_TYPE as STOPPED
from events.sudden_stop import EVENT_TYPE as SUDDEN_STOP
from events.zone_entered import EVENT_TYPE as ZONE_ENTERED
from events.zone_exited import EVENT_TYPE as ZONE_EXITED

SUPPORTED_CHANNELS = ("dashboard", "api")

# Every real TRACE event type (Section 7), imported from each rule module's
# own EVENT_TYPE constant rather than duplicated as a parallel literal list
# that could silently drift from the real ones.
ALL_EVENT_TYPES = {
    LINE_CROSSED,
    ZONE_ENTERED,
    ZONE_EXITED,
    OVERSPEED,
    STOPPED,
    SUDDEN_STOP,
    LOITERING,
    OBJECT_APPEARED,
    OBJECT_DISAPPEARED,
}


def _error(message: str) -> Dict[str, Any]:
    return {"error": message}


def _propose(session: Session, action_type: str, parameters: Dict[str, Any], summary: str) -> Dict[str, Any]:
    action = repository.create_pending_action(session, action_type, parameters, summary)
    return {
        "status": "pending_approval",
        "action_id": action.id,
        "action_type": action_type,
        "summary": summary,
        "parameters": parameters,
    }


# --- propose_*: validate only, never mutate. Registered as agent tools. ---


def propose_create_alert(
    session: Session, camera_id: str, event_type: str, message: str, channel: str = "dashboard"
) -> Dict[str, Any]:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return _error(f"no camera with camera_id={camera_id!r}")
    if event_type not in ALL_EVENT_TYPES:
        return _error(f"unknown event_type {event_type!r} -- must be one of {sorted(ALL_EVENT_TYPES)}")
    if not message.strip():
        return _error("message must not be empty")
    if channel not in SUPPORTED_CHANNELS:
        return _error(f"unsupported channel {channel!r} -- must be one of {SUPPORTED_CHANNELS}")

    parameters = {"camera_id": camera_id, "event_type": event_type, "message": message, "channel": channel}
    summary = f"Create a {event_type} alert on camera {camera_id!r}: {message!r} (channel: {channel})"
    return _propose(session, "create_alert", parameters, summary)


def propose_configure_zone(
    session: Session, camera_id: str, zone_id: str, polygon: List[Tuple[float, float]]
) -> Dict[str, Any]:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return _error(f"no camera with camera_id={camera_id!r}")
    if len(polygon) < 3:
        return _error("a zone needs at least 3 points")

    parameters = {"camera_id": camera_id, "zone_id": zone_id, "polygon": [list(point) for point in polygon]}
    summary = f"Configure zone {zone_id!r} on camera {camera_id!r} with {len(polygon)} points"
    return _propose(session, "configure_zone", parameters, summary)


def propose_configure_line(
    session: Session, camera_id: str, line_id: str, start: Tuple[float, float], end: Tuple[float, float]
) -> Dict[str, Any]:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return _error(f"no camera with camera_id={camera_id!r}")
    if tuple(start) == tuple(end):
        return _error("a line's start and end must differ")

    parameters = {"camera_id": camera_id, "line_id": line_id, "start": list(start), "end": list(end)}
    summary = f"Configure line {line_id!r} on camera {camera_id!r} from {tuple(start)} to {tuple(end)}"
    return _propose(session, "configure_line", parameters, summary)


def propose_generate_report(
    session: Session, camera_id: str, start_time: Optional[float] = None, end_time: Optional[float] = None
) -> Dict[str, Any]:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return _error(f"no camera with camera_id={camera_id!r}")
    if start_time is not None and end_time is not None and start_time > end_time:
        return _error("start_time must not be after end_time")

    parameters = {"camera_id": camera_id, "start_time": start_time, "end_time": end_time}
    summary = f"Generate an analytics report for camera {camera_id!r}"
    return _propose(session, "generate_report", parameters, summary)


def propose_send_notification(session: Session, camera_id: str, message: str, channel: str = "dashboard") -> Dict[str, Any]:
    camera = repository.get_camera(session, camera_id)
    if camera is None:
        return _error(f"no camera with camera_id={camera_id!r}")
    if not message.strip():
        return _error("message must not be empty")
    if channel not in SUPPORTED_CHANNELS:
        return _error(f"unsupported channel {channel!r} -- must be one of {SUPPORTED_CHANNELS}")

    parameters = {"camera_id": camera_id, "message": message, "channel": channel}
    summary = f"Send a notification on camera {camera_id!r} via {channel}: {message!r}"
    return _propose(session, "send_notification", parameters, summary)


# --- _execute_*: the real mutation, only ever called via execute_pending_action ---


def _execute_create_alert(session: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    camera = repository.get_camera(session, params["camera_id"])
    if camera is None:
        return _error(f"no camera with camera_id={params['camera_id']!r}")
    alert = repository.create_alert(
        session, camera, event_type=params["event_type"], message=params["message"], channel=params["channel"]
    )
    return {"alert_id": alert.id}


def _execute_configure_zone(session: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    camera = repository.get_camera(session, params["camera_id"])
    if camera is None:
        return _error(f"no camera with camera_id={params['camera_id']!r}")
    zone = repository.get_or_create_zone(session, camera, params["zone_id"], [tuple(p) for p in params["polygon"]])
    return {"zone_id": zone.zone_id, "id": zone.id}


def _execute_configure_line(session: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    camera = repository.get_camera(session, params["camera_id"])
    if camera is None:
        return _error(f"no camera with camera_id={params['camera_id']!r}")
    line = repository.get_or_create_line(session, camera, params["line_id"], tuple(params["start"]), tuple(params["end"]))
    return {"line_id": line.line_id, "id": line.id}


def _execute_generate_report(session: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    camera_id = params["camera_id"]
    filters = dict(camera_id=camera_id, start_time=params.get("start_time"), end_time=params.get("end_time"))
    # The same real Section 11 functions GET /analytics bundles -- a
    # generated "report" is this bundle, never a fabricated summary.
    return {
        "camera_id": camera_id,
        "start_time": params.get("start_time"),
        "end_time": params.get("end_time"),
        "object_count": analytics_queries.object_count(session, **filters),
        "line_crossing_count": analytics_queries.line_crossing_count(session, **filters),
        "zone_violation_count": analytics_queries.zone_violation_count(session, **filters),
        "average_dwell_time": analytics_queries.average_dwell_time(session, **filters),
        "traffic_volume": analytics_queries.traffic_volume(session, **filters),
        "event_frequency": analytics_queries.event_frequency(session, **filters),
        "per_class_stats": analytics_queries.per_class_stats(session, **filters),
    }


def _execute_send_notification(session: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    camera = repository.get_camera(session, params["camera_id"])
    if camera is None:
        return _error(f"no camera with camera_id={params['camera_id']!r}")
    alert = repository.create_alert(
        session, camera, event_type="AGENT_NOTIFICATION", message=params["message"], channel=params["channel"]
    )
    return {"alert_id": alert.id, "delivered_via": params["channel"]}


_EXECUTORS: Dict[str, Callable[[Session, Dict[str, Any]], Dict[str, Any]]] = {
    "create_alert": _execute_create_alert,
    "configure_zone": _execute_configure_zone,
    "configure_line": _execute_configure_line,
    "generate_report": _execute_generate_report,
    "send_notification": _execute_send_notification,
}


def execute_pending_action(session: Session, action_id: int) -> Dict[str, Any]:
    """The only function in this codebase that turns a PendingAction into a
    real mutation. Only reachable from POST /agent/actions/{id}/approve --
    see this module's docstring for why that's a deliberate, not
    incidental, restriction."""
    action = repository.get_pending_action(session, action_id)
    if action is None:
        return _error(f"no pending action with id={action_id}")
    if action.status != "pending":
        return _error(f"action {action_id} is not pending (status={action.status!r}) -- it was already executed")

    handler = _EXECUTORS[action.action_type]
    result = handler(session, action.parameters)

    action.status = "executed"
    action.result = result
    action.executed_at = dt.datetime.utcnow()
    session.commit()
    return result
