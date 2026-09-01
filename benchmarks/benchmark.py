"""Phase 15 performance benchmarking harness -- Section 20 of the study
guide. Measures, for one detector backend, against the real pipeline
(`FrameSource` -> `YoloDetector` -> `ByteTracker`) on `data/sample.mp4`:

  - detection FPS / per-frame latency  (YoloDetector.detect() alone)
  - tracking FPS / per-frame latency   (ByteTracker.update() alone)
  - end-to-end FPS / per-frame latency (read -> detect -> update, full loop)
  - CPU usage (this process, sampled via psutil)
  - GPU memory (benchmarks/gpu_support.py -- real torch.cuda stats if a
    CUDA-enabled PyTorch build with a device is running this process, else
    an explicit "not measured, here's why" rather than a fabricated number)

The backend (PyTorch `.pt` vs ONNX `.onnx`) is never special-cased here:
Ultralytics' `YOLO(model_path)` dispatches on the file extension via its own
AutoBackend, so `YoloDetector` (src/detection/yolo_detector.py) already
handles both through the exact same code path this harness calls. Pass
whichever weights file you want measured via --model.

A fixed number of warmup frames run before any frame is timed, so
first-inference cold-start cost (backend session creation, buffer
allocation) doesn't bleed into the steady-state numbers.

Usage:
    python benchmarks/benchmark.py --model yolov8n.pt --label pytorch_pretrained
    python benchmarks/benchmark.py --model yolov8n.onnx --label onnx_pretrained
    python benchmarks/benchmark.py --model yolov8n.pt --warmup-frames 5 --max-frames 50
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from gpu_support import gpu_memory_status  # noqa: E402

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
DEFAULT_SOURCE_VIDEO = REPO_ROOT / "data" / "sample.mp4"


def _latency_stats(samples_seconds: list[float]) -> dict:
    ms = [s * 1000.0 for s in samples_seconds]
    return {
        "count": len(ms),
        "mean_ms": statistics.mean(ms),
        "median_ms": statistics.median(ms),
        "p95_ms": sorted(ms)[max(0, int(len(ms) * 0.95) - 1)],
        "min_ms": min(ms),
        "max_ms": max(ms),
    }


def run_benchmark(
    model_path: str,
    source_video: Path = DEFAULT_SOURCE_VIDEO,
    warmup_frames: int = 10,
    max_frames: int | None = None,
) -> dict:
    import psutil

    from detection.frame_source import FrameSource
    from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
    from tracking.byte_tracker import ByteTracker

    process = psutil.Process()

    detector = YoloDetector(model_path=model_path, confidence_threshold=0.25, class_allowlist=DEFAULT_CLASS_ALLOWLIST)
    tracker = ByteTracker()

    # Warmup: absorbs first-call cost (backend session/graph build,
    # allocator warm-up) so it doesn't skew the measured samples below.
    with FrameSource(str(source_video), source_id="warmup", frame_skip=1) as warmup_source:
        for _ in range(warmup_frames):
            frame = warmup_source.read()
            if frame is None:
                break
            detector.detect(frame)

    process.cpu_percent(interval=None)  # first call always returns 0.0; primes the internal counter
    cpu_start_time = time.perf_counter()

    detect_latencies: list[float] = []
    track_latencies: list[float] = []
    total_latencies: list[float] = []
    frames_processed = 0

    with FrameSource(str(source_video), source_id="benchmark", frame_skip=1) as source:
        while max_frames is None or frames_processed < max_frames:
            loop_start = time.perf_counter()
            frame = source.read()
            if frame is None:
                break

            t0 = time.perf_counter()
            detections = detector.detect(frame)
            t1 = time.perf_counter()
            tracker.update(detections)
            t2 = time.perf_counter()

            detect_latencies.append(t1 - t0)
            track_latencies.append(t2 - t1)
            total_latencies.append(t2 - loop_start)
            frames_processed += 1

    wall_elapsed = time.perf_counter() - cpu_start_time
    cpu_percent = process.cpu_percent(interval=None)

    def _fps(latencies: list[float]) -> float:
        return len(latencies) / sum(latencies) if latencies and sum(latencies) > 0 else 0.0

    return {
        "model_path": model_path,
        "source_video": str(source_video),
        "frames_processed": frames_processed,
        "warmup_frames": warmup_frames,
        "detection_fps": _fps(detect_latencies),
        "tracking_fps": _fps(track_latencies),
        "end_to_end_fps": frames_processed / wall_elapsed if wall_elapsed > 0 else 0.0,
        "detection_latency": _latency_stats(detect_latencies),
        "tracking_latency": _latency_stats(track_latencies),
        "end_to_end_latency": _latency_stats(total_latencies),
        "cpu_percent_process": cpu_percent,
        "wall_elapsed_seconds": wall_elapsed,
        "gpu_memory": gpu_memory_status(),
    }


def _format_report(label: str, result: dict) -> str:
    lines = [
        f"=== {label} ({result['model_path']}) ===",
        f"frames processed: {result['frames_processed']} (warmup: {result['warmup_frames']})",
        f"detection FPS:  {result['detection_fps']:.2f}   (mean {result['detection_latency']['mean_ms']:.2f} ms, p95 {result['detection_latency']['p95_ms']:.2f} ms)",
        f"tracking FPS:   {result['tracking_fps']:.2f}   (mean {result['tracking_latency']['mean_ms']:.2f} ms, p95 {result['tracking_latency']['p95_ms']:.2f} ms)",
        f"end-to-end FPS: {result['end_to_end_fps']:.2f}   (mean {result['end_to_end_latency']['mean_ms']:.2f} ms, p95 {result['end_to_end_latency']['p95_ms']:.2f} ms)",
        f"CPU (process):  {result['cpu_percent_process']:.1f}%",
        f"GPU memory:     {'measured' if result['gpu_memory']['measured'] else 'not measured -- ' + result['gpu_memory']['reason']}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True, help="Weights path -- .pt (PyTorch) or .onnx (ONNX Runtime).")
    parser.add_argument("--label", default=None, help="Result label (default: derived from --model).")
    parser.add_argument("--source-video", type=Path, default=DEFAULT_SOURCE_VIDEO)
    parser.add_argument("--warmup-frames", type=int, default=10)
    parser.add_argument("--max-frames", type=int, default=None, help="Cap frames processed (default: full clip).")
    args = parser.parse_args()

    label = args.label or Path(args.model).stem
    result = run_benchmark(
        model_path=args.model,
        source_video=args.source_video,
        warmup_frames=args.warmup_frames,
        max_frames=args.max_frames,
    )

    report = _format_report(label, result)
    print(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"{label}.json"
    txt_path = RESULTS_DIR / f"{label}.txt"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    txt_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nwritten: {json_path}, {txt_path}")


if __name__ == "__main__":
    main()
