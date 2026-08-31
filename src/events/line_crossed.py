"""LINE_CROSSED event: built from geometry.line_crossing's LineCrossing output.

Detection itself (segment intersection, direction) lives in
geometry.line_crossing (Phase 5) -- this module is only the pure translation
from (Track, LineCrossing) to Section 7's Event schema. No smoothing/debounce
needed here: segment intersection is already robust per-step, unlike zone
containment or speed.
"""

from __future__ import annotations

from events.event import Event
from geometry.line_crossing import LineCrossing
from tracking.tracker import Track

EVENT_TYPE = "LINE_CROSSED"


def build_event(track: Track, crossing: LineCrossing, camera_id: str) -> Event:
    return Event(
        event_type=EVENT_TYPE,
        object_id=track.object_id,
        class_name=track.class_name,
        timestamp=track.timestamp,
        camera_id=camera_id,
        confidence=track.confidence,
        metadata={
            "line_id": crossing.line_id,
            "direction": crossing.direction,
            "side_before": crossing.side_before,
            "side_after": crossing.side_after,
        },
    )
