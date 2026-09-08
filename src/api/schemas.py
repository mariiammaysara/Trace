"""Pydantic request/response schemas for src/api/.

Validation lives here -- e.g. a zone polygon needs at least 3 points to be a
real polygon, enforced before any route handler or repository call ever sees
it. A malformed request never reaches business logic, per Section 10's
"validate at the API boundary" principle. FastAPI turns any ValueError raised
in a validator into a 422 response automatically -- no route-level code needed
for that.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1)
    name: Optional[str] = None
    location: Optional[str] = None
    calibration_reference: Optional[str] = None


class CameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    calibration_reference: Optional[str] = None


class CameraDeletionCounts(BaseModel):
    """Real per-table counts -- shared shape between the read-only preview
    (GET .../deletion-preview, computed with COUNT queries, nothing deleted)
    and the actual delete response (DELETE ..., the real number of rows each
    DELETE statement removed). Never a fabricated/estimated number in either
    case -- see database/repository.py's count_camera_dependents and
    delete_camera_cascade."""

    alerts: int
    events: int
    track_points: int
    objects: int
    videos: int
    zones: int
    lines: int


class CameraDeletionPreviewRead(BaseModel):
    camera_id: str
    counts: CameraDeletionCounts


class CameraDeleteRead(BaseModel):
    camera_id: str
    deleted: CameraDeletionCounts


class VideoCreate(BaseModel):
    camera_id: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    started_at: Optional[dt.datetime] = None


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    path: str
    started_at: Optional[dt.datetime] = None
    status: str = "done"
    total_frames: Optional[int] = None
    frames_processed: int = 0
    current_fps: Optional[float] = None
    error_message: Optional[str] = None


class VideoStatusRead(BaseModel):
    """GET /videos/{id}/status -- every field here is either a stored column
    or computed directly from two stored columns (percent, eta_seconds).
    Nothing here is a simulated/guessed number: percent is None until
    total_frames is known (always is, for an upload -- read from the file
    itself before the row exists) and eta_seconds is None until current_fps
    has a real measurement (see MIN_FRAMES_FOR_FPS_ESTIMATE in
    api/routers/videos.py -- an ETA from a 1-2 frame sample is noise, not a
    real estimate, so it's omitted rather than shown looking precise."""

    id: int
    status: str
    total_frames: Optional[int] = None
    frames_processed: int = 0
    percent: Optional[float] = None
    current_fps: Optional[float] = None
    eta_seconds: Optional[float] = None
    error_message: Optional[str] = None


class ZoneCreate(BaseModel):
    camera_id: str = Field(..., min_length=1)
    zone_id: str = Field(..., min_length=1)
    polygon: List[Tuple[float, float]]

    @field_validator("polygon")
    @classmethod
    def _at_least_three_points(cls, value: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(value) < 3:
            raise ValueError(f"a zone polygon needs at least 3 points to be a real polygon, got {len(value)}")
        return value


class ZoneRead(BaseModel):
    id: int
    zone_id: str
    polygon: List[List[float]]


class LineCreate(BaseModel):
    camera_id: str = Field(..., min_length=1)
    line_id: str = Field(..., min_length=1)
    start: Tuple[float, float]
    end: Tuple[float, float]

    @field_validator("end")
    @classmethod
    def _start_and_end_must_differ(cls, value: Tuple[float, float], info) -> Tuple[float, float]:
        start = info.data.get("start")
        if start is not None and tuple(value) == tuple(start):
            raise ValueError("a line's start and end points must be different -- a zero-length line has no direction")
        return value


class LineRead(BaseModel):
    id: int
    line_id: str
    start: Tuple[float, float]
    end: Tuple[float, float]


class TrackedObjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    object_id: int
    class_name: str
    first_seen: float
    last_seen: float


class EventRead(BaseModel):
    id: int
    object_id: int
    event_type: str
    class_name: str
    timestamp: float
    confidence: float
    metadata: Dict[str, Any]
    zone_id: Optional[str] = None
    line_id: Optional[str] = None


class TrackPointRead(BaseModel):
    frame_id: int
    timestamp: float
    x: float
    y: float
    x_min: Optional[float] = None
    y_min: Optional[float] = None
    x_max: Optional[float] = None
    y_max: Optional[float] = None


class TrajectoryRead(BaseModel):
    object_id: int
    camera_id: str
    class_name: str
    first_seen: float
    last_seen: float
    points: List[TrackPointRead]


class ObjectProfileRead(BaseModel):
    """GET /objects/{id} -- Phase 19's Object Profile view. Every field here
    is either a stored column or a real aggregate over stored rows (event
    count, dwell time); nothing is computed by re-running tracking."""

    id: int
    object_id: int
    class_name: str
    first_seen: float
    last_seen: float
    camera_id: str
    camera_name: Optional[str] = None
    total_dwell_seconds: float
    event_count: int


class AnalyticsSummary(BaseModel):
    """One bundled response for GET /analytics -- Section 10 lists a single
    endpoint returning "aggregated metrics", so this combines several of
    Section 11's functions for the requested camera/time-range filter rather
    than exposing eight separate query endpoints (which Section 10's table
    doesn't call for)."""

    camera_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    object_count: int
    line_crossing_count: int
    zone_violation_count: int
    average_dwell_time: float
    traffic_volume: int
    event_frequency: Dict[str, int]
    per_class_stats: Dict[str, Dict[str, int]]


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AgentToolCallRead(BaseModel):
    """One tool call the agent made while answering -- returned for
    transparency, so a caller can see exactly what grounded the answer."""

    name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]


class AgentQueryResponse(BaseModel):
    answer: str
    tool_calls: List[AgentToolCallRead]


class AlertCreate(BaseModel):
    """Direct alert creation -- Section 10/13's POST /alerts. Bypasses the
    agent's propose/approve gate entirely (that gate exists for the LLM's
    own autonomous tool-calling, Section 13; a direct API call is already a
    real human/system action, same as POST /zones or POST /lines)."""

    camera_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    channel: str = "dashboard"


class AlertRead(BaseModel):
    id: int
    camera_id: str
    event_id: Optional[int] = None
    event_type: str
    message: str
    channel: str
    created_at: dt.datetime


class PendingActionRead(BaseModel):
    """A proposed-but-not-yet-approved (or already-executed) agent action --
    Section 13's real, code-level approval gate. GET so a caller/dashboard
    can review a proposal before deciding whether to approve it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action_type: str
    parameters: Dict[str, Any]
    summary: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: dt.datetime
    executed_at: Optional[dt.datetime] = None
