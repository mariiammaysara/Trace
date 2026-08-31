"""Shared Event schema -- the common envelope every rule module in this
package emits, per Section 7.

The event engine is pure/deterministic: no module in src/events/ calls an
LLM or any other nondeterministic external service. Every Event here is
derived solely from Tracker/Trajectory/Geometry output through fixed,
auditable rules -- this is a hard constraint from the study guide's
engineering rules (the LLM reasons over structured data this layer produces,
it never produces the data itself), not a style preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Event:
    """One structured, semantic event.

    timestamp stays a float (seconds), matching every other timestamp in this
    codebase (Frame, Detection, Track, MotionStep) -- deliberately NOT the
    ISO8601 wall-clock string shown in Section 7's illustrative JSON. That
    string implicitly assumes a real calendar time, which file-based sources
    don't have (Phase 1: file timestamps are video-relative, not wall-clock);
    forcing ISO8601 here would silently misrepresent video-relative time as a
    real timestamp. Convert to a wall-clock string at the point you actually
    know the anchor (e.g. when writing to a database in Phase 8), not here.

    class_name (not `class`, a reserved word) holds the object's detected
    class; .to_dict() serializes it under the schema's "class" key.
    """

    event_type: str
    object_id: int
    class_name: str
    timestamp: float
    camera_id: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "object_id": self.object_id,
            "class": self.class_name,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }
