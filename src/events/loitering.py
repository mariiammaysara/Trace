"""LOITERING event: dwell time in a zone exceeds a configured threshold.

Section 4's dwell time is defined cumulatively -- summed across every visit
to a zone, not reset per-visit -- and Section 7's LOITERING description
("dwell time exceeds configured threshold") uses that same cumulative
quantity. So LoiteringRule fires exactly once, ever, per (object_id, zone_id)
pair, the moment cumulative dwell time first crosses the threshold; there is
no "reset" afterward, because a cumulative sum only grows.

Section 4 flagged an open question this answers by construction: does brief
tracking loss reset the loitering timer? LoiteringRule is fed the *debounced*
confirmed containment from geometry.zone.ZoneDetector.is_inside() (via
trajectories.dwell.DwellTracker), not raw per-frame containment. A tracking
loss briefer than the zone's own debounce window never flips the confirmed
state, so DwellTracker never sees an exit, so the dwell timer is never
interrupted by it -- only a loss long enough to actually flip the debounced
zone state resets anything, and that's the zone debounce's job, not this
rule's.
"""

from __future__ import annotations

from typing import Set, Tuple

from events.event import Event
from tracking.tracker import Track
from trajectories.dwell import DwellTracker

EVENT_TYPE = "LOITERING"


class LoiteringRule:
    def __init__(self, min_dwell_seconds: float, camera_id: str = "") -> None:
        if min_dwell_seconds <= 0:
            raise ValueError(f"min_dwell_seconds must be > 0, got {min_dwell_seconds}")
        self.min_dwell_seconds = min_dwell_seconds
        self.camera_id = camera_id
        self._fired: Set[Tuple[int, str]] = set()

    def update(self, track: Track, zone_id: str, dwell_tracker: DwellTracker, timestamp: float) -> "Event | None":
        key = (track.object_id, zone_id)
        if key in self._fired:
            return None

        dwell_seconds = dwell_tracker.total_dwell_time(
            track.object_id, zone_id, include_open=True, current_timestamp=timestamp
        )
        if dwell_seconds < self.min_dwell_seconds:
            return None

        self._fired.add(key)
        return Event(
            event_type=EVENT_TYPE,
            object_id=track.object_id,
            class_name=track.class_name,
            timestamp=timestamp,
            camera_id=self.camera_id,
            confidence=track.confidence,
            metadata={"zone_id": zone_id, "dwell_seconds": dwell_seconds},
        )
