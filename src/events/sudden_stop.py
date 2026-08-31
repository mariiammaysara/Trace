"""SUDDEN_STOP event: rapid deceleration.

Section 7: "large negative acceleration within a short window," using real
elapsed time -- Section 4's MotionStep.acceleration is already computed from
real frame timestamps, never assumed FPS, so that requirement is inherited
for free. SuddenStopRule fires when a step's acceleration magnitude exceeds
min_deceleration_magnitude AND speed actually dropped versus the previous
step -- the second condition matters because a large acceleration magnitude
alone doesn't distinguish "slowing down hard" from "speeding up hard" or
"sharp turn at constant speed"; only an actual speed decrease is a stop.
"""

from __future__ import annotations

from typing import Dict, Optional

from events.event import Event
from tracking.tracker import Track
from trajectories.trajectory import MotionStep, magnitude

EVENT_TYPE = "SUDDEN_STOP"


class SuddenStopRule:
    def __init__(self, min_deceleration_magnitude: float, camera_id: str = "") -> None:
        if min_deceleration_magnitude <= 0:
            raise ValueError(f"min_deceleration_magnitude must be > 0, got {min_deceleration_magnitude}")
        self.min_deceleration_magnitude = min_deceleration_magnitude
        self.camera_id = camera_id
        self._last_speed: Dict[int, float] = {}

    def update(self, track: Track, step: Optional[MotionStep]) -> Optional[Event]:
        if step is None:
            return None

        object_id = track.object_id
        previous_speed = self._last_speed.get(object_id)
        self._last_speed[object_id] = step.speed

        if previous_speed is None or step.acceleration is None:
            return None

        deceleration_magnitude = magnitude(step.acceleration)
        speed_dropped = step.speed < previous_speed

        if deceleration_magnitude >= self.min_deceleration_magnitude and speed_dropped:
            return Event(
                event_type=EVENT_TYPE,
                object_id=object_id,
                class_name=track.class_name,
                timestamp=step.timestamp,
                camera_id=self.camera_id,
                confidence=track.confidence,
                metadata={
                    "acceleration": step.acceleration,
                    "deceleration_magnitude": deceleration_magnitude,
                    "speed_before": previous_speed,
                    "speed_after": step.speed,
                },
            )
        return None
