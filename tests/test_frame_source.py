"""Tests for detection.frame_source.FrameSource against a synthetic sample video."""

from __future__ import annotations

import numpy as np
import pytest

from detection import frame_source as frame_source_module
from detection.frame_source import Frame, FrameSource


def test_read_returns_frame_instances(sample_video_path):
    with FrameSource(str(sample_video_path)) as source:
        frame = source.read()
    assert isinstance(frame, Frame)
    assert frame.frame_id == 0
    assert frame.image.ndim == 3
    assert frame.image.shape[2] == 3


def test_reads_every_frame_by_default(sample_video_path, sample_video_frame_count):
    frames = []
    with FrameSource(str(sample_video_path)) as source:
        while True:
            frame = source.read()
            if frame is None:
                break
            frames.append(frame)

    assert len(frames) == sample_video_frame_count
    assert [f.frame_id for f in frames] == list(range(sample_video_frame_count))


def test_frame_skip_advances_frame_id_and_reduces_count(sample_video_path, sample_video_frame_count):
    frame_skip = 3
    frames = []
    with FrameSource(str(sample_video_path), frame_skip=frame_skip) as source:
        while True:
            frame = source.read()
            if frame is None:
                break
            frames.append(frame)

    expected_count = sample_video_frame_count // frame_skip
    assert len(frames) == expected_count
    assert [f.frame_id for f in frames] == [
        frame_skip * i + (frame_skip - 1) for i in range(expected_count)
    ]


def test_bgr_to_rgb_conversion_happens_at_the_boundary(sample_video_path):
    # first frame was written as pure blue in BGR order; after conversion the
    # blue channel must land at index 2 (RGB), not index 0.
    with FrameSource(str(sample_video_path)) as source:
        frame = source.read()

    mean_r, _mean_g, mean_b = frame.image.reshape(-1, 3).mean(axis=0)
    assert mean_b > 150
    assert mean_r < 100


def test_source_id_defaults_to_source(sample_video_path):
    with FrameSource(str(sample_video_path)) as source:
        assert source.source_id == str(sample_video_path)


def test_source_id_can_be_overridden(sample_video_path):
    with FrameSource(str(sample_video_path), source_id="cam_1") as source:
        frame = source.read()
    assert frame.source_id == "cam_1"


def test_file_timestamps_are_video_relative_and_increasing(sample_video_path):
    with FrameSource(str(sample_video_path)) as source:
        assert source.is_live is False
        first = source.read()
        second = source.read()

    assert first.timestamp >= 0
    assert second.timestamp > first.timestamp


def test_read_returns_none_once_exhausted(sample_video_path, sample_video_frame_count):
    with FrameSource(str(sample_video_path)) as source:
        for _ in range(sample_video_frame_count):
            assert source.read() is not None
        assert source.read() is None


def test_invalid_frame_skip_raises(sample_video_path):
    with pytest.raises(ValueError):
        FrameSource(str(sample_video_path), frame_skip=0)


def test_nonexistent_file_path_raises_ioerror():
    with pytest.raises(IOError):
        FrameSource("this/path/does/not/exist.mp4")


def test_camera_source_is_marked_live_and_uses_wall_clock_timestamp(monkeypatch):
    fake_frame = np.zeros((4, 4, 3), dtype=np.uint8)

    class FakeCapture:
        def isOpened(self):
            return True

        def read(self):
            return True, fake_frame.copy()

        def get(self, prop):
            return 0.0

        def release(self):
            pass

    monkeypatch.setattr(frame_source_module.cv2, "VideoCapture", lambda source: FakeCapture())
    monkeypatch.setattr(frame_source_module.time, "time", lambda: 12345.0)

    with FrameSource(0) as source:
        assert source.is_live is True
        frame = source.read()

    assert frame.timestamp == 12345.0
