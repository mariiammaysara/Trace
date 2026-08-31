"""Per-zone dwell-time tracking: entry_timestamp -> exit_timestamp per
zone-visit, summed across multiple visits, per Section 4's dwell time
definition.

Deliberately decoupled from *how* zone membership is determined --
point-in-polygon geometry (Section 7's ZONE_ENTERED/ZONE_EXITED) is not
implemented yet. This module consumes a plain is_inside boolean per update
instead of computing membership itself, so it's usable the moment real zone
detection exists, unchanged: whatever produces that boolean (a polygon test,
a mock, a hand-authored test sequence) just needs to call update() once per
frame per (object_id, zone_id) pair being tracked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ZoneVisit:
    """One continuous stay of one object inside one zone. exit_timestamp is
    None while the visit is still open (the object hasn't left yet)."""

    object_id: int
    zone_id: str
    entry_timestamp: float
    exit_timestamp: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        """Visit length in seconds, or None while still open."""
        if self.exit_timestamp is None:
            return None
        return self.exit_timestamp - self.entry_timestamp


class DwellTracker:
    """Tracks zone visits per (object_id, zone_id) pair and sums their durations."""

    def __init__(self) -> None:
        self._open_visits: Dict[Tuple[int, str], ZoneVisit] = {}
        self._completed_visits: Dict[Tuple[int, str], List[ZoneVisit]] = {}

    def update(self, object_id: int, zone_id: str, is_inside: bool, timestamp: float) -> Optional[ZoneVisit]:
        """Feed one frame's membership state for one object/zone pair.

        Returns the just-completed ZoneVisit if this call closed one
        (transitioned inside -> outside), else None -- including while a
        visit stays open, and while the object stays outside the zone.
        """
        key = (object_id, zone_id)
        open_visit = self._open_visits.get(key)

        if is_inside and open_visit is None:
            self._open_visits[key] = ZoneVisit(object_id=object_id, zone_id=zone_id, entry_timestamp=timestamp)
            return None

        if not is_inside and open_visit is not None:
            open_visit.exit_timestamp = timestamp
            self._completed_visits.setdefault(key, []).append(open_visit)
            del self._open_visits[key]
            return open_visit

        return None

    def visits(self, object_id: int, zone_id: str) -> List[ZoneVisit]:
        """Completed visits for one object/zone pair, oldest first."""
        return list(self._completed_visits.get((object_id, zone_id), []))

    def total_dwell_time(
        self,
        object_id: int,
        zone_id: str,
        *,
        include_open: bool = True,
        current_timestamp: Optional[float] = None,
    ) -> float:
        """Sum of completed visit durations for one object/zone pair.

        If a visit is still open (the object hasn't left), pass
        include_open=True with current_timestamp to add its
        duration-so-far; otherwise only completed visits count.
        """
        key = (object_id, zone_id)
        total = sum(visit.duration for visit in self._completed_visits.get(key, []))

        open_visit = self._open_visits.get(key)
        if include_open and open_visit is not None and current_timestamp is not None:
            total += current_timestamp - open_visit.entry_timestamp

        return total
