"""MOTA / IDF1 / ID-switch computation via the real `motmetrics` library --
never hand-rolled metric math, per this phase's explicit requirement.

A real, necessary compatibility fix, found while building this: motmetrics
1.4.0 (the latest release on PyPI at the time this was written) calls the
long-removed `numpy.asfarray` internally (motmetrics/distances.py's
`iou_matrix`) -- removed in NumPy 2.0; this environment has NumPy 2.4.6.
Restoring `asfarray`'s exact old behavior (`np.asarray(a, dtype=float)`) is
a minimal, targeted shim -- not a workaround that avoids using the real
library, and not a NumPy downgrade, which every other part of this codebase
(opencv, torch, ultralytics) also depends on and which risked a much wider
blast radius.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

if not hasattr(np, "asfarray"):
    np.asfarray = lambda a, dtype=float: np.asarray(a, dtype=dtype)  # type: ignore[attr-defined]

import motmetrics as mm  # noqa: E402 -- must be imported after the shim above

BBoxXYXY = Tuple[float, float, float, float]
FrameEntries = List[Tuple[int, BBoxXYXY]]

METRIC_NAMES = ["mota", "idf1", "num_switches", "num_false_positives", "num_misses", "num_matches"]


def _xyxy_to_xywh(box: BBoxXYXY) -> List[float]:
    x_min, y_min, x_max, y_max = box
    return [x_min, y_min, x_max - x_min, y_max - y_min]


def compute_mot_metrics(
    gt_by_frame: Dict[int, FrameEntries],
    hyp_by_frame: Dict[int, FrameEntries],
    max_iou_distance: float = 0.5,
) -> Dict[str, float]:
    """gt_by_frame / hyp_by_frame: frame_id -> [(object_id, bbox_xyxy), ...].

    Every frame_id present in EITHER dict is stepped through, in sorted
    order, even if the other side has no entries for that frame (a real
    miss or false positive, not silently skipped). `max_iou_distance` is
    motmetrics' own "maximum tolerable overlap distance" (1 - IoU) -- 0.5
    is the standard MOT-benchmark IoU>=0.5-to-match threshold.

    Returns real values straight from motmetrics' own MOTAccumulator +
    metrics host -- mota, idf1, num_switches, num_false_positives,
    num_misses, num_matches -- nothing recomputed by hand here.
    """
    acc = mm.MOTAccumulator(auto_id=True)
    all_frames = sorted(set(gt_by_frame) | set(hyp_by_frame))

    for frame_id in all_frames:
        gt_entries = gt_by_frame.get(frame_id, [])
        hyp_entries = hyp_by_frame.get(frame_id, [])
        gt_ids = [object_id for object_id, _ in gt_entries]
        hyp_ids = [object_id for object_id, _ in hyp_entries]
        gt_boxes = np.array([_xyxy_to_xywh(box) for _, box in gt_entries]) if gt_entries else np.empty((0, 4))
        hyp_boxes = np.array([_xyxy_to_xywh(box) for _, box in hyp_entries]) if hyp_entries else np.empty((0, 4))
        distances = mm.distances.iou_matrix(gt_boxes, hyp_boxes, max_iou=max_iou_distance)
        acc.update(gt_ids, hyp_ids, distances)

    metrics_host = mm.metrics.create()
    summary = metrics_host.compute(acc, metrics=METRIC_NAMES, name="eval")
    row = summary.to_dict("records")[0]
    return {key: float(value) for key, value in row.items()}
