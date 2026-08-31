"""Line-crossing detection: did an object's movement between two consecutive
trajectory points cross a configured virtual line, and in which direction.

Per Section 7's flagged edge case: checking "is the point past the line this
frame" (a single point-vs-line side comparison) misses fast-moving objects
that jump clean over a thin line between frames. The fix there is segment
intersection -- test whether the object's movement segment (point_before ->
point_after) actually intersects the line segment, not just whether the two
endpoints are on different sides of the line's *infinite* extension.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]


@dataclass
class Line:
    """A configured virtual line in pixel space, with two named endpoints.

    `id` identifies the line (e.g. for the eventual LINE_CROSSED event's
    `line` field, Phase 7). start/end order matters -- it defines which side
    is "left" and which is "right" for crossing direction (see _side below).
    """

    id: str
    start: Point
    end: Point

    @classmethod
    def from_config(cls, data: dict) -> "Line":
        return cls(id=data["id"], start=tuple(data["start"]), end=tuple(data["end"]))


@dataclass
class LineCrossing:
    """One detected crossing of one line by one movement segment.

    direction is "left_to_right" or "right_to_left", relative to walking from
    Line.start to Line.end (in image coordinates, y increases downward -- this
    is a geometric left/right, not a compass direction). side_before/side_after
    are the raw signed side values (+1 left, -1 right, 0 exactly on the line)
    the crossing was computed from.
    """

    line_id: str
    direction: str
    side_before: int
    side_after: int


def _orientation(p: Point, q: Point, r: Point) -> int:
    """+1 clockwise, -1 counterclockwise, 0 colinear, for ordered points p, q, r."""
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if val > 0:
        return 1
    if val < 0:
        return -1
    return 0


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    """True if q lies on segment p-r, given p, q, r are already known colinear."""
    return min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])


def segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """Standard orientation-based segment intersection test (handles the
    colinear/touching-endpoint edge cases correctly, not just the general
    case) -- whether segment p1-p2 intersects segment p3-p4 at all."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and _on_segment(p1, p3, p2):
        return True
    if o2 == 0 and _on_segment(p1, p4, p2):
        return True
    if o3 == 0 and _on_segment(p3, p1, p4):
        return True
    if o4 == 0 and _on_segment(p3, p2, p4):
        return True
    return False


def _side(line: Line, point: Point) -> int:
    """+1 if point is left of the directed line start->end, -1 if right, 0 if on it."""
    ax, ay = line.start
    bx, by = line.end
    px, py = point
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


def detect_line_crossing(line: Line, point_before: Point, point_after: Point) -> Optional[LineCrossing]:
    """Did the movement point_before -> point_after cross `line`? Returns None if not.

    Uses real segment intersection (not a naive "which side is each point on"
    check), so a fast-moving object whose two sampled points straddle the line
    from far apart is still caught, as long as its actual path segment crosses it.
    """
    if not segments_intersect(point_before, point_after, line.start, line.end):
        return None

    side_before = _side(line, point_before)
    side_after = _side(line, point_after)
    if side_before == side_after:
        # touched the line (e.g. an endpoint landed exactly on it) without
        # actually changing sides -- not a real crossing.
        return None

    direction = "left_to_right" if side_before > 0 else "right_to_left"
    return LineCrossing(line_id=line.id, direction=direction, side_before=side_before, side_after=side_after)


class LineCrossingDetector:
    """Stateful wrapper: call once per frame per object with its current
    position; internally keeps the previous position per object and runs
    detect_line_crossing() against every configured line."""

    def __init__(self, lines: List[Line]) -> None:
        self.lines = lines
        self._last_position: Dict[int, Point] = {}

    def update(self, object_id: int, point: Point) -> List[LineCrossing]:
        crossings = []
        previous = self._last_position.get(object_id)
        if previous is not None:
            for line in self.lines:
                crossing = detect_line_crossing(line, previous, point)
                if crossing is not None:
                    crossings.append(crossing)
        self._last_position[object_id] = point
        return crossings


def load_camera_lines(camera_id: str, configs_dir: "str | Path" = "configs/cameras") -> List[Line]:
    """configs/cameras/<camera_id>.json's "lines" array -> list[Line]. Empty if absent."""
    path = Path(configs_dir) / f"{camera_id}.json"
    with open(path) as f:
        data = json.load(f)
    return [Line.from_config(entry) for entry in data.get("lines", [])]
