"""Section 15's detection evaluation: precision, recall, mAP50, mAP50-95,
pretrained vs. Stage 1 vs. Stage 2 (Phase 13). Deliberately NOT a
reimplementation -- this reuses Phase 13's own held-out splits and
Ultralytics-based evaluation functions directly (training/evaluate.py's
build_coco_holdout_comparison/build_real_footage_holdout_comparison), since
Section 15's requirement is explicitly to formalize/re-run that comparison
as this phase's own evaluation artifact, not to duplicate the logic.

Usage:
    python evaluation/detection/evaluate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "training"))

import evaluate as training_evaluate  # noqa: E402

RESULTS_DIR = REPO_ROOT / "evaluation" / "results"


def main() -> None:
    coco_holdout = training_evaluate.build_coco_holdout_comparison()
    real_footage_holdout = training_evaluate.build_real_footage_holdout_comparison()

    report = (
        "=== COCO_HOLDOUT: pretrained vs Stage 1 (held-out COCO128 val, 6 classes) ===\n"
        + training_evaluate._format_table(coco_holdout)
        + "\n\n=== REAL_FOOTAGE_HOLDOUT: pretrained vs Stage 1 vs Stage 2 (held-out data/sample.mp4 frames, person only) ===\n"
        + training_evaluate._format_table(real_footage_holdout)
    )
    print(report)

    def _json_default(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    combined = {"coco_holdout": coco_holdout, "real_footage_holdout": real_footage_holdout}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "detection_comparison.json").write_text(json.dumps(combined, indent=2, default=_json_default), encoding="utf-8")
    (RESULTS_DIR / "detection_comparison.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\nwritten: {RESULTS_DIR / 'detection_comparison.json'}, {RESULTS_DIR / 'detection_comparison.txt'}")


if __name__ == "__main__":
    main()
