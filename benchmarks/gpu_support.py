"""Real, no-guessing GPU / CUDA / TensorRT capability probe -- shared by
benchmark.py (the GPU-memory metric) and export_tensorrt.py (the export
skip logic). Nothing here is a hardcoded skip: both callers act on what
these functions actually detect on the machine they're running on.

Two genuinely different facts, checked independently and never conflated
into one another:

  - a physical NVIDIA GPU being present, via `nvidia-smi` -- this talks to
    the driver directly and is true regardless of what PyTorch was built
    with.
  - `torch.cuda.is_available()` -- whether the PyTorch build actually
    *installed in this environment* has CUDA support compiled in.

On the machine this was built on, the two disagree: `nvidia-smi` finds a
real GPU, but the installed `torch` is a CPU-only wheel, so
`torch.cuda.is_available()` is False. That is a software-stack limitation,
not an absence of hardware -- report it precisely, never as a blanket
"no GPU".
"""

from __future__ import annotations

import shutil
import subprocess


def nvidia_smi_gpu_name() -> str | None:
    """The real physical GPU name via `nvidia-smi`, or None if no NVIDIA driver
    responds. Independent of the installed PyTorch build."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().splitlines()[0].strip()


def torch_cuda_status() -> dict:
    import torch

    return {
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }


def tensorrt_availability() -> dict:
    """Whether this environment can actually run a TensorRT export/inference,
    checked directly rather than assumed. Ultralytics' TensorRT ("engine")
    export builds the engine on-device, so it needs BOTH the `tensorrt`
    Python package installed AND a CUDA-enabled PyTorch build with a visible
    device -- each is checked independently so the reported reason names the
    actual missing piece(s), not a generic "unsupported"."""
    reasons: list[str] = []

    try:
        import tensorrt  # noqa: F401

        has_tensorrt_package = True
    except ImportError:
        has_tensorrt_package = False
        reasons.append("the `tensorrt` Python package is not installed")

    cuda = torch_cuda_status()
    if not cuda["cuda_available"]:
        reasons.append(
            f"torch.cuda.is_available() is False (installed PyTorch is {cuda['torch_version']}, a CPU-only build)"
        )

    gpu_name = nvidia_smi_gpu_name()
    supported = has_tensorrt_package and cuda["cuda_available"]

    return {
        "supported": supported,
        "has_tensorrt_package": has_tensorrt_package,
        "torch_cuda_available": cuda["cuda_available"],
        "torch_version": cuda["torch_version"],
        "physical_gpu_detected": gpu_name,
        "reasons_unsupported": reasons,
    }


def gpu_memory_status() -> dict:
    """GPU memory usage for the current process, only if PyTorch itself can see
    a CUDA device -- there is nothing meaningful to report otherwise (an
    ONNX Runtime CPU session, or PyTorch running on CPU, never allocates
    GPU memory)."""
    cuda = torch_cuda_status()
    if not cuda["cuda_available"]:
        return {
            "measured": False,
            "reason": (
                f"torch.cuda.is_available() is False (installed PyTorch is {cuda['torch_version']}, "
                f"a CPU-only build) -- no CUDA device for this process to allocate GPU memory on"
            ),
            "physical_gpu_detected": nvidia_smi_gpu_name(),
        }

    import torch

    return {
        "measured": True,
        "allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
        "reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
        "max_allocated_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
    }


if __name__ == "__main__":
    import json

    print(json.dumps({"tensorrt": tensorrt_availability(), "gpu_memory": gpu_memory_status()}, indent=2))
