"""Real-world speed estimation: corrects pixel motion to real-world units via a
GroundPlaneHomography, using real elapsed time between frames (never assumed
FPS), per Section 6's algorithm:

    1. pixel position (ground-contact point) at t1 and t2
    2. apply homography -> estimated ground-plane real-world position at t1, t2
    3. real_distance = euclidean distance between the two world-plane points
    4. elapsed_time  = t2 - t1   (from frame timestamps, not assumed FPS)
    5. estimated_speed = real_distance / elapsed_time

Lives in geometry/, not trajectories/: it's meaningless without a homography,
whereas trajectories/ is deliberately pixel-space-only (Phase 4's explicit
scope). Keeping this here also keeps Sections 5 and 6 -- homography and speed
estimation -- co-located in one module, since neither means anything without
the other.

Per the study guide's explicit, deliberate convention (Section 6): this value
is always "estimated_speed", never "speed" or "measured speed" -- in the
field name below, in every log line, in every name that surfaces it. Multiple
real, independent error sources (calibration error, detection/tracking
jitter, non-planar ground, frame drops) mean it is never exact, and TRACE
does not claim otherwise anywhere it's reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

from geometry.homography import GroundPlaneHomography, ground_contact_point
from tracking.tracker import Track


@dataclass
class EstimatedSpeedSample:
    """One object's estimated_speed for one frame-to-frame step, in whatever
    real-world units the calibration's world_points used (meters, if you
    calibrated in meters -- TRACE doesn't hardcode a unit)."""

    object_id: int
    frame_id: int
    timestamp: float
    world_position: Tuple[float, float]
    estimated_speed: float


class SpeedEstimator:
    """Per-object real-world estimated_speed, fed directly by Tracker output."""

    def __init__(self, homography: GroundPlaneHomography) -> None:
        self._homography = homography
        self._last_world_position: Dict[int, Tuple[float, float]] = {}
        self._last_timestamp: Dict[int, float] = {}

    def update(self, tracks: list[Track]) -> list[EstimatedSpeedSample]:
        """Feed one frame's tracks in; returns an EstimatedSpeedSample for each
        track that already had a prior point (an object's first-ever
        appearance has nothing to compute estimated_speed against yet)."""
        samples = []
        for track in tracks:
            world_position = self._homography.pixel_to_world(ground_contact_point(track.bbox))
            object_id = track.object_id

            if object_id in self._last_world_position:
                prev_position = self._last_world_position[object_id]
                prev_timestamp = self._last_timestamp[object_id]
                dt = track.timestamp - prev_timestamp
                if dt > 0:
                    real_distance = math.hypot(
                        world_position[0] - prev_position[0],
                        world_position[1] - prev_position[1],
                    )
                    samples.append(
                        EstimatedSpeedSample(
                            object_id=object_id,
                            frame_id=track.frame_id,
                            timestamp=track.timestamp,
                            world_position=world_position,
                            estimated_speed=real_distance / dt,
                        )
                    )

            self._last_world_position[object_id] = world_position
            self._last_timestamp[object_id] = track.timestamp
        return samples
