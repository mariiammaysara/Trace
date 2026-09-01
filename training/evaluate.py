"""Evaluate the pretrained baseline, Stage 1, and Stage 2 -- and report all
three side by side, never just whichever came out best. Two separate
held-out comparisons, because they answer two different questions:

  1. COCO_HOLDOUT: pretrained vs Stage 1, on Stage 1's held-out COCO128
     val split (6 classes). Answers "did narrowing to TRACE's classes on
     generic COCO imagery help on more generic COCO imagery?"
  2. REAL_FOOTAGE_HOLDOUT: pretrained vs Stage 1 vs Stage 2, on Stage 2's
     held-out real-footage val split (person only -- data/sample.mp4 is
     confirmed person-only, see stage2/apply_review.py). Answers the
     question this whole two-stage design exists to answer: did Stage 2's
     domain adaptation help on TRACE's actual deployment conditions, over
     and above Stage 1 alone?

A real cross-class-space problem, found and fixed while building this: the
pretrained baseline is an 80-class COCO model (class index 2 = "car"), but
Stage 1/2 are genuinely narrowed to TRACE's 6 classes (class index 1 =
"car"). Ultralytics' evaluator matches predictions to ground truth by
INTEGER class index, not by name -- pointing the pretrained model directly
at a 6-class dataset.yaml would silently compare index 2 (baseline's "car")
against whatever index 2 means in the 6-class scheme (motorcycle),
producing a meaningless number that looks like a real metric. Fixed for
COCO_HOLDOUT by evaluating the baseline against a separate, auto-built
dataset.yaml using the SAME held-out val images through their ORIGINAL
coco128 path/80-class labels (stage1/prepare_dataset.py's
val_original_coco_paths.txt). Not needed for REAL_FOOTAGE_HOLDOUT: person
is class 0 in BOTH COCO's and TRACE's class order, so stage2/dataset.yaml's
labels are already valid ground truth for the pretrained model too --
verified, not assumed (mAP for "person" from all three models here is a
real, safe comparison). Either way, results are only ever compared by
CLASS NAME afterward (Ultralytics' DetMetrics.summary() keys its per-class
rows by name already, which is what makes this safe).

Usage:
    python training/evaluate.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = REPO_ROOT / "training"
STAGE1_DIR = TRAINING_DIR / "stage1"
STAGE2_DIR = TRAINING_DIR / "stage2"
STAGE1_SPLIT_DIR = STAGE1_DIR.parent / "data" / "stage1" / "split"
RESULTS_DIR = TRAINING_DIR / "results"
TMP_DIR = TRAINING_DIR / "data" / "eval_tmp"

DEFAULT_BASELINE_PATH = "yolov8n.pt"
DEFAULT_STAGE1_PATH = REPO_ROOT / "models" / "yolov8n_trace_stage1.pt"
DEFAULT_STAGE2_PATH = REPO_ROOT / "models" / "yolov8n_trace_stage2.pt"

# Section 2's DEFAULT_CLASS_ALLOWLIST, i.e. TRACE's actual target classes.
TARGET_CLASSES = ("person", "car", "motorcycle", "bus", "truck", "bicycle")


def _build_baseline_coco_dataset_yaml() -> Path:
    """Auto-builds a dataset.yaml for evaluating the 80-class pretrained
    model against the SAME held-out COCO val images Stage 1 is evaluated
    on, through their original coco128 path/label space. See this module's
    docstring."""
    from ultralytics.data.utils import check_det_dataset

    coco128 = check_det_dataset("coco128.yaml")
    val_list = STAGE1_SPLIT_DIR / "val_original_coco_paths.txt"
    if not val_list.exists():
        raise FileNotFoundError(f"{val_list} missing -- run `python training/stage1/prepare_dataset.py` first.")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    names_block = "\n".join(f"  {class_id}: {name}" for class_id, name in coco128["names"].items())
    dataset_yaml = TMP_DIR / "baseline_coco_dataset.yaml"
    dataset_yaml.write_text(f"train: {val_list}\nval: {val_list}\nnames:\n{names_block}\n", encoding="utf-8")
    return dataset_yaml


def evaluate_one(weights_path: str, dataset_yaml: Path, label: str) -> list[dict]:
    """Runs model.val() against the given dataset config and returns
    per-class metric dicts for TRACE's target classes only."""
    from ultralytics import YOLO

    model = YOLO(weights_path)
    results = model.val(
        data=str(dataset_yaml), split="val", verbose=False, project=str(TRAINING_DIR / "runs" / "detect"),
        name=f"val_{label}", exist_ok=True,
    )
    summary = results.summary()
    rows = [row for row in summary if row["Class"] in TARGET_CLASSES]
    for row in rows:
        row["model"] = label
    return rows


def _run_models(models: list[tuple[str, str, Path]]) -> dict:
    by_class: dict[str, dict] = {}
    weights_used = {}
    for label, weights_path, dataset_yaml in models:
        weights_used[label] = weights_path
        for row in evaluate_one(weights_path, dataset_yaml, label):
            by_class.setdefault(row["Class"], {})[label] = row
    return {"weights": weights_used, "per_class": by_class}


def build_coco_holdout_comparison() -> dict:
    baseline_dataset_yaml = _build_baseline_coco_dataset_yaml()
    return _run_models(
        [
            ("pretrained", DEFAULT_BASELINE_PATH, baseline_dataset_yaml),
            ("stage1", str(DEFAULT_STAGE1_PATH), STAGE1_DIR / "dataset.yaml"),
        ]
    )


def build_real_footage_holdout_comparison() -> dict:
    real_footage_dataset_yaml = STAGE2_DIR / "dataset.yaml"
    return _run_models(
        [
            ("pretrained", DEFAULT_BASELINE_PATH, real_footage_dataset_yaml),
            ("stage1", str(DEFAULT_STAGE1_PATH), real_footage_dataset_yaml),
            ("stage2", str(DEFAULT_STAGE2_PATH), real_footage_dataset_yaml),
        ]
    )


def _format_table(comparison: dict) -> str:
    lines = [f"{label}: {weights}" for label, weights in comparison["weights"].items()]
    lines += [
        "",
        f"{'class':<12} {'model':<10} {'images':>7} {'instances':>10} {'P':>7} {'R':>7} {'mAP50':>7} {'mAP50-95':>9}",
    ]
    model_labels = list(comparison["weights"].keys())
    for class_name in TARGET_CLASSES:
        rows = comparison["per_class"].get(class_name, {})
        if not rows:
            continue
        for model_label in model_labels:
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
    parser.parse_args()

    coco_holdout = build_coco_holdout_comparison()
    real_footage_holdout = build_real_footage_holdout_comparison()

    report = (
        "=== COCO_HOLDOUT: pretrained vs Stage 1 (held-out COCO128 val, 6 classes) ===\n"
        + _format_table(coco_holdout)
        + "\n\n=== REAL_FOOTAGE_HOLDOUT: pretrained vs Stage 1 vs Stage 2 (held-out data/sample.mp4 frames, person only) ===\n"
        + _format_table(real_footage_holdout)
    )
    print(report)

    def _json_default(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    combined = {"coco_holdout": coco_holdout, "real_footage_holdout": real_footage_holdout}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "comparison.json").write_text(json.dumps(combined, indent=2, default=_json_default), encoding="utf-8")
    (RESULTS_DIR / "comparison.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\nwritten: {RESULTS_DIR / 'comparison.json'}, {RESULTS_DIR / 'comparison.txt'}")


if __name__ == "__main__":
    main()
