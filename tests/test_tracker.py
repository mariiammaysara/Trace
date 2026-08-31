"""Tests for tracking.tracker.Tracker interface and tracking.byte_tracker.ByteTracker.

ByteTracker wraps ultralytics' own, already-tested BYTETracker rather than a
from-scratch Kalman filter/Hungarian implementation (see Section 3 of the
study guide for that trade-off), so these tests exercise TRACE's adapter
logic -- Detection in, Track out, id stability across synthetic sequences --
rather than re-verifying the underlying algorithm itself.

Ground-truth tracking metrics (MOTA/IDF1) require annotated tracking data we
don't have yet; that's `[PLANNED]` for the evaluation phase, not attempted
here (see Section 3 update in TRACE_STUDY_GUIDE.md).
"""

from __future__ import annotations

import pytest

from detection.detector import Detection
from detection.frame_source import FrameSource
from detection.yolo_detector import YoloDetector
from tracking.byte_tracker import ByteTracker
from tracking.tracker import Track


def _box_at(x_center: float, y_center: float, size: float = 20.0):
    half = size / 2
    return (x_center - half, y_center - half, x_center + half, y_center + half)


def _make_detection(x_center, y_center, class_name="person", confidence=0.9, frame_id=0, timestamp=0.0, size=20.0):
    return Detection(
        bbox=_box_at(x_center, y_center, size=size),
        class_name=class_name,
        confidence=confidence,
        frame_id=frame_id,
        timestamp=timestamp,
    )


def test_update_with_no_detections_returns_empty_list():
    tracker = ByteTracker()
    assert tracker.update([]) == []


def test_single_object_gets_stable_id_across_frames():
    tracker = ByteTracker()
    ids = []
    for frame_id in range(5):
        det = _make_detection(50 + frame_id, 50, frame_id=frame_id, timestamp=frame_id * 0.1)
        tracks = tracker.update([det])
        assert len(tracks) == 1
        ids.append(tracks[0].object_id)
    assert len(set(ids)) == 1


def test_track_fields_are_populated_from_the_source_detection():
    tracker = ByteTracker()
    det = _make_detection(50, 50, class_name="car", confidence=0.77, frame_id=42, timestamp=4.2)
    tracks = tracker.update([det])
    assert len(tracks) == 1
    track = tracks[0]
    assert isinstance(track, Track)
    assert isinstance(track.object_id, int)
    assert track.class_name == "car"
    assert track.confidence == pytest.approx(0.77)  # float32 round-trip through ultralytics' Boxes
    assert track.frame_id == 42
    assert track.timestamp == 4.2
    x_min, y_min, x_max, y_max = track.bbox
    assert x_min < x_max
    assert y_min < y_max


def test_two_objects_crossing_paths_keep_distinct_stable_ids():
    # Object A travels left->right along y=50; object B travels right->left
    # along y=150. Their x-positions cross at frame 10 (both reach x=120),
    # but they never overlap in y, so this is an unambiguous "crossing
    # paths" scenario with a known-correct answer: ids must never swap or
    # merge. Step size (10px) is kept well under box size (40px) so IoU-based
    # frame-to-frame matching has strong overlap to work with -- a step size
    # close to or exceeding box size would make consecutive-frame IoU drop to
    # ~0 and break tracking continuity, which is a property of this synthetic
    # sequence's motion, not something ByteTrack should be expected to handle.
    tracker = ByteTracker()
    ids_for_a = []
    ids_for_b = []

    for frame_id in range(20):
        x_a = 20 + frame_id * 10
        x_b = 220 - frame_id * 10
        det_a = _make_detection(x_a, 50, frame_id=frame_id, timestamp=frame_id * 0.1, size=40.0)
        det_b = _make_detection(x_b, 150, frame_id=frame_id, timestamp=frame_id * 0.1, size=40.0)

        tracks = tracker.update([det_a, det_b])
        assert len(tracks) == 2

        track_a = next(t for t in tracks if abs((t.bbox[1] + t.bbox[3]) / 2 - 50) < 5)
        track_b = next(t for t in tracks if abs((t.bbox[1] + t.bbox[3]) / 2 - 150) < 5)
        ids_for_a.append(track_a.object_id)
        ids_for_b.append(track_b.object_id)

    assert len(set(ids_for_a)) == 1, "object A's id changed across frames"
    assert len(set(ids_for_b)) == 1, "object B's id changed across frames"
    assert ids_for_a[0] != ids_for_b[0], "the two objects were assigned the same id"


def test_object_recovers_same_id_after_short_occlusion():
    tracker = ByteTracker(track_buffer=5)

    first = tracker.update([_make_detection(50, 50, frame_id=0, timestamp=0.0)])
    original_id = first[0].object_id

    # occluded for 2 frames -- well within track_buffer=5
    for frame_id in (1, 2):
        assert tracker.update([]) == []

    reappeared = tracker.update([_make_detection(54, 50, frame_id=3, timestamp=0.3)])
    assert len(reappeared) == 1
    assert reappeared[0].object_id == original_id


def test_object_gets_new_id_after_occlusion_beyond_track_buffer():
    tracker = ByteTracker(track_buffer=2)

    first = tracker.update([_make_detection(50, 50, frame_id=0, timestamp=0.0)])
    original_id = first[0].object_id

    # occluded for 4 frames -- well beyond track_buffer=2, so the original
    # track is removed rather than recovered.
    for frame_id in range(1, 5):
        tracker.update([])

    # The old track is gone, so this starts a brand-new track. Ultralytics'
    # BYTETracker only auto-confirms a new track on the tracker's very first
    # ever update() call; any later new track needs a second consecutive
    # match before it's reported (standard tentative-track confirmation, to
    # avoid spawning a track from one noisy detection) -- so the first
    # reappearance frame legitimately reports nothing yet.
    first_reappearance = tracker.update([_make_detection(50, 50, frame_id=5, timestamp=0.5)])
    assert first_reappearance == []

    confirmed_reappearance = tracker.update([_make_detection(51, 50, frame_id=6, timestamp=0.6)])
    assert len(confirmed_reappearance) == 1
    assert confirmed_reappearance[0].object_id != original_id


# --- integration: real detector + tracker, real fixture frames, structure-only assertions ---


def test_detector_to_tracker_pipeline_on_real_fixture_frames(sample_video_path):
    detector = YoloDetector(confidence_threshold=0.01, class_allowlist=None)
    tracker = ByteTracker()

    with FrameSource(str(sample_video_path)) as source:
        for _ in range(5):
            frame = source.read()
            if frame is None:
                break

            # tracker.update() runs every frame, even when detections is empty.
            detections = detector.detect(frame)
            tracks = tracker.update(detections)

            assert isinstance(tracks, list)
            for track in tracks:
                assert isinstance(track, Track)
                assert isinstance(track.object_id, int)
                assert isinstance(track.class_name, str) and track.class_name
                assert 0.0 <= track.confidence <= 1.0
                x_min, y_min, x_max, y_max = track.bbox
                assert x_min < x_max
                assert y_min < y_max
                assert track.frame_id == frame.frame_id
                assert track.timestamp == frame.timestamp
