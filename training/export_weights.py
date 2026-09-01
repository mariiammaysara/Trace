"""Export a fine-tuned checkpoint into the format/location Phase 2's
Detector interface expects -- the "export" step, kept separate from
training per this phase's explicit requirement. Shared by both stages
(--stage 1 or --stage 2), since the logic is identical either way.

There's no format conversion here: Ultralytics' training output (best.pt)
is already a plain `.pt` checkpoint, exactly what `YoloDetector(model_path=...)`
loads directly (src/detection/yolo_detector.py just passes model_path
straight to `ultralytics.YOLO(model_path)`). What actually needs "exporting"
is location and stability: `training/runs/detect/<run_name>/weights/best.pt`
lives inside Ultralytics' own ephemeral, gitignored run output (a fresh
directory per run), which is not somewhere the rest of the codebase should
ever hardcode a path into. This script copies best.pt to a fixed,
documented, gitignored path under models/ that YoloDetector/DEFAULT_MODEL_PATH
can reference by name -- models/yolov8n_trace_stage1.pt or
models/yolov8n_trace_stage2.pt.

Usage:
    python training/export_weights.py --stage 1
    python training/export_weights.py --stage 2
    python training/export_weights.py --run-dir training/runs/detect/some_other_run --export-path models/custom.pt
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = REPO_ROOT / "training"

STAGE_RUN_NAMES = {1: "stage1_finetune", 2: "stage2_finetune"}
STAGE_EXPORT_NAMES = {1: "yolov8n_trace_stage1.pt", 2: "yolov8n_trace_stage2.pt"}


def export(run_dir: Path, export_path: Path) -> Path:
    best_weights = run_dir / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"no checkpoint at {best_weights} -- run the matching stage's train.py first.")

    export_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, export_path)
    return export_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=[1, 2], help="Export the standard run/export path for this stage.")
    parser.add_argument("--run-dir", type=Path, help="Override: training run directory containing weights/best.pt.")
    parser.add_argument("--export-path", type=Path, help="Override: where to copy the checkpoint to.")
    args = parser.parse_args()

    if args.stage is None and (args.run_dir is None or args.export_path is None):
        parser.error("pass --stage 1|2, or both --run-dir and --export-path explicitly")

    run_dir = args.run_dir or (TRAINING_DIR / "runs" / "detect" / STAGE_RUN_NAMES[args.stage])
    export_path = args.export_path or (REPO_ROOT / "models" / STAGE_EXPORT_NAMES[args.stage])

    result_path = export(run_dir, export_path)
    print(f"exported: {result_path}")


if __name__ == "__main__":
    main()
