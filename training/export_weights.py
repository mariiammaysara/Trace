"""Export the fine-tuned checkpoint into the format/location Phase 2's
Detector interface expects -- the "export" step, kept separate from
training (train.py) per this phase's explicit requirement.

There's no format conversion here: Ultralytics' training output (best.pt)
is already a plain `.pt` checkpoint, exactly what `YoloDetector(model_path=...)`
loads directly (src/detection/yolo_detector.py just passes model_path
straight to `ultralytics.YOLO(model_path)`). What actually needs "exporting"
is location and stability: `training/runs/detect/<run_name>/weights/best.pt`
lives inside Ultralytics' own ephemeral, gitignored run output (a fresh
directory per run), which is not somewhere the rest of the codebase should
ever hardcode a path into. This script copies best.pt to a fixed,
documented, gitignored path under models/ that YoloDetector/DEFAULT_MODEL_PATH
can reference by name.

Usage:
    python training/export_weights.py
    python training/export_weights.py --run-dir training/runs/detect/trace_finetune
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = REPO_ROOT / "training"
DEFAULT_RUN_DIR = TRAINING_DIR / "runs" / "detect" / "trace_finetune"
EXPORT_PATH = REPO_ROOT / "models" / "yolov8n_trace_finetuned.pt"


def export(run_dir: Path, export_path: Path = EXPORT_PATH) -> Path:
    best_weights = run_dir / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"no checkpoint at {best_weights} -- run `python training/train.py` first.")

    export_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, export_path)
    return export_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR, help="training run directory containing weights/best.pt")
    parser.add_argument("--export-path", type=Path, default=EXPORT_PATH, help="where to copy the checkpoint to")
    args = parser.parse_args()

    export_path = export(args.run_dir, args.export_path)
    print(f"exported: {export_path}")


if __name__ == "__main__":
    main()
