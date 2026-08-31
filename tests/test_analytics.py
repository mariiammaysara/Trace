"""Analytics query tests against seeded data with known expected results.

Seed scenario (all on camera "cam_a"):
  object 1 (person): OBJECT_APPEARED@0.0, ZONE_ENTERED(z1)@1.0, ZONE_EXITED(z1)@4.0, LINE_CROSSED(l1)@5.0
  object 2 (car):     OBJECT_APPEARED@0.0, LINE_CROSSED(l1)@2.0, LINE_CROSSED(l1)@3.0

So: 2 objects (1 person, 1 car); 3 LINE_CROSSED events from 2 distinct objects;
1 ZONE_ENTERED; one completed zone visit of exactly 3.0s (4.0 - 1.0); 7 events
total, 4 for the person and 3 for the car.
"""

from __future__ import annotations

import pytest

from analytics import queries
from database import repository
from events.event import Event as PipelineEvent


@pytest.fixture
def seeded(db_session):
    camera = repository.get_or_create_camera(db_session, "cam_a")
    repository.get_or_create_zone(db_session, camera, "z1", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    repository.get_or_create_line(db_session, camera, "l1", (0.0, 50.0), (100.0, 50.0))

    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    repository.get_or_create_object(db_session, camera, object_id=2, class_name="car", timestamp=0.0)

    def emit(object_id, class_name, event_type, timestamp, metadata=None):
        repository.get_or_create_object(db_session, camera, object_id=object_id, class_name=class_name, timestamp=timestamp)
        event = PipelineEvent(
            event_type=event_type, object_id=object_id, class_name=class_name,
            timestamp=timestamp, camera_id="cam_a", confidence=0.9, metadata=metadata or {},
        )
        repository.add_event_from_pipeline(db_session, camera, event)

    emit(1, "person", "OBJECT_APPEARED", 0.0)
    emit(1, "person", "ZONE_ENTERED", 1.0, {"zone_id": "z1"})
    emit(1, "person", "ZONE_EXITED", 4.0, {"zone_id": "z1"})
    emit(1, "person", "LINE_CROSSED", 5.0, {"line_id": "l1"})

    emit(2, "car", "OBJECT_APPEARED", 0.0)
    emit(2, "car", "LINE_CROSSED", 2.0, {"line_id": "l1"})
    emit(2, "car", "LINE_CROSSED", 3.0, {"line_id": "l1"})

    db_session.flush()
    return db_session


def test_object_count(seeded):
    assert queries.object_count(seeded, camera_id="cam_a") == 2
    assert queries.object_count(seeded, camera_id="cam_a", class_name="person") == 1
    assert queries.object_count(seeded, camera_id="cam_a", class_name="car") == 1
    assert queries.object_count(seeded, camera_id="nonexistent_camera") == 0


def test_line_crossing_count(seeded):
    assert queries.line_crossing_count(seeded, camera_id="cam_a") == 3
    assert queries.line_crossing_count(seeded, camera_id="cam_a", line_id="l1") == 3


def test_zone_violation_count(seeded):
    assert queries.zone_violation_count(seeded, camera_id="cam_a") == 1
    assert queries.zone_violation_count(seeded, camera_id="cam_a", zone_id="z1") == 1


def test_average_dwell_time(seeded):
    assert queries.average_dwell_time(seeded, camera_id="cam_a", zone_id="z1") == pytest.approx(3.0)


def test_average_dwell_time_is_zero_with_no_completed_visits(seeded):
    assert queries.average_dwell_time(seeded, camera_id="cam_a", zone_id="nonexistent_zone") == 0.0


def test_traffic_volume_counts_distinct_objects_not_raw_crossings(seeded):
    # object 2 crossed twice, object 1 crossed once -- traffic_volume counts
    # 2 distinct objects, unlike line_crossing_count's raw count of 3.
    assert queries.traffic_volume(seeded, camera_id="cam_a") == 2


def test_event_frequency(seeded):
    frequency = queries.event_frequency(seeded, camera_id="cam_a")
    assert frequency == {
        "OBJECT_APPEARED": 2,
        "ZONE_ENTERED": 1,
        "ZONE_EXITED": 1,
        "LINE_CROSSED": 3,
    }


def test_per_class_stats(seeded):
    stats = queries.per_class_stats(seeded, camera_id="cam_a")
    assert stats["person"] == {"object_count": 1, "event_count": 4}
    assert stats["car"] == {"object_count": 1, "event_count": 3}


def test_busiest_hours_returns_the_bucket_containing_all_seeded_events(seeded):
    # all seeded events land in the same UTC hour bucket (timestamps 0.0-5.0
    # as Unix epoch seconds are all within the same hour) -- so exactly one
    # bucket should come back holding the full event count.
    result = queries.busiest_hours(seeded, camera_id="cam_a", top_n=5)
    assert len(result) == 1
    _bucket, count = result[0]
    assert count == 7
