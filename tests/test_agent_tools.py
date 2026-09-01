"""Unit tests for src/agent/tools.py: the underlying repository/analytics
calls are mocked so each test asserts, in isolation, that a tool builds the
correct query from its arguments -- not that the database works (that's
already covered by tests/test_repository.py and tests/test_analytics.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from agent import tools


@dataclass
class FakeRef:
    """Stand-in for a Camera/Zone/Line row -- tools only ever read .id and
    the human-readable id off these before passing the object straight
    through to another repository call. Carries all three human-id field
    names (camera_id/zone_id/line_id) so one fake class works for whichever
    of the three a given test needs, matching the real models' distinct
    attribute names."""

    id: int
    camera_id: str = "demo"
    zone_id: str = "zone-1"
    line_id: str = "line-1"


@dataclass
class FakeEvent:
    id: int
    object_id: int
    camera: FakeRef
    event_type: str = "OBJECT_APPEARED"
    class_name: str = "person"
    timestamp: float = 0.0
    confidence: float = 1.0
    event_metadata: Dict[str, Any] = field(default_factory=dict)
    zone: Optional[FakeRef] = None
    line: Optional[FakeRef] = None


# --- get_camera_events ---


def test_get_camera_events_unknown_camera_returns_error_without_querying_events():
    with patch.object(tools.repository, "get_camera", return_value=None) as get_camera, patch.object(
        tools.repository, "list_events_for_camera"
    ) as list_events:
        result = tools.get_camera_events(MagicMock(), camera_id="nope")

    get_camera.assert_called_once_with(get_camera.call_args.args[0], "nope")
    list_events.assert_not_called()
    assert result == {"error": "no camera with camera_id='nope'"}


def test_get_camera_events_passes_filters_through_to_repository():
    camera = FakeRef(id=7)
    events = [FakeEvent(id=1, object_id=1, camera=camera, event_type="OVERSPEED")]
    session = MagicMock()

    with patch.object(tools.repository, "get_camera", return_value=camera) as get_camera, patch.object(
        tools.repository, "list_events_for_camera", return_value=events
    ) as list_events:
        result = tools.get_camera_events(session, camera_id="demo", event_type="OVERSPEED", start_time=1.0, end_time=9.0)

    get_camera.assert_called_once_with(session, "demo")
    list_events.assert_called_once_with(session, camera, event_type="OVERSPEED", start_time=1.0, end_time=9.0)
    assert result["camera_id"] == "demo"
    assert result["count"] == 1
    assert result["events"][0]["event_type"] == "OVERSPEED"


# --- get_object_stats ---


def test_get_object_stats_unknown_object_returns_error():
    with patch.object(tools.repository, "get_object", return_value=None) as get_object:
        result = tools.get_object_stats(MagicMock(), object_id=999)

    get_object.assert_called_once()
    assert result == {"error": "no tracked object with id=999"}


def test_get_object_stats_summarizes_events_and_track_points():
    camera = FakeRef(id=1)
    obj = MagicMock(id=42, camera=camera, class_name="car", first_seen=0.0, last_seen=12.5)
    events = [
        FakeEvent(id=1, object_id=42, camera=camera, event_type="OBJECT_APPEARED"),
        FakeEvent(id=2, object_id=42, camera=camera, event_type="OVERSPEED"),
        FakeEvent(id=3, object_id=42, camera=camera, event_type="OVERSPEED"),
    ]
    session = MagicMock()

    with patch.object(tools.repository, "get_object", return_value=obj) as get_object, patch.object(
        tools.repository, "get_events_for_object", return_value=events
    ) as get_events, patch.object(tools.repository, "get_track_points_for_object", return_value=[MagicMock(), MagicMock()]):
        result = tools.get_object_stats(session, object_id=42)

    get_object.assert_called_once_with(session, 42)
    get_events.assert_called_once_with(session, obj)
    assert result["duration_seconds"] == 12.5
    assert result["track_point_count"] == 2
    assert result["event_type_counts"] == {"OBJECT_APPEARED": 1, "OVERSPEED": 2}


# --- get_zone_events ---


def test_get_zone_events_unknown_zone_returns_error():
    camera = FakeRef(id=1)
    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "get_zone", return_value=None
    ) as get_zone, patch.object(tools.repository, "list_events_for_zone") as list_events:
        result = tools.get_zone_events(MagicMock(), camera_id="demo", zone_id="restricted")

    get_zone.assert_called_once()
    list_events.assert_not_called()
    assert "error" in result


def test_get_zone_events_queries_by_resolved_zone():
    camera = FakeRef(id=1)
    zone = FakeRef(id=5)
    events = [FakeEvent(id=1, object_id=1, camera=camera, event_type="ZONE_ENTERED", zone=zone)]
    session = MagicMock()

    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "get_zone", return_value=zone
    ) as get_zone, patch.object(tools.repository, "list_events_for_zone", return_value=events) as list_events:
        result = tools.get_zone_events(session, camera_id="demo", zone_id="restricted")

    get_zone.assert_called_once_with(session, camera, "restricted")
    list_events.assert_called_once_with(session, zone)
    assert result["count"] == 1


# --- get_line_crossings ---


def test_get_line_crossings_unknown_line_returns_error():
    camera = FakeRef(id=1)
    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "get_line", return_value=None
    ) as get_line, patch.object(tools.repository, "list_events_for_line") as list_events:
        result = tools.get_line_crossings(MagicMock(), camera_id="demo", line_id="gate")

    get_line.assert_called_once()
    list_events.assert_not_called()
    assert "error" in result


def test_get_line_crossings_queries_by_resolved_line():
    camera = FakeRef(id=1)
    line = FakeRef(id=9)
    events = [FakeEvent(id=1, object_id=1, camera=camera, event_type="LINE_CROSSED", line=line)]
    session = MagicMock()

    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "get_line", return_value=line
    ) as get_line, patch.object(tools.repository, "list_events_for_line", return_value=events) as list_events:
        result = tools.get_line_crossings(session, camera_id="demo", line_id="gate")

    get_line.assert_called_once_with(session, camera, "gate")
    list_events.assert_called_once_with(session, line)
    assert result["count"] == 1


# --- get_traffic_stats ---


def test_get_traffic_stats_unknown_camera_returns_error_without_querying_analytics():
    with patch.object(tools.repository, "get_camera", return_value=None), patch.object(
        tools.analytics_queries, "traffic_volume"
    ) as traffic_volume:
        result = tools.get_traffic_stats(MagicMock(), camera_id="nope")

    traffic_volume.assert_not_called()
    assert "error" in result


def test_get_traffic_stats_forwards_camera_id_and_time_range():
    camera = FakeRef(id=1)
    session = MagicMock()

    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.analytics_queries, "traffic_volume", return_value=3
    ) as traffic_volume, patch.object(tools.analytics_queries, "line_crossing_count", return_value=5) as line_crossing_count:
        result = tools.get_traffic_stats(session, camera_id="demo", start_time=0.0, end_time=60.0)

    traffic_volume.assert_called_once_with(session, camera_id="demo", start_time=0.0, end_time=60.0)
    line_crossing_count.assert_called_once_with(session, camera_id="demo", start_time=0.0, end_time=60.0)
    assert result == {
        "camera_id": "demo",
        "start_time": 0.0,
        "end_time": 60.0,
        "traffic_volume": 3,
        "line_crossing_count": 5,
    }


# --- get_event ---


def test_get_event_unknown_id_returns_error():
    with patch.object(tools.repository, "get_event", return_value=None) as get_event:
        result = tools.get_event(MagicMock(), event_id=404)

    get_event.assert_called_once()
    assert result == {"error": "no event with id=404"}


def test_get_event_returns_full_detail():
    camera = FakeRef(id=1)
    zone = FakeRef(id=2)
    event = FakeEvent(id=10, object_id=3, camera=camera, event_type="ZONE_ENTERED", zone=zone, event_metadata={"foo": "bar"})
    session = MagicMock()

    with patch.object(tools.repository, "get_event", return_value=event) as get_event:
        result = tools.get_event(session, event_id=10)

    get_event.assert_called_once_with(session, 10)
    assert result["id"] == 10
    assert result["zone_id"] == zone.zone_id
    assert result["metadata"] == {"foo": "bar"}


# --- get_video_segment ---


def test_get_video_segment_no_video_registered_returns_error():
    camera = FakeRef(id=1)
    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "list_videos", return_value=[]
    ) as list_videos:
        result = tools.get_video_segment(MagicMock(), camera_id="demo", timestamp=10.0)

    list_videos.assert_called_once()
    assert "error" in result


def test_get_video_segment_builds_window_around_timestamp_clamped_at_zero():
    camera = FakeRef(id=1)
    video = MagicMock(id=5, path="data/sample.mp4")
    session = MagicMock()

    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "list_videos", return_value=[video]
    ) as list_videos:
        result = tools.get_video_segment(session, camera_id="demo", timestamp=2.0, window_seconds=5.0)

    list_videos.assert_called_once_with(session, camera_id="demo")
    assert result["start_time"] == 0.0  # 2.0 - 5.0 clamped to 0
    assert result["end_time"] == 7.0
    assert result["video_id"] == 5
    assert result["stream_url"] == "/videos/5/stream"


# --- execute_tool dispatch ---


def test_execute_tool_dispatches_by_name():
    camera = FakeRef(id=1)
    session = MagicMock()
    with patch.object(tools.repository, "get_camera", return_value=camera), patch.object(
        tools.repository, "list_events_for_camera", return_value=[]
    ):
        result = tools.execute_tool(session, "get_camera_events", {"camera_id": "demo"})
    assert result["camera_id"] == "demo"


def test_execute_tool_unknown_name_returns_error_not_exception():
    result = tools.execute_tool(MagicMock(), "not_a_real_tool", {})
    assert result == {"error": "unknown tool 'not_a_real_tool'"}


def test_execute_tool_invalid_arguments_returns_error_not_exception():
    result = tools.execute_tool(MagicMock(), "get_camera_events", {"not_a_real_kwarg": 1})
    assert "error" in result
