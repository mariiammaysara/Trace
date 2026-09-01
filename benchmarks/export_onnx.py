"""Exports the default TRACE detector to ONNX via Ultralytics' own export
path (no hand-rolled conversion). Defaults to `yolov8n.pt` -- the pretrained
baseline Phase 13 kept as `DEFAULT_MODEL_PATH` after Stage 1/2 fine-tuning
collapsed (src/detection/yolo_detector.py, TRACE_STUDY_GUIDE.md Section 2)
-- since that's the model Section 20's benchmark actually runs.

The exported .onnx file can be pointed at directly by YoloDetector
(`YoloDetector(model_path="yolov8n.onnx")`): Ultralytics dispatches on file
extension via its own AutoBackend, so no separate ONNX-specific detector
code was needed anywhere in src/.

Usage:
    python benchmarks/export_onnx.py
    python benchmarks/export_onnx.py --model yolov8n.pt --output-dir models
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def export(model_path: str, output_dir: Path) -> Path:
    from ultralytics import YOLO

    model = YOLO(model_path)
    exported_path = Path(model.export(format="onnx"))

    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / exported_path.name
    if exported_path.resolve() != final_path.resolve():
        exported_path.replace(final_path)
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="yolov8n.pt", help="Source weights to export (default: yolov8n.pt).")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "models", help="Where to place the .onnx file.")
    args = parser.parse_args()

    result = export(args.model, args.output_dir)
    print(f"exported: {result}")


if __name__ == "__main__":
    main()
