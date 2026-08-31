"""OBJECT_APPEARED event: a new track was created this frame.

Section 7's edge case: distinguishing a genuinely new object from a
re-identification after occlusion. This module can't resolve that ambiguity
by itself -- it only knows what Tracker.update() reports. Phase 3's own
ByteTrack testing found that a brief occlusion recovers under the *same*
object_id (no event needed here), while an occlusion beyond ByteTrack's own
track_buffer gets a genuinely new object_id on reappearance -- which really
is a new track from this system's point of view, and correctly fires
OBJECT_APPEARED again for that new id. ObjectAppearedRule fires the first
time it sees a given object_id, once, ever, per instance.
"""

from __future__ import annotations

from typing import Set

from events.event import Event
from tracking.tracker import Track

EVENT_TYPE = "OBJECT_APPEARED"


class ObjectAppearedRule:
    def __init__(self, camera_id: str = "") -> None:
        self.camera_id = camera_id
        self._seen: Set[int] = set()

    def update(self, track: Track) -> "Event | None":
        if track.object_id in self._seen:
            return None
        self._seen.add(track.object_id)
        return Event(
            event_type=EVENT_TYPE,
            object_id=track.object_id,
            class_name=track.class_name,
            timestamp=track.timestamp,
            camera_id=self.camera_id,
            confidence=track.confidence,
            metadata={},
        )
