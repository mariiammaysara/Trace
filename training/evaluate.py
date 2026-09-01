"""Evaluate the pretrained baseline AND the fine-tuned checkpoint on the
SAME held-out val split (training/dataset.yaml's val:, built by
prepare_dataset.py -- images neither model was trained on: the pretrained
baseline was never trained on any of this data, and the fine-tuned model
only ever saw train.txt's images during training/train.py's run), and
report both side by side. Never reports the fine-tuned result alone.

Per-class precision/recall/mAP50/mAP50-95 come straight from Ultralytics'
own `DetMetrics.summary()` (ultralytics.utils.metrics) -- not recomputed by
hand -- filtered down to TRACE's 6 target classes
(src/detection/yolo_detector.py's DEFAULT_CLASS_ALLOWLIST).

Usage:
    python training/evaluate.py                                    # baseline vs models/yolov8n_trace_finetuned.pt
    python training/evaluate.py --finetuned path/to/other.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = REPO_ROOT / "training"
DATASET_PATH = TRAINING_DIR / "dataset.yaml"
DEFAULT_FINETUNED_PATH = REPO_ROOT / "models" / "yolov8n_trace_finetuned.pt"
DEFAULT_BASELINE_PATH = "yolov8n.pt"
RESULTS_DIR = TRAINING_DIR / "results"
RUNS_DIR = TRAINING_DIR / "runs"

# Section 2's DEFAULT_CLASS_ALLOWLIST, i.e. TRACE's actual target classes.
TARGET_CLASSES = ("person", "car", "motorcycle", "bus", "truck", "bicycle")


def evaluate_one(weights_path: str, label: str) -> list[dict]:
    """Runs model.val() against training/dataset.yaml's held-out val split
    and returns per-class metric dicts for TRACE's target classes only."""
    from ultralytics import YOLO

    model = YOLO(weights_path)
    results = model.val(
        data=str(DATASET_PATH), split="val", verbose=False, project=str(RUNS_DIR / "detect"), name=f"val_{label}", exist_ok=True
    )
    summary = results.summary()
    rows = [row for row in summary if row["Class"] in TARGET_CLASSES]
    for row in rows:
        row["model"] = label
    return rows


def build_comparison(baseline_path: str, finetuned_path: str) -> dict:
    baseline_rows = evaluate_one(baseline_path, "pretrained")
    finetuned_rows = evaluate_one(finetuned_path, "finetuned")

    by_class: dict[str, dict] = {}
    for row in baseline_rows:
        by_class.setdefault(row["Class"], {})["pretrained"] = row
    for row in finetuned_rows:
        by_class.setdefault(row["Class"], {})["finetuned"] = row

    return {
        "baseline_weights": baseline_path,
        "finetuned_weights": finetuned_path,
        "dataset": str(DATASET_PATH),
        "per_class": by_class,
    }


def _format_report(comparison: dict) -> str:
    lines = [
        f"baseline:  {comparison['baseline_weights']}",
        f"finetuned: {comparison['finetuned_weights']}",
        f"dataset:   {comparison['dataset']}",
        "",
        f"{'class':<12} {'model':<10} {'images':>7} {'instances':>10} {'P':>7} {'R':>7} {'mAP50':>7} {'mAP50-95':>9}",
    ]
    for class_name in TARGET_CLASSES:
        rows = comparison["per_class"].get(class_name, {})
        for model_label in ("pretrained", "finetuned"):
            row = rows.get(model_label)
            if row is None:
                lines.append(f"{class_name:<12} {model_label:<10} {'no val instances of this class':>45}")
                continue
            lines.append(
                f"{class_name:<12} {model_label:<10} {row['Images']:>7} {row['Instances']:>10} "
                f"{row['Box-P']:>7.3f} {row['Box-R']:>7.3f} {row['mAP50']:>7.3f} {row['mAP50-95']:>9.3f}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--finetuned", default=str(DEFAULT_FINETUNED_PATH))
    args = parser.parse_args()

    comparison = build_comparison(args.baseline, args.finetuned)
    report = _format_report(comparison)
    print(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # Ultralytics' summary() returns numpy scalars (int64/float64) for the
    # per-class counts/metrics -- .item() converts whichever of those show up
    # to a native Python type so json.dumps doesn't choke on them.
    def _json_default(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    (RESULTS_DIR / "comparison.json").write_text(json.dumps(comparison, indent=2, default=_json_default), encoding="utf-8")
    (RESULTS_DIR / "comparison.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\nwritten: {RESULTS_DIR / 'comparison.json'}, {RESULTS_DIR / 'comparison.txt'}")


if __name__ == "__main__":
    main()
