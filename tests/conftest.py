"""Shared pytest fixtures for TRACE tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_VIDEO_PATH = FIXTURES_DIR / "sample_video.mp4"
SAMPLE_VIDEO_FRAME_COUNT = 15
SAMPLE_VIDEO_FPS = 10
SAMPLE_VIDEO_WIDTH = 64
SAMPLE_VIDEO_HEIGHT = 64


def _generate_sample_video(path: Path) -> None:
    """Write a small synthetic test video: solid-color frames, first frame pure blue (BGR order)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        SAMPLE_VIDEO_FPS,
        (SAMPLE_VIDEO_WIDTH, SAMPLE_VIDEO_HEIGHT),
    )
    try:
        for i in range(SAMPLE_VIDEO_FRAME_COUNT):
            frame_bgr = np.zeros((SAMPLE_VIDEO_HEIGHT, SAMPLE_VIDEO_WIDTH, 3), dtype=np.uint8)
            if i == 0:
                frame_bgr[:, :] = (255, 0, 0)  # pure blue, written in BGR channel order
            else:
                frame_bgr[:, :] = (0, 0, min(255, 20 + i * 15))  # increasingly red, BGR order
            writer.write(frame_bgr)
    finally:
        writer.release()


@pytest.fixture(scope="session")
def sample_video_path() -> Path:
    """Path to a small synthetic test video, generated once under tests/fixtures/ if missing."""
    if not SAMPLE_VIDEO_PATH.exists():
        _generate_sample_video(SAMPLE_VIDEO_PATH)
    return SAMPLE_VIDEO_PATH


@pytest.fixture
def sample_video_frame_count() -> int:
    return SAMPLE_VIDEO_FRAME_COUNT
