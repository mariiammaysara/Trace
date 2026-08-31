"""STOPPED event: object stationary beyond a threshold duration.

Section 4's MotionStep.is_stationary is an instantaneous per-step read;
Section 7 requires that sustained over N real seconds before it counts as a
genuine STOPPED state, not tracker jitter -- "must distinguish 'genuinely
stopped' from tracker jitter." StoppedRule tracks how long an object's
is_stationary streak has run continuously (in real elapsed time, from
MotionStep.timestamp), and fires once when it first crosses
min_stationary_seconds. Any single step reading is_stationary=False breaks
the streak back to zero and re-arms the rule for the next stop.
"""

from __future__ import annotations

from typing import Dict, Optional

from events.event import Event
from tracking.tracker import Track
from trajectories.trajectory import MotionStep

EVENT_TYPE = "STOPPED"


class StoppedRule:
    def __init__(self, min_stationary_seconds: float, camera_id: str = "") -> None:
        if min_stationary_seconds <= 0:
            raise ValueError(f"min_stationary_seconds must be > 0, got {min_stationary_seconds}")
        self.min_stationary_seconds = min_stationary_seconds
        self.camera_id = camera_id
        self._streak_start: Dict[int, float] = {}
        self._fired: Dict[int, bool] = {}

    def update(self, track: Track, step: Optional[MotionStep]) -> Optional[Event]:
        if step is None:
            return None

        object_id = track.object_id
        if not step.is_stationary:
            self._streak_start.pop(object_id, None)
            self._fired[object_id] = False
            return None

        if object_id not in self._streak_start:
            self._streak_start[object_id] = step.timestamp

        duration = step.timestamp - self._streak_start[object_id]
        if duration >= self.min_stationary_seconds and not self._fired.get(object_id, False):
            self._fired[object_id] = True
            return Event(
                event_type=EVENT_TYPE,
                object_id=object_id,
                class_name=track.class_name,
                timestamp=step.timestamp,
                camera_id=self.camera_id,
                confidence=track.confidence,
                metadata={"stationary_duration_seconds": duration},
            )
        return None
