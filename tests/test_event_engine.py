"""Integration tests for events.engine.EventEngine: wires Trajectory + Geometry
internally and drives every Section 7 rule from one tracks-per-frame call.
"""

from __future__ import annotations

from detection.frame_source import FrameSource
from detection.yolo_detector import YoloDetector
from events.engine import EventEngine
from events.event import Event
from geometry.homography import GroundPlaneHomography
from geometry.line_crossing import Line
from geometry.zone import Zone
from tracking.byte_tracker import ByteTracker
from tracking.tracker import Track

PIXEL_POINTS = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
WORLD_POINTS = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]


def _track(object_id, x, y, timestamp, frame_id, w=20.0, confidence=0.9):
    return Track(
        object_id=object_id, class_name="person",
        bbox=(x - w / 2, y - w / 2, x + w / 2, y + w / 2),
        confidence=confidence, timestamp=timestamp, frame_id=frame_id,
    )


def test_object_appeared_fires_on_first_frame():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    engine = EventEngine("cam_1", homography)
    events = engine.update([_track(1, 50, 50, 0.0, 0)], timestamp=0.0)
    appeared = [e for e in events if e.event_type == "OBJECT_APPEARED"]
    assert len(appeared) == 1


def test_object_disappeared_fires_after_timeout_through_the_engine():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    engine = EventEngine("cam_1", homography, missing_timeout_seconds=1.0)
    engine.update([_track(1, 50, 50, 0.0, 0)], timestamp=0.0)
    events = engine.update([], timestamp=2.0)  # 2s gap, exceeds 1.0s timeout
    disappeared = [e for e in events if e.event_type == "OBJECT_DISAPPEARED"]
    assert len(disappeared) == 1


def test_line_crossing_flows_through_the_engine():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    line = Line(id="l1", start=(0.0, 50.0), end=(100.0, 50.0))
    engine = EventEngine("cam_1", homography, lines=[line])

    engine.update([_track(1, 50, 0, 0.0, 0)], timestamp=0.0)
    events = engine.update([_track(1, 50, 100, 1.0, 1)], timestamp=1.0)

    crossed = [e for e in events if e.event_type == "LINE_CROSSED"]
    assert len(crossed) == 1
    assert crossed[0].metadata["line_id"] == "l1"


def test_stopped_and_sudden_stop_flow_through_the_engine_together():
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    engine = EventEngine(
        "cam_1", homography,
        stationary_speed_threshold=30.0,
        min_stationary_seconds=0.2,
        min_deceleration_magnitude=500.0,
    )

    # moves fast, then stops abruptly and stays stopped
    engine.update([_track(1, 0, 50, 0.0, 0)], timestamp=0.0)
    events = engine.update([_track(1, 50, 50, 0.1, 1)], timestamp=0.1)  # 500 px/s
    events += engine.update([_track(1, 50, 50, 0.2, 2)], timestamp=0.2)  # stopped -- large deceleration
    events += engine.update([_track(1, 50, 50, 0.3, 3)], timestamp=0.3)
    events += engine.update([_track(1, 50, 50, 0.4, 4)], timestamp=0.4)  # sustained past 0.2s

    event_types = {e.event_type for e in events}
    assert "SUDDEN_STOP" in event_types
    assert "STOPPED" in event_types


def test_full_pipeline_smoke_test_on_real_fixture_video(sample_video_path):
    # structure-only assertions -- same pattern as every previous phase's
    # real-fixture integration test: no exceptions, well-formed output, never
    # asserting exact events (not deterministic/robust enough to assert on).
    homography = GroundPlaneHomography(PIXEL_POINTS, WORLD_POINTS)
    zone = Zone(id="restricted_area", polygon=[(0.0, 0.0), (64.0, 0.0), (64.0, 64.0), (0.0, 64.0)])
    line = Line(id="mid_line", start=(0.0, 32.0), end=(64.0, 32.0))
    engine = EventEngine("cam_1", homography, lines=[line], zones=[zone])

    detector = YoloDetector(confidence_threshold=0.01, class_allowlist=None)
    tracker = ByteTracker()

    with FrameSource(str(sample_video_path)) as source:
        for _ in range(5):
            frame = source.read()
            if frame is None:
                break

            detections = detector.detect(frame)
            tracks = tracker.update(detections)
            events = engine.update(tracks, timestamp=frame.timestamp)

            assert isinstance(events, list)
            for event in events:
                assert isinstance(event, Event)
                assert isinstance(event.event_type, str) and event.event_type
                assert isinstance(event.object_id, int)
                assert isinstance(event.class_name, str) and event.class_name
                assert event.camera_id == "cam_1"
                assert 0.0 <= event.confidence <= 1.0
                assert isinstance(event.metadata, dict)
