"""A small, fully controlled synthetic 2-object crossing scenario.

Used two ways: (1) tests/test_evaluation_tracking.py builds a hand-derivable
expected MOTA/IDF1 from a tiny slice of this shape, verifying the harness's
own correctness independent of real data; (2) evaluation/tracking/evaluate.py
runs the REAL ByteTracker against this full scenario to report whatever
actually happens -- this codebase's only ID-switch-capable tracking
scenario, since the real-footage ground truth (ground_truth_real.py) has
exactly one object and can never produce a switch.

20 frames, two objects moving in straight lines at constant, equal-and-
opposite velocity, crossing paths at the frame range's midpoint -- a
classic, realistic "two people/vehicles crossing paths" scenario, and a
genuinely hard case for IoU-based association specifically because the
symmetric velocities make the two objects' Kalman-predicted next positions
converge right where the crossing happens.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

FRAME_COUNT = 20
BOX_WIDTH = 30.0
BOX_HEIGHT = 60.0
Y = 100.0
SPEED = 12.0  # pixels/frame

OBJECT_A_GT_ID = 1
OBJECT_B_GT_ID = 2


def _box(center_x: float) -> Tuple[float, float, float, float]:
    return (center_x - BOX_WIDTH / 2, Y, center_x + BOX_WIDTH / 2, Y + BOX_HEIGHT)


def object_a_center_x(frame_id: int) -> float:
    return 20.0 + SPEED * frame_id  # moving right


def object_b_center_x(frame_id: int) -> float:
    return 280.0 - SPEED * frame_id  # moving left -- crosses object A around the midpoint


def ground_truth(frame_count: int = FRAME_COUNT) -> Dict[int, List[Tuple[int, Tuple[float, float, float, float]]]]:
    """frame_id -> [(gt_id, bbox_xyxy), ...] -- both objects present every frame."""
    gt: Dict[int, List[Tuple[int, Tuple[float, float, float, float]]]] = {}
    for frame_id in range(frame_count):
        gt[frame_id] = [
            (OBJECT_A_GT_ID, _box(object_a_center_x(frame_id))),
            (OBJECT_B_GT_ID, _box(object_b_center_x(frame_id))),
        ]
    return gt
