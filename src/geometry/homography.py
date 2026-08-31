"""Ground-plane homography: maps a pixel position to an estimated real-world
position, given 4+ configured pixel<->real-world point correspondences per
camera. Practical, lightweight calibration per Section 5 -- not full 3D
camera calibration (intrinsics/extrinsics), which this system doesn't need
for a fixed, roughly-planar-ground scene.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Tuple

import cv2
import numpy as np


def ground_contact_point(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Bottom-center of an xyxy box, not the centroid.

    Section 5 is explicit about why: homography is only valid for points on
    the calibrated plane (the ground), and it does not correctly map a point
    at head-height (a person's centroid) to ground-plane real-world
    coordinates. The bottom-center of the box approximates where the object
    actually touches the ground, which is what the calibrated plane models --
    the centroid does not. This is a different position than Phase 4's
    trajectories.centroid(), deliberately: that one is pixel-space-only
    motion, this one is specifically for homography mapping.
    """
    x_min, y_min, x_max, y_max = bbox
    return ((x_min + x_max) / 2.0, y_max)


class GroundPlaneHomography:
    """A homography fit from 4+ pixel<->real-world point correspondences on one
    camera's ground plane, per Section 5's practical-calibration approach.

    `pixel_to_world()` is only meaningful for points on the plane the
    correspondences were measured on (see ground_contact_point) -- feeding it
    an arbitrary image point (e.g. a centroid at head-height) produces a
    number, but not a physically meaningful one.
    """

    def __init__(
        self,
        pixel_points: Sequence[Tuple[float, float]],
        world_points: Sequence[Tuple[float, float]],
    ) -> None:
        if len(pixel_points) != len(world_points):
            raise ValueError(
                f"pixel_points and world_points must be the same length, got {len(pixel_points)} and {len(world_points)}"
            )
        if len(pixel_points) < 4:
            raise ValueError(f"homography needs at least 4 point correspondences, got {len(pixel_points)}")

        matrix, _ = cv2.findHomography(
            np.array(pixel_points, dtype=np.float64),
            np.array(world_points, dtype=np.float64),
        )
        if matrix is None:
            raise ValueError("cv2.findHomography could not compute a homography from the given correspondences")
        self._matrix = matrix

    def pixel_to_world(self, pixel_point: Tuple[float, float]) -> Tuple[float, float]:
        """Map one pixel position on the calibrated ground plane to an estimated
        real-world position, in whatever units the configured world_points used."""
        src = np.array([[[pixel_point[0], pixel_point[1]]]], dtype=np.float64)
        dst = cv2.perspectiveTransform(src, self._matrix)
        return (float(dst[0, 0, 0]), float(dst[0, 0, 1]))

    @classmethod
    def from_correspondences(cls, correspondences: Sequence[dict]) -> "GroundPlaneHomography":
        """Build from a list of {"pixel": [x, y], "world": [X, Y]} dicts."""
        pixel_points = [tuple(c["pixel"]) for c in correspondences]
        world_points = [tuple(c["world"]) for c in correspondences]
        return cls(pixel_points, world_points)

    @classmethod
    def from_config(cls, path: "str | Path") -> "GroundPlaneHomography":
        """Load correspondences from a JSON config file (see configs/cameras/ for
        the expected {"camera_id": ..., "correspondences": [...]} shape)."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_correspondences(data["correspondences"])


def load_camera_homography(camera_id: str, configs_dir: "str | Path" = "configs/cameras") -> GroundPlaneHomography:
    """Convenience loader: configs/cameras/<camera_id>.json -> GroundPlaneHomography."""
    path = Path(configs_dir) / f"{camera_id}.json"
    return GroundPlaneHomography.from_config(path)
