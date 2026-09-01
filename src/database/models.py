"""SQLAlchemy ORM models implementing Section 9's schema: cameras, videos,
objects, track_points, zones, lines, events -- with the foreign-key
relationships Section 9 diagrams:

    cameras 1--* videos
    cameras 1--* zones
    cameras 1--* lines
    cameras 1--* objects        (an object is tracked on one camera's feed)
    objects 1--* track_points   (an object's trajectory over time)
    objects 1--* events         (every semantic event references the object it happened to)
    zones   1--* events         (zone-related events reference which zone)
    lines   1--* events         (line-crossing events reference which line)

All per-frame timestamps (TrackPoint.timestamp, Event.timestamp,
TrackedObject.first_seen/last_seen) are floats (seconds), matching the
convention used everywhere else in this codebase since Phase 1 -- NOT
wall-clock DateTime. File-based sources are video-relative, not wall-clock
(Phase 1); forcing a DateTime column here would misrepresent that. Video.
started_at is the one deliberate exception: it's about when the *file was
registered for processing*, a genuine real-world moment, not a per-frame
timestamp.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    calibration_reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    videos: Mapped[List["Video"]] = relationship(back_populates="camera")
    zones: Mapped[List["Zone"]] = relationship(back_populates="camera")
    lines: Mapped[List["Line"]] = relationship(back_populates="camera")
    objects: Mapped[List["TrackedObject"]] = relationship(back_populates="camera")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    camera: Mapped["Camera"] = relationship(back_populates="videos")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    zone_id: Mapped[str] = mapped_column(String, nullable=False)  # matches geometry.zone.Zone.id
    polygon: Mapped[list] = mapped_column(JSON, nullable=False)  # [[x, y], ...]

    __table_args__ = (UniqueConstraint("camera_id", "zone_id", name="uq_zone_camera_zoneid"),)

    camera: Mapped["Camera"] = relationship(back_populates="zones")
    events: Mapped[List["Event"]] = relationship(back_populates="zone")


class Line(Base):
    __tablename__ = "lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    line_id: Mapped[str] = mapped_column(String, nullable=False)  # matches geometry.line_crossing.Line.id
    start_x: Mapped[float] = mapped_column(Float, nullable=False)
    start_y: Mapped[float] = mapped_column(Float, nullable=False)
    end_x: Mapped[float] = mapped_column(Float, nullable=False)
    end_y: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("camera_id", "line_id", name="uq_line_camera_lineid"),)

    camera: Mapped["Camera"] = relationship(back_populates="lines")
    events: Mapped[List["Event"]] = relationship(back_populates="line")


class TrackedObject(Base):
    """One row per tracked object's lifetime -- Section 9's `objects` table.

    object_id is the Tracker's own per-camera id (Section 3) -- NOT globally
    unique. ByteTrack's ids restart from 1 on every new tracker instance, so
    (camera_id, object_id) is only a stable key *within one continuous
    pipeline run*; a process restart that starts a fresh ByteTracker and
    reuses object_id=1 will be merged into the same row rather than starting
    a new one. This is a known, documented limitation, not an oversight --
    see the study guide's Section 9 update.
    """

    __tablename__ = "objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_name: Mapped[str] = mapped_column(String, nullable=False)
    first_seen: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("camera_id", "object_id", name="uq_object_camera_objectid"),)

    camera: Mapped["Camera"] = relationship(back_populates="objects")
    track_points: Mapped[List["TrackPoint"]] = relationship(back_populates="object", cascade="all, delete-orphan")
    events: Mapped[List["Event"]] = relationship(back_populates="object", cascade="all, delete-orphan")


class TrackPoint(Base):
    """Time-series position per object -- Section 9's `track_points` table.

    x/y is the centroid (Phase 4's trajectories.centroid()), kept for
    lightweight trajectory-line rendering. x_min/y_min/x_max/y_max is the
    full xyxy detection box (Section 1.3/2 convention) -- added in Phase 10.1
    so the dashboard's Live/Video overlay can draw real detection boxes
    instead of a fixed-size guess around the centroid. Nullable because it's
    optional at the repository layer: existing callers that only ever needed
    the centroid (Phase 8) keep working unchanged.
    """

    __tablename__ = "track_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False, index=True)
    frame_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    x_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    y_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    x_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    y_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    object: Mapped["TrackedObject"] = relationship(back_populates="track_points")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False, index=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("zones.id"), nullable=True)
    line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lines.id"), nullable=True)

    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # attribute is event_metadata (Base.metadata is a reserved SQLAlchemy name);
    # the actual DB column is still named "metadata", matching Section 7's schema.
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    object: Mapped["TrackedObject"] = relationship(back_populates="events")
    camera: Mapped["Camera"] = relationship()
    zone: Mapped[Optional["Zone"]] = relationship(back_populates="events")
    line: Mapped[Optional["Line"]] = relationship(back_populates="events")


class Alert(Base):
    """One delivered/triggered alert -- Section 13's real-time alerting.

    Created two ways, both going through repository.create_alert(): (1)
    automatically, synchronously, whenever add_event_from_pipeline() persists
    an event whose type is in alerts.rules.ALERT_TRIGGERING_EVENT_TYPES
    (event_id is set); (2) by the Vision Agent's create_alert/send_notification
    actions, only after a human approves the pending action that proposed it
    (Section 13) -- event_id is None for these, since they aren't tied to one
    specific persisted event.

    channel is the delivery channel this alert was recorded for -- "dashboard"
    (the dashboard/API polling GET /alerts, satisfying Section 13's "dashboard/
    API at minimum" delivery-channel requirement) or "api". Telegram is
    documented as [OPTIONAL] and was NOT implemented this phase (confirmed
    with the user before proceeding).
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("events.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    message: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False, default="dashboard")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)

    camera: Mapped["Camera"] = relationship()
    event: Mapped[Optional["Event"]] = relationship()


class PendingAction(Base):
    """The real, code-level approval gate for the Vision Agent's
    state-changing tools (Section 13) -- create_alert, configure_zone,
    configure_line, generate_report, send_notification.

    Every one of those tools, when the agent calls it, ONLY inserts a row
    here (status="pending") after validating its parameters -- it never
    touches cameras/zones/lines/alerts directly (src/agent/actions.py's
    propose_*() functions). The action only actually executes when
    execute_pending_action() runs against this row, which is reachable ONLY
    from POST /agent/actions/{id}/approve (api/routers/agent.py) -- there is
    no agent TOOL that can approve a pending action. That's deliberate: if
    approval were itself just another tool, a single conversation turn could
    call propose-then-approve back to back with no real human step in
    between, defeating the point of an approval gate.
    """

    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)  # pending | executed
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    executed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
