"""Tests for detection.detector.Detector interface and detection.yolo_detector.YoloDetector.

The bulk of these tests mock out ultralytics.YOLO entirely so they run fast and
offline, with no weights download. One integration-style test at the bottom
exercises the real pretrained model against a couple of real fixture frames
and only checks the *shape* of what comes back (well-formed Detection
objects), never exact detections -- YOLO output on arbitrary frames isn't
deterministic/robust enough to assert on precisely.
"""

from __future__ import annotations

import numpy as np
import pytest
import ultralytics

from detection.detector import Detection
from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import YoloDetector


class _FakeBox:
    def __init__(self, cls_id: int, confidence: float, xyxy):
        self.cls = [cls_id]
        self.conf = [confidence]
        self.xyxy = [xyxy]


class _FakeResults:
    def __init__(self, names, boxes):
        self.names = names
        self.boxes = boxes


class _FakeYOLO:
    """Stands in for ultralytics.YOLO -- returns a fixed set of fake boxes, no weights download."""

    NAMES = {0: "person", 1: "car", 2: "airplane"}

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.last_predict_kwargs = None

    def predict(self, image, conf, device, verbose):
        self.last_predict_kwargs = {"conf": conf, "device": device, "verbose": verbose}
        boxes = [
            _FakeBox(0, 0.91, (10.0, 20.0, 30.0, 40.0)),  # person -- in default allowlist
            _FakeBox(1, 0.55, (50.0, 60.0, 70.0, 80.0)),  # car -- in default allowlist
            _FakeBox(2, 0.99, (0.0, 0.0, 5.0, 5.0)),  # airplane -- not in default allowlist
        ]
        return [_FakeResults(self.NAMES, boxes)]


@pytest.fixture
def fake_yolo(monkeypatch):
    monkeypatch.setattr(ultralytics, "YOLO", _FakeYOLO)


@pytest.fixture
def sample_frame() -> Frame:
    return Frame(
        image=np.zeros((100, 100, 3), dtype=np.uint8),
        frame_id=7,
        timestamp=1.23,
        source_id="test",
    )


def test_detect_filters_to_default_allowlist_and_fills_all_fields(fake_yolo, sample_frame):
    detector = YoloDetector(model_path="fake.pt")
    detections = detector.detect(sample_frame)

    assert [d.class_name for d in detections] == ["person", "car"]
    person = detections[0]
    assert isinstance(person, Detection)
    assert person.bbox == (10.0, 20.0, 30.0, 40.0)
    assert person.confidence == 0.91
    assert person.frame_id == 7
    assert person.timestamp == 1.23


def test_confidence_threshold_is_passed_through_to_the_model(fake_yolo, sample_frame):
    detector = YoloDetector(model_path="fake.pt", confidence_threshold=0.4)
    detector.detect(sample_frame)
    assert detector._model.last_predict_kwargs["conf"] == 0.4


def test_custom_class_allowlist_filters_to_only_those_classes(fake_yolo, sample_frame):
    detector = YoloDetector(model_path="fake.pt", class_allowlist=("airplane",))
    detections = detector.detect(sample_frame)
    assert [d.class_name for d in detections] == ["airplane"]


def test_class_allowlist_none_keeps_every_class(fake_yolo, sample_frame):
    detector = YoloDetector(model_path="fake.pt", class_allowlist=None)
    detections = detector.detect(sample_frame)
    assert [d.class_name for d in detections] == ["person", "car", "airplane"]


def test_invalid_confidence_threshold_raises():
    with pytest.raises(ValueError):
        YoloDetector(model_path="fake.pt", confidence_threshold=1.5)


# --- integration: real model, real fixture frames, structure-only assertions ---


def test_yolo_detector_returns_well_formed_detections_on_real_frames(sample_video_path):
    detector = YoloDetector(confidence_threshold=0.01, class_allowlist=None)

    with FrameSource(str(sample_video_path)) as source:
        frames = [source.read(), source.read()]

    for frame in frames:
        assert frame is not None
        detections = detector.detect(frame)
        assert isinstance(detections, list)
        for det in detections:
            assert isinstance(det, Detection)
            assert isinstance(det.class_name, str) and det.class_name
            assert 0.0 <= det.confidence <= 1.0
            x_min, y_min, x_max, y_max = det.bbox
            assert x_min < x_max
            assert y_min < y_max
            assert det.frame_id == frame.frame_id
            assert det.timestamp == frame.timestamp
