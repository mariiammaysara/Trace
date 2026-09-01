"""Verifies evaluation/tracking/metrics.py's compute_mot_metrics() against
small, hand-derivable scenarios with a KNOWN expected MOTA/IDF1 -- so the
metric computation itself (the motmetrics wiring, the xyxy->xywh
conversion, the numpy shim) is verified independent of whatever real data
Section 15 ends up reporting numbers from.

Each expected value below was independently hand-derived from MOTA/IDF1's
own definitions (not just copied from a first run's output) and then cross-
checked directly against `motmetrics` in isolation while building this --
see the comment on each test for the derivation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.tracking.metrics import compute_mot_metrics  # noqa: E402

BOX = (0.0, 0.0, 10.0, 10.0)  # a fixed, perfectly-overlapping box for every entry below


def test_perfect_tracking_scores_mota_and_idf1_at_one():
    # 3 frames, 1 GT object (id 1), 1 hypothesis that keeps the same id (100)
    # and a perfect box every frame: 0 misses, 0 FPs, 0 switches.
    # MOTA = 1 - (FN+FP+IDSW)/GT = 1 - 0/3 = 1.0. IDF1 = 1.0 (perfect ID match).
    gt = {frame: [(1, BOX)] for frame in range(3)}
    hyp = {frame: [(100, BOX)] for frame in range(3)}

    metrics = compute_mot_metrics(gt, hyp)

    assert metrics["mota"] == 1.0
    assert metrics["idf1"] == 1.0
    assert metrics["num_switches"] == 0


def test_a_single_id_switch_with_otherwise_perfect_boxes():
    # 3 frames, 1 GT object (id 1), perfect box match every frame, but the
    # hypothesis id changes from 100 to 200 between frame 2 and frame 3 --
    # a pure ID switch, no detection error at all.
    #
    # MOTA: 3 GT boxes total, all 3 spatially matched (IoU=1.0) -> FN=0,
    # FP=0. The id change while continuously matched to the same GT track
    # counts as exactly 1 IDSW. MOTA = 1 - (0+0+1)/3 = 0.6667.
    #
    # IDF1: the optimal single GT-track<->pred-track pairing is GT-1<->id100
    # (matched in 2 of 3 frames) -> IDTP=2. IDFN = 3(total GT)-2 = 1.
    # IDFP = 3(total hyp)-2 = 1. IDF1 = 2*2/(2*2+1+1) = 4/6 = 0.6667.
    gt = {frame: [(1, BOX)] for frame in range(3)}
    hyp = {0: [(100, BOX)], 1: [(100, BOX)], 2: [(200, BOX)]}

    metrics = compute_mot_metrics(gt, hyp)

    assert round(metrics["mota"], 4) == round(2 / 3, 4)
    assert round(metrics["idf1"], 4) == round(2 / 3, 4)
    assert metrics["num_switches"] == 1


def test_a_missed_detection_with_no_switch():
    # 2 frames, 1 GT object. Frame 0: no hypothesis at all (a miss). Frame 1:
    # a perfect match under a fresh id (100) -- no prior id to switch FROM,
    # so this is a miss, not a switch.
    #
    # MOTA: FN=1 (frame 0's miss), FP=0, IDSW=0. MOTA = 1 - 1/2 = 0.5.
    # IDF1: IDTP=1 (frame 1), IDFN = 2(total GT)-1 = 1, IDFP = 1(total hyp)-1 = 0.
    # IDF1 = 2*1/(2*1+0+1) = 2/3 = 0.6667.
    gt = {0: [(1, BOX)], 1: [(1, BOX)]}
    hyp = {0: [], 1: [(100, BOX)]}

    metrics = compute_mot_metrics(gt, hyp)

    assert metrics["mota"] == 0.5
    assert round(metrics["idf1"], 4) == round(2 / 3, 4)
    assert metrics["num_switches"] == 0
    assert metrics["num_misses"] == 1


def test_synthetic_crossing_scenario_runs_end_to_end_through_the_real_tracker():
    # Not an accuracy assertion -- whether ByteTrack switches ids at the
    # crossing is a real, reported result (evaluation/tracking/evaluate.py),
    # not something to assert here. This only confirms the harness's
    # detection->tracker->metrics pipeline runs without crashing on the
    # actual synthetic scenario evaluate.py uses for real.
    from evaluation.tracking import ground_truth_synthetic
    from detection.detector import Detection
    from tracking.byte_tracker import ByteTracker

    gt = ground_truth_synthetic.ground_truth(frame_count=10)
    tracker = ByteTracker()
    hyp = {}
    for frame_id in sorted(gt):
        detections = [
            Detection(bbox=box, class_name="synthetic", confidence=1.0, frame_id=frame_id, timestamp=float(frame_id))
            for _gt_id, box in gt[frame_id]
        ]
        tracks = tracker.update(detections)
        hyp[frame_id] = [(t.object_id, t.bbox) for t in tracks]

    metrics = compute_mot_metrics(gt, hyp)

    assert 0.0 <= metrics["mota"] <= 1.0
    assert 0.0 <= metrics["idf1"] <= 1.0
    assert metrics["num_switches"] >= 0
