"""Tests for events.object_appeared.ObjectAppearedRule and
events.object_disappeared.ObjectDisappearedRule."""

from __future__ import annotations

import pytest

from events.object_appeared import ObjectAppearedRule
from events.object_disappeared import ObjectDisappearedRule
from tracking.tracker import Track


def _track(object_id, timestamp, frame_id, class_name="person", confidence=0.9):
    return Track(object_id=object_id, class_name=class_name, bbox=(0.0, 0.0, 10.0, 10.0), confidence=confidence, timestamp=timestamp, frame_id=frame_id)


def test_appeared_fires_once_for_a_new_object_id():
    rule = ObjectAppearedRule()
    first = rule.update(_track(1, 0.0, 0))
    second = rule.update(_track(1, 1.0, 1))
    assert first is not None and first.event_type == "OBJECT_APPEARED"
    assert second is None


def test_appeared_fires_independently_per_object_id():
    rule = ObjectAppearedRule()
    e1 = rule.update(_track(1, 0.0, 0))
    e2 = rule.update(_track(2, 0.0, 0))
    assert e1 is not None and e2 is not None
    assert e1.object_id == 1 and e2.object_id == 2


def test_disappeared_does_not_fire_for_a_brief_absence_under_timeout():
    rule = ObjectDisappearedRule(missing_timeout_seconds=2.0)
    rule.update([_track(1, 0.0, 0)], current_timestamp=0.0)
    events = rule.update([], current_timestamp=0.5)  # 0.5s missing, under 2.0s timeout
    assert events == []
    events = rule.update([_track(1, 1.0, 2)], current_timestamp=1.0)  # reappears
    assert events == []  # no disappeared event should ever have fired


def test_disappeared_fires_once_after_timeout_elapses():
    rule = ObjectDisappearedRule(missing_timeout_seconds=2.0)
    rule.update([_track(1, 0.0, 0)], current_timestamp=0.0)
    assert rule.update([], current_timestamp=1.0) == []  # 1.0s missing, not yet

    events = rule.update([], current_timestamp=2.5)  # 2.5s missing, past timeout
    assert len(events) == 1
    assert events[0].event_type == "OBJECT_DISAPPEARED"
    assert events[0].object_id == 1

    events = rule.update([], current_timestamp=5.0)  # doesn't fire again
    assert events == []


def test_disappeared_caches_class_and_confidence_from_last_sighting():
    rule = ObjectDisappearedRule(missing_timeout_seconds=1.0)
    rule.update([_track(1, 0.0, 0, class_name="car", confidence=0.77)], current_timestamp=0.0)
    events = rule.update([], current_timestamp=2.0)
    assert events[0].class_name == "car"
    assert events[0].confidence == 0.77


def test_invalid_timeout_raises():
    with pytest.raises(ValueError):
        ObjectDisappearedRule(missing_timeout_seconds=0)
