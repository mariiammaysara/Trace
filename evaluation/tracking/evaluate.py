"""Section 15's tracking evaluation: MOTA / IDF1 / ID switches, via the real
`motmetrics` library (evaluation/tracking/metrics.py), against two
ground-truth sources that test different things:

1. REAL_FOOTAGE (ground_truth_real.py) -- data/sample.mp4, all 244 frames,
   one continuously-visible person. Run through the REAL pipeline
   (FrameSource -> YoloDetector -> ByteTracker) for the pretrained
   baseline AND both Phase 13 fine-tuned stages, so this evaluation is what
   makes Phase 13's detector comparison rigorous for tracking too, not just
   anecdotal. Tests whether the tracker holds one continuous id across a
   full real clip despite real detection noise (frame 241's duplicate
   detection, in particular) -- cannot exercise an ID switch (only one
   object ever present).
2. SYNTHETIC_CROSSING (ground_truth_synthetic.py) -- a controlled 2-object
   crossing scenario, detections = the exact ground-truth boxes (isolating
   tracker behavior from any detector noise), run once through the same
   ByteTracker. This is what CAN exercise a real ID switch, and is run
   once (not once per detector stage) since it deliberately has no
   detector in the loop.

Usage:
    python evaluation/tracking/evaluate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from evaluation.tracking import ground_truth_real, ground_truth_synthetic  # noqa: E402
from evaluation.tracking.metrics import compute_mot_metrics  # noqa: E402

RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

DETECTOR_WEIGHTS = {
    "pretrained": "yolov8n.pt",
    "stage1": str(REPO_ROOT / "models" / "yolov8n_trace_stage1.pt"),
    "stage2": str(REPO_ROOT / "models" / "yolov8n_trace_stage2.pt"),
}
SOURCE_VIDEO = REPO_ROOT / "data" / "sample.mp4"


def _run_tracker_on_video(weights_path: str) -> dict:
    """Runs FrameSource -> YoloDetector(weights_path) -> ByteTracker across
    the full real clip, returning frame_id -> [(track_id, bbox_xyxy), ...]
    in the same shape ground_truth_real.ground_truth() uses, so the two can
    be compared directly by compute_mot_metrics()."""
    from detection.frame_source import FrameSource
    from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
    from tracking.byte_tracker import ByteTracker

    detector = YoloDetector(model_path=weights_path, confidence_threshold=0.25, class_allowlist=DEFAULT_CLASS_ALLOWLIST)
    tracker = ByteTracker()
    source = FrameSource(str(SOURCE_VIDEO), source_id="sample", frame_skip=1)

    hyp_by_frame: dict = {}
    try:
        while True:
            frame = source.read()
            if frame is None:
                break
            detections = detector.detect(frame)
            tracks = tracker.update(detections)
            hyp_by_frame[frame.frame_id] = [(track.object_id, track.bbox) for track in tracks]
    finally:
        source.release()

    return hyp_by_frame


def evaluate_real_footage() -> dict:
    gt = ground_truth_real.ground_truth()
    results = {}
    for label, weights_path in DETECTOR_WEIGHTS.items():
        hyp = _run_tracker_on_video(weights_path)
        results[label] = compute_mot_metrics(gt, hyp, max_iou_distance=0.5)
    return {"ground_truth_frames": ground_truth_real.FRAME_COUNT, "weights": DETECTOR_WEIGHTS, "results": results}


def evaluate_synthetic_crossing() -> dict:
    from detection.detector import Detection
    from tracking.byte_tracker import ByteTracker

    gt = ground_truth_synthetic.ground_truth()
    tracker = ByteTracker()

    hyp_by_frame: dict = {}
    for frame_id in sorted(gt):
        detections = [
            Detection(bbox=box, class_name="synthetic", confidence=1.0, frame_id=frame_id, timestamp=float(frame_id))
            for _gt_id, box in gt[frame_id]
        ]
        tracks = tracker.update(detections)
        hyp_by_frame[frame_id] = [(track.object_id, track.bbox) for track in tracks]

    metrics = compute_mot_metrics(gt, hyp_by_frame, max_iou_distance=0.5)
    return {"ground_truth_frames": ground_truth_synthetic.FRAME_COUNT, "results": metrics}


def _format_report(real_footage: dict, synthetic: dict) -> str:
    lines = [
        f"=== REAL_FOOTAGE ({real_footage['ground_truth_frames']} frames, data/sample.mp4, person only) ===",
        f"{'model':<12} {'MOTA':>8} {'IDF1':>8} {'switches':>9} {'FP':>7} {'misses':>8} {'matches':>8}",
    ]
    for label, m in real_footage["results"].items():
        lines.append(
            f"{label:<12} {m['mota']:>8.3f} {m['idf1']:>8.3f} {int(m['num_switches']):>9} "
            f"{int(m['num_false_positives']):>7} {int(m['num_misses']):>8} {int(m['num_matches']):>8}"
        )

    m = synthetic["results"]
    lines += [
        "",
        f"=== SYNTHETIC_CROSSING ({synthetic['ground_truth_frames']} frames, 2 objects, real ByteTracker, no detector) ===",
        f"MOTA={m['mota']:.3f}  IDF1={m['idf1']:.3f}  switches={int(m['num_switches'])}  "
        f"FP={int(m['num_false_positives'])}  misses={int(m['num_misses'])}  matches={int(m['num_matches'])}",
    ]
    return "\n".join(lines)


def main() -> None:
    real_footage = evaluate_real_footage()
    synthetic = evaluate_synthetic_crossing()

    report = _format_report(real_footage, synthetic)
    print(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    combined = {"real_footage": real_footage, "synthetic_crossing": synthetic}
    (RESULTS_DIR / "tracking_comparison.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
    (RESULTS_DIR / "tracking_comparison.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\nwritten: {RESULTS_DIR / 'tracking_comparison.json'}, {RESULTS_DIR / 'tracking_comparison.txt'}")


if __name__ == "__main__":
    main()
