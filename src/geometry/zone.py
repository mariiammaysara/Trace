"""Zone containment: point-in-polygon test for a configured zone, with
debounce so a point wobbling right at the boundary doesn't fire spurious
enter/exit pairs -- the flicker problem Section 7 explicitly flags for
ZONE_ENTERED/ZONE_EXITED.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np

Point = Tuple[float, float]


@dataclass
class Zone:
    """A configured polygon zone in pixel space. `polygon` need not repeat the
    first point at the end -- it's treated as implicitly closed."""

    id: str
    polygon: List[Point]

    @classmethod
    def from_config(cls, data: dict) -> "Zone":
        return cls(id=data["id"], polygon=[tuple(p) for p in data["polygon"]])


def point_in_polygon(polygon: Sequence[Point], point: Point) -> bool:
    """cv2.pointPolygonTest under the hood (well-tested, handles the polygon
    edge cases correctly) rather than a hand-rolled ray-casting test. A point
    exactly on the boundary counts as inside."""
    contour = np.array(polygon, dtype=np.float32).reshape((-1, 1, 2))
    result = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False)
    return result >= 0


@dataclass
class ZoneTransition:
    """A confirmed (debounced) enter or exit of one zone by one object."""

    zone_id: str
    object_id: int
    transition: str  # "entered" or "exited"
    timestamp: float
    frame_id: int


class ZoneDetector:
    """Debounced zone containment per (object_id, zone) pair.

    Debounce strategy: consecutive-frame confirmation. A raw containment
    reading (point_in_polygon each frame) only flips the *confirmed* state
    -- and only then produces a ZoneTransition -- after `debounce_frames`
    consecutive frames agree with the new reading in a row. A single-frame
    flicker back to the old state resets that count to zero, so it takes a
    genuinely sustained change to confirm, not a momentary boundary wobble.

    This is deliberately the simplest debounce that solves the flicker
    problem: one configurable integer (frames, not a distance/time margin or
    a second buffer polygon), directly analogous to a hardware button
    debounce, and directly testable with a synthetic in/out/in/out sequence.
    """

    def __init__(self, zones: List[Zone], debounce_frames: int = 3) -> None:
        if debounce_frames < 1:
            raise ValueError(f"debounce_frames must be >= 1, got {debounce_frames}")
        self.zones: Dict[str, Zone] = {zone.id: zone for zone in zones}
        self.debounce_frames = debounce_frames
        self._confirmed_inside: Dict[Tuple[int, str], bool] = {}
        self._pending_state: Dict[Tuple[int, str], bool] = {}
        self._pending_streak: Dict[Tuple[int, str], int] = {}

    def update(self, object_id: int, point: Point, timestamp: float, frame_id: int) -> List[ZoneTransition]:
        transitions = []
        for zone_id, zone in self.zones.items():
            raw_inside = point_in_polygon(zone.polygon, point)
            key = (object_id, zone_id)
            confirmed_inside = self._confirmed_inside.get(key, False)

            if raw_inside == confirmed_inside:
                # agrees with the confirmed state -- nothing pending a flip
                self._pending_streak[key] = 0
                continue

            if self._pending_state.get(key) == raw_inside:
                self._pending_streak[key] = self._pending_streak.get(key, 0) + 1
            else:
                self._pending_state[key] = raw_inside
                self._pending_streak[key] = 1

            if self._pending_streak[key] >= self.debounce_frames:
                self._confirmed_inside[key] = raw_inside
                self._pending_streak[key] = 0
                transitions.append(
                    ZoneTransition(
                        zone_id=zone_id,
                        object_id=object_id,
                        transition="entered" if raw_inside else "exited",
                        timestamp=timestamp,
                        frame_id=frame_id,
                    )
                )
        return transitions


def load_camera_zones(camera_id: str, configs_dir: "str | Path" = "configs/cameras") -> List[Zone]:
    """configs/cameras/<camera_id>.json's "zones" array -> list[Zone]. Empty if absent."""
    path = Path(configs_dir) / f"{camera_id}.json"
    with open(path) as f:
        data = json.load(f)
    return [Zone.from_config(entry) for entry in data.get("zones", [])]
