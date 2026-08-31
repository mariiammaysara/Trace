"""Tests for trajectories.dwell.DwellTracker: dwell time summed across zone-visits.

Uses a hand-authored is_inside boolean sequence rather than real point-in-polygon
zone detection, since that geometry (Section 7 / Phase 5) isn't implemented yet
-- DwellTracker is deliberately decoupled from how membership is computed.
"""

from __future__ import annotations

import pytest

from trajectories.dwell import DwellTracker


def test_no_visit_recorded_while_object_stays_outside():
    tracker = DwellTracker()
    assert tracker.update(1, "entrance", is_inside=False, timestamp=0.0) is None
    assert tracker.update(1, "entrance", is_inside=False, timestamp=1.0) is None
    assert tracker.visits(1, "entrance") == []


def test_single_visit_duration_is_exit_minus_entry():
    tracker = DwellTracker()
    assert tracker.update(1, "entrance", is_inside=False, timestamp=0.0) is None
    assert tracker.update(1, "entrance", is_inside=True, timestamp=1.0) is None  # enters
    assert tracker.update(1, "entrance", is_inside=True, timestamp=2.0) is None  # still inside

    completed = tracker.update(1, "entrance", is_inside=False, timestamp=3.0)  # exits
    assert completed is not None
    assert completed.entry_timestamp == 1.0
    assert completed.exit_timestamp == 3.0
    assert completed.duration == pytest.approx(2.0)

    assert tracker.total_dwell_time(1, "entrance") == pytest.approx(2.0)


def test_dwell_time_sums_across_multiple_visits():
    tracker = DwellTracker()

    # visit 1: enter at t=1, exit at t=3 -> duration 2.0
    tracker.update(1, "entrance", is_inside=True, timestamp=1.0)
    tracker.update(1, "entrance", is_inside=False, timestamp=3.0)

    # gap outside the zone
    tracker.update(1, "entrance", is_inside=False, timestamp=4.0)

    # visit 2: enter at t=5, exit at t=7 -> duration 2.0
    tracker.update(1, "entrance", is_inside=True, timestamp=5.0)
    tracker.update(1, "entrance", is_inside=False, timestamp=7.0)

    visits = tracker.visits(1, "entrance")
    assert len(visits) == 2
    assert [v.duration for v in visits] == [pytest.approx(2.0), pytest.approx(2.0)]
    assert tracker.total_dwell_time(1, "entrance") == pytest.approx(4.0)


def test_open_visit_is_excluded_unless_include_open_with_current_timestamp():
    tracker = DwellTracker()
    tracker.update(1, "entrance", is_inside=True, timestamp=1.0)  # still open, never exits

    assert tracker.total_dwell_time(1, "entrance", include_open=False) == 0.0
    assert tracker.total_dwell_time(1, "entrance", include_open=True, current_timestamp=None) == 0.0
    assert tracker.total_dwell_time(1, "entrance", include_open=True, current_timestamp=4.0) == pytest.approx(3.0)
    assert tracker.visits(1, "entrance") == []  # not completed, so not in the visit list


def test_objects_and_zones_are_tracked_independently():
    tracker = DwellTracker()
    tracker.update(1, "entrance", is_inside=True, timestamp=0.0)
    tracker.update(2, "entrance", is_inside=True, timestamp=0.0)
    tracker.update(1, "loading_dock", is_inside=True, timestamp=0.0)

    tracker.update(1, "entrance", is_inside=False, timestamp=2.0)  # object 1 leaves entrance after 2s
    tracker.update(2, "entrance", is_inside=False, timestamp=5.0)  # object 2 leaves entrance after 5s
    tracker.update(1, "loading_dock", is_inside=False, timestamp=10.0)  # object 1 leaves loading_dock after 10s

    assert tracker.total_dwell_time(1, "entrance") == pytest.approx(2.0)
    assert tracker.total_dwell_time(2, "entrance") == pytest.approx(5.0)
    assert tracker.total_dwell_time(1, "loading_dock") == pytest.approx(10.0)
