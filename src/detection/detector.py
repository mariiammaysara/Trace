"""Detector interface: any concrete detector turns a Frame into a list of Detections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from detection.frame_source import Frame


@dataclass
class Detection:
    """One detected object in one frame.

    bbox is (x_min, y_min, x_max, y_max) — absolute pixel coordinates in the
    source frame's own resolution, xyxy format (not xywh, not normalized
    0-1). Origin is the image's top-left corner, y increases downward, per
    Section 1.3 of the study guide. Every producer/consumer of Detection
    must agree on this format — a silent xyxy/xywh mismatch is a classic,
    hard-to-notice integration bug.
    """

    bbox: Tuple[float, float, float, float]
    class_name: str
    confidence: float
    frame_id: int
    timestamp: float


class Detector(ABC):
    """Interface every concrete detector implements.

    Kept deliberately minimal so the specific model (YOLO, RT-DETR, ...)
    stays swappable and never leaks into tracking/event code, per Section 2's
    "detector as swappable interface" design decision.
    """

    @abstractmethod
    def detect(self, frame: Frame) -> list[Detection]:
        """Return detections for one frame, already filtered to this detector's
        confidence threshold and class allowlist."""
        raise NotImplementedError
