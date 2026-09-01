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
