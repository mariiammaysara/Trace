"""Per-object trajectory history and frame-to-frame motion analysis.

Pixel-space only: positions/speeds here are in pixels and pixels/second, not
real-world units -- that correction is Phase 5 (geometry/homography) and
Phase 6 (speed estimation), not this module. Per Section 4's own emphasis,
every quantity is computed per consecutive-point step, not from a track's
start/end -- that's what lets a stop or a direction change show up at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from tracking.tracker import Track

DEFAULT_STATIONARY_SPEED_THRESHOLD = 30.0  # pixels/second -- a starting point, not a universal constant;
# the right value depends on frame rate and camera distance/resolution (jitter of a few pixels/frame
# is normal detector/tracker noise), so tune it per deployment rather than trusting this default blindly.


def centroid(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Reduce an xyxy box to its centroid -- Section 4's documented default position.

    (Bottom-center, which better approximates ground contact, is a Phase
    5/6 concern for homography mapping -- not needed for pixel-space motion.)
    """
    x_min, y_min, x_max, y_max = bbox
    return ((x_min + x_max) / 2.0, (y_min + y_max) / 2.0)


def magnitude(vector: Tuple[float, float]) -> float:
    return math.hypot(vector[0], vector[1])


@dataclass
class MotionStep:
    """Motion computed between one track point and the point immediately before it.

    velocity/acceleration are vectors (px/s, px/s^2); speed is the velocity
    vector's magnitude; direction is atan2(dy, dx) in radians (0 when there
    was no displacement at all, e.g. a perfectly stationary step).
    acceleration is None until a second velocity sample exists (needs 3
    positions), matching Section 4's per-step formulas.
    """

    object_id: int
    frame_id: int
    timestamp: float
    position: Tuple[float, float]
    displacement: Tuple[float, float]
    velocity: Tuple[float, float]
    speed: float
    direction: float
    acceleration: Optional[Tuple[float, float]]
    is_stationary: bool


class Trajectory:
    """One object's position history plus the per-step motion derived from it.

    `stationary_speed_threshold` (px/s) is deliberately a single, simple
    threshold on instantaneous per-step speed -- no duration/hysteresis
    smoothing. That keeps small detector/tracker jitter around a truly
    stationary point from being misread as movement, as long as the
    threshold is set above typical jitter magnitude for the frame rate in
    use; sustained-duration state (LOITERING/STOPPED) is Section 7's job,
    not this module's.
    """

    def __init__(self, object_id: int, stationary_speed_threshold: float = DEFAULT_STATIONARY_SPEED_THRESHOLD) -> None:
        self.object_id = object_id
        self.stationary_speed_threshold = stationary_speed_threshold
        self.positions: list[Tuple[float, float]] = []
        self.timestamps: list[float] = []
        self.frame_ids: list[int] = []
        self._last_velocity: Optional[Tuple[float, float]] = None

    def update(self, position: Tuple[float, float], timestamp: float, frame_id: int) -> Optional[MotionStep]:
        """Record a new point and return the motion step it produced, or None
        if this is the first point ever (nothing to compute a step against
        yet) or the timestamp didn't advance (no meaningful velocity)."""
        self.positions.append(position)
        self.timestamps.append(timestamp)
        self.frame_ids.append(frame_id)

        if len(self.positions) < 2:
            return None

        prev_position = self.positions[-2]
        prev_timestamp = self.timestamps[-2]
        dt = timestamp - prev_timestamp
        if dt <= 0:
            return None

        dx = position[0] - prev_position[0]
        dy = position[1] - prev_position[1]
        displacement = (dx, dy)
        velocity = (dx / dt, dy / dt)
        speed = magnitude(velocity)
        direction = math.atan2(dy, dx)
        is_stationary = speed <= self.stationary_speed_threshold

        acceleration = None
        if self._last_velocity is not None:
            acceleration = (
                (velocity[0] - self._last_velocity[0]) / dt,
                (velocity[1] - self._last_velocity[1]) / dt,
            )
        self._last_velocity = velocity

        return MotionStep(
            object_id=self.object_id,
            frame_id=frame_id,
            timestamp=timestamp,
            position=position,
            displacement=displacement,
            velocity=velocity,
            speed=speed,
            direction=direction,
            acceleration=acceleration,
            is_stationary=is_stationary,
        )


class TrajectoryManager:
    """Maintains one Trajectory per object_id, fed by the Tracker's output each frame."""

    def __init__(self, stationary_speed_threshold: float = DEFAULT_STATIONARY_SPEED_THRESHOLD) -> None:
        self.stationary_speed_threshold = stationary_speed_threshold
        self.trajectories: Dict[int, Trajectory] = {}

    def update(self, tracks: list[Track]) -> list[MotionStep]:
        """Feed one frame's tracks in; returns a MotionStep for each track that
        already had at least one prior point (i.e. not each object's very
        first-ever appearance)."""
        steps = []
        for track in tracks:
            trajectory = self.trajectories.setdefault(
                track.object_id, Trajectory(track.object_id, self.stationary_speed_threshold)
            )
            step = trajectory.update(centroid(track.bbox), track.timestamp, track.frame_id)
            if step is not None:
                steps.append(step)
        return steps

    def get_path(self, object_id: int) -> list[Tuple[float, float]]:
        """Full position history for one object, oldest first. Empty if unseen."""
        trajectory = self.trajectories.get(object_id)
        return list(trajectory.positions) if trajectory is not None else []
