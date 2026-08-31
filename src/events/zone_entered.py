"""ZONE_ENTERED event: built from geometry.zone's ZoneTransition output
(transition == "entered"). Debounce itself lives in geometry.zone.ZoneDetector
(Phase 5) -- this module is only the pure translation to Section 7's schema.
"""

from __future__ import annotations

from events.event import Event
from geometry.zone import ZoneTransition
from tracking.tracker import Track

EVENT_TYPE = "ZONE_ENTERED"


def build_event(track: Track, transition: ZoneTransition, camera_id: str) -> Event:
    if transition.transition != "entered":
        raise ValueError(f"expected an 'entered' transition, got {transition.transition!r}")
    return Event(
        event_type=EVENT_TYPE,
        object_id=track.object_id,
        class_name=track.class_name,
        timestamp=transition.timestamp,
        camera_id=camera_id,
        confidence=track.confidence,
        metadata={"zone_id": transition.zone_id},
    )
