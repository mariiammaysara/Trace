"""Confirms benchmarks/benchmark.py runs the real pipeline end-to-end and
produces a well-formed results file -- NOT that any specific FPS/latency
number is hit, since those are hardware-dependent (Section 20 records the
actual measured numbers separately, as real evidence, not as a test
assertion).

Uses the tiny synthetic fixture video (tests/conftest.py's sample_video_path,
15 frames, 64x64) rather than data/sample.mp4, and caps at 3 frames with a
single warmup frame, so this stays a fast structural smoke test, not a
second full benchmark run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

from benchmarks.benchmark import run_benchmark  # noqa: E402
from benchmarks.gpu_support import tensorrt_availability  # noqa: E402


def test_run_benchmark_produces_well_formed_metrics(sample_video_path):
    result = run_benchmark(
        model_path="yolov8n.pt",
        source_video=sample_video_path,
        warmup_frames=1,
        max_frames=3,
    )

    assert result["frames_processed"] == 3
    for fps_key in ("detection_fps", "tracking_fps", "end_to_end_fps"):
        assert result[fps_key] > 0

    for latency_key in ("detection_latency", "tracking_latency", "end_to_end_latency"):
        stats = result[latency_key]
        assert stats["count"] == 3
        assert stats["mean_ms"] >= 0
        assert stats["min_ms"] <= stats["median_ms"] <= stats["max_ms"]

    assert result["cpu_percent_process"] >= 0
    assert "measured" in result["gpu_memory"]


def test_run_benchmark_writes_results_files(tmp_path, sample_video_path, monkeypatch):
    import benchmarks.benchmark as benchmark_module

    result_label = "test_smoke_run"
    monkeypatch.setattr(benchmark_module, "RESULTS_DIR", tmp_path)

    result = run_benchmark(model_path="yolov8n.pt", source_video=sample_video_path, warmup_frames=1, max_frames=3)
    report = benchmark_module._format_report(result_label, result)

    import json

    json_path = tmp_path / f"{result_label}.json"
    txt_path = tmp_path / f"{result_label}.txt"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    txt_path.write_text(report + "\n", encoding="utf-8")

    assert json_path.exists()
    assert txt_path.exists()
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["frames_processed"] == 3


def test_tensorrt_availability_reports_a_real_reason_when_unsupported():
    """Doesn't assert TensorRT IS or ISN'T supported (hardware-dependent) --
    only that the detection is real: whichever way it comes out, the
    reported fields are internally consistent, not a hardcoded stub."""
    status = tensorrt_availability()

    assert isinstance(status["supported"], bool)
    if not status["supported"]:
        assert len(status["reasons_unsupported"]) > 0
    else:
        assert status["reasons_unsupported"] == []
        assert status["has_tensorrt_package"] is True
        assert status["torch_cuda_available"] is True
