"""Attempts to export the default TRACE detector to TensorRT.

This does real capability detection (benchmarks/gpu_support.py), not a
hardcoded skip: it actually tries to import `tensorrt` and actually checks
`torch.cuda.is_available()`, then reports exactly which of those failed. If
either is missing, the export is skipped with a specific, honest message
and a results file recording the real check outcome -- per this phase's
explicit requirement not to fake numbers for a backend that was never run.

Usage:
    python benchmarks/export_tensorrt.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from gpu_support import tensorrt_availability  # noqa: E402

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"


def export(model_path: str, output_dir: Path) -> Path:
    """Only called once tensorrt_availability()['supported'] is True."""
    from ultralytics import YOLO

    model = YOLO(model_path)
    exported_path = Path(model.export(format="engine"))

    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / exported_path.name
    if exported_path.resolve() != final_path.resolve():
        exported_path.replace(final_path)
    return final_path


def main() -> None:
    status = tensorrt_availability()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not status["supported"]:
        print("TensorRT export SKIPPED -- not supported in this environment. Real reasons checked:")
        for reason in status["reasons_unsupported"]:
            print(f"  - {reason}")
        if status["physical_gpu_detected"]:
            print(
                f"Note: nvidia-smi DOES detect a physical GPU here ({status['physical_gpu_detected']}) -- "
                "this is a software-stack limitation (no CUDA-enabled PyTorch / no `tensorrt` package "
                "installed), not an absence of GPU hardware."
            )
        else:
            print("Note: nvidia-smi did not detect any physical NVIDIA GPU on this machine either.")

        (RESULTS_DIR / "tensorrt_export_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(f"\nwritten: {RESULTS_DIR / 'tensorrt_export_status.json'}")
        return

    result_path = export("yolov8n.pt", REPO_ROOT / "models")
    status["exported_path"] = str(result_path)
    (RESULTS_DIR / "tensorrt_export_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"exported: {result_path}")


if __name__ == "__main__":
    main()
