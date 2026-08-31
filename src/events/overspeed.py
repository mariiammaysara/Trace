"""OVERSPEED event: estimated_speed (Section 6) exceeds a configured limit.

Section 7's flagged edge case: a noisy single-frame speed spike must be
smoothed before comparing, or false alerts spike. OverspeedRule smooths with
a simple moving average over the last `window` estimated_speed samples per
object, and fires once per continuous over-limit period (not every frame
while still over) -- it resets when the smoothed value drops back under the
limit, so a later, genuinely new overspeed period can fire again.

Metadata keys follow Section 6's hard "estimated_speed" naming convention --
never bare "speed" -- for both the raw and smoothed values.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Optional

from events.event import Event
from geometry.speed import EstimatedSpeedSample
from tracking.tracker import Track

EVENT_TYPE = "OVERSPEED"


class OverspeedRule:
    def __init__(self, speed_limit: float, window: int = 3, camera_id: str = "") -> None:
        if speed_limit <= 0:
            raise ValueError(f"speed_limit must be > 0, got {speed_limit}")
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self.speed_limit = speed_limit
        self.window = window
        self.camera_id = camera_id
        self._history: Dict[int, Deque[float]] = {}
        self._over_limit: Dict[int, bool] = {}

    def update(self, track: Track, sample: Optional[EstimatedSpeedSample]) -> Optional[Event]:
        if sample is None:
            return None

        history = self._history.setdefault(track.object_id, deque(maxlen=self.window))
        history.append(sample.estimated_speed)
        smoothed_estimated_speed = sum(history) / len(history)

        was_over = self._over_limit.get(track.object_id, False)
        is_over = smoothed_estimated_speed > self.speed_limit
        self._over_limit[track.object_id] = is_over

        if is_over and not was_over:
            return Event(
                event_type=EVENT_TYPE,
                object_id=track.object_id,
                class_name=track.class_name,
                timestamp=track.timestamp,
                camera_id=self.camera_id,
                confidence=track.confidence,
                metadata={
                    "estimated_speed": sample.estimated_speed,
                    "smoothed_estimated_speed": smoothed_estimated_speed,
                    "limit": self.speed_limit,
                },
            )
        return None
