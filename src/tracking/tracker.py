"""Tracker interface: any concrete tracker turns per-frame Detections into stable Tracks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from detection.detector import Detection


@dataclass
class Track:
    """One tracked object's state as of the frame it was last updated on.

    bbox is xyxy pixel coordinates, same convention as Detection.bbox (Section
    1.3 / Section 2). object_id is stable across frames for the same real
    object -- that stability, not the bbox itself, is what tracking adds over
    plain per-frame detection.
    """

    object_id: int
    class_name: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    timestamp: float
    frame_id: int


class Tracker(ABC):
    """Interface every concrete tracker implements.

    Kept minimal so the specific algorithm (ByteTrack, BoT-SORT, ...) stays
    swappable, mirroring Section 2's detector-as-interface design decision.

    `update()` must be called exactly once per video frame, in order --
    including frames with an empty detections list. Trackers built on a
    Kalman filter advance their internal motion model by one time step per
    call; skipping a call for an empty frame desyncs the tracker's notion of
    elapsed time from the real frame count.
    """

    @abstractmethod
    def update(self, detections: list[Detection]) -> list[Track]:
        """Advance the tracker by one frame and return the currently active tracks."""
        raise NotImplementedError
