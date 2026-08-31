"""Unified frame source: reads frames from a video file or a live camera through one interface."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Union

import cv2
import numpy as np


@dataclass
class Frame:
    """A single decoded frame, already converted to RGB.

    timestamp is video-relative seconds (from the file's own position, via
    cv2.CAP_PROP_POS_MSEC) when reading a file, or wall-clock time.time()
    seconds when reading a live camera. Check FrameSource.is_live to know
    which one a given Frame came from.
    """

    image: np.ndarray
    frame_id: int
    timestamp: float
    source_id: str


class FrameSource:
    """Reads frames from a video file or a live camera behind one interface.

    `source` is a file path (str) for a video file, or an int camera index
    for a live device — cv2.VideoCapture accepts both, which is what lets
    the rest of the pipeline stay agnostic to where frames come from.

    `frame_skip=N` processes every Nth frame (frame_skip=1 processes every
    frame). Frame ids always reflect the true position in the underlying
    source, including skipped frames, so they stay meaningful for seeking
    or correlating against the original video.

    BGR -> RGB conversion happens here, once, at the boundary — nothing
    downstream needs to think about color channel order.
    """

    def __init__(
        self,
        source: Union[str, int],
        source_id: str | None = None,
        frame_skip: int = 1,
    ) -> None:
        if frame_skip < 1:
            raise ValueError(f"frame_skip must be >= 1, got {frame_skip}")

        self._capture = cv2.VideoCapture(source)
        if not self._capture.isOpened():
            raise IOError(f"could not open frame source: {source!r}")

        self.source = source
        self.source_id = source_id if source_id is not None else str(source)
        self.frame_skip = frame_skip
        self.is_live = isinstance(source, int)
        self._frame_id = -1
        self._released = False

    def read(self) -> Frame | None:
        """Return the next Frame after applying frame_skip, or None once the source is exhausted."""
        image_bgr = None
        for _ in range(self.frame_skip):
            ok, image_bgr = self._capture.read()
            self._frame_id += 1
            if not ok:
                return None

        timestamp = (
            time.time()
            if self.is_live
            else self._capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        )
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        return Frame(
            image=image_rgb,
            frame_id=self._frame_id,
            timestamp=timestamp,
            source_id=self.source_id,
        )

    def release(self) -> None:
        if not self._released:
            self._capture.release()
            self._released = True

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
