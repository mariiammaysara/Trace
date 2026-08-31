"""OBJECT_DISAPPEARED event: a track exceeds its missed-frame timeout.

Section 7's edge case: premature termination on brief occlusion produces
false disappear/reappear pairs. ObjectDisappearedRule only fires once an
object_id has been *absent* from Tracker.update()'s output for
missing_timeout_seconds of real elapsed time -- not the instant it vanishes
for a single frame, since ByteTrack (Phase 3) already recovers brief
occlusions under its own track_buffer without changing object_id. Set this
rule's timeout comfortably longer than ByteTrack's track_buffer converted to
seconds (frames / fps), or this will fire before ByteTrack even gives up on
the track internally.

class_name/confidence are cached from the last frame the object was actually
seen, since neither exists once it's gone from Tracker output.
"""

from __future__ import annotations

from typing import Dict, List

from events.event import Event
from tracking.tracker import Track

EVENT_TYPE = "OBJECT_DISAPPEARED"


class ObjectDisappearedRule:
    def __init__(self, missing_timeout_seconds: float, camera_id: str = "") -> None:
        if missing_timeout_seconds <= 0:
            raise ValueError(f"missing_timeout_seconds must be > 0, got {missing_timeout_seconds}")
        self.missing_timeout_seconds = missing_timeout_seconds
        self.camera_id = camera_id
        self._last_seen: Dict[int, Track] = {}

    def update(self, tracks: List[Track], current_timestamp: float) -> List[Event]:
        """Call once per frame with the full current track list, even when
        empty -- absence bookkeeping has to advance every frame, including
        frames where nothing at all is currently tracked."""
        present_ids = {t.object_id for t in tracks}
        for track in tracks:
            self._last_seen[track.object_id] = track

        events = []
        for object_id in list(self._last_seen):
            if object_id in present_ids:
                continue

            last_track = self._last_seen[object_id]
            missing_seconds = current_timestamp - last_track.timestamp
            if missing_seconds >= self.missing_timeout_seconds:
                events.append(
                    Event(
                        event_type=EVENT_TYPE,
                        object_id=object_id,
                        class_name=last_track.class_name,
                        timestamp=current_timestamp,
                        camera_id=self.camera_id,
                        confidence=last_track.confidence,
                        metadata={
                            "last_seen_frame_id": last_track.frame_id,
                            "missing_seconds": missing_seconds,
                        },
                    )
                )
                del self._last_seen[object_id]
        return events
