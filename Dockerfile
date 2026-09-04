FROM python:3.11-slim

# opencv-python (not the headless variant -- kept as-is so local dev's
# `--display` flags on scripts/*.py still work outside the container) needs
# libGL/libglib at import time even though this image never opens a
# display; these two packages are what every "cv2 ImportError: libGL.so.1"
# report traces back to.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Installed BEFORE the package itself, and from PyTorch's own CPU wheel
# index, deliberately: ultralytics' plain PyPI resolution otherwise pulls
# PyTorch's full CUDA-enabled Linux build -- multiple GB of `nvidia-cu13-*`
# dependencies (cuDNN, cuBLAS, NCCL, Triton, the whole CUDA toolkit) -- that
# this container never has a GPU to use anyway. This matches the same real,
# deliberate choice already documented in Section 14/20 (this project runs
# on a CPU-only PyTorch build) instead of silently downloading a multi-GB
# stack no code path here can exercise. Installing it first satisfies
# ultralytics' `torch>=1.8.0` constraint before pip's resolver ever
# considers the CUDA build.
#
# torchvision is installed HERE, in the same command and from the same CPU
# index, not left for `pip install .[agent]` below to resolve on its own --
# left separate, pip is already satisfied once ultralytics' bare
# `torchvision>=0.9.0` constraint is met and pulls whatever torchvision
# build the *default* PyPI index resolves that against, which is not
# guaranteed to be the exact matching +cpu build for the torch version just
# installed above. A version/ABI mismatch there doesn't fail at install
# time -- pip has no way to check that -- it fails at first real inference
# call: `RuntimeError: operator torchvision::nms does not exist` (thrown
# from inside torchvision's compiled extension the moment
# YoloDetector.detect() runs). Pinning both from the same index in one
# command is what guarantees a matching pair.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# [agent] included by default so the Vision Agent works out of the box once
# ANTHROPIC_API_KEY is set -- without it, GET /agent/query would 503 with an
# import error instead of the clean "not configured" response deps.py
# already handles.
RUN pip install --no-cache-dir .[agent]

COPY scripts ./scripts
COPY configs ./configs

# Phase 14's checked-in evaluation-harness output (evaluation/results/*.json,
# git-tracked -- unlike data/, this is reference data, not gitignored real
# footage) -- GET /evaluation (src/api/routers/evaluation.py) reads these two
# files straight off disk. Same "reference data baked into the image at build
# time" treatment as configs/ above, not a runtime bind mount like data/: the
# results are static, checked-in artifacts of a harness that's re-run
# manually and re-committed, not something regenerated per-container.
COPY evaluation/results ./evaluation/results

# Real weights (yolov8n.pt) are intentionally NOT copied here -- they're
# gitignored, not source (see Section 2), and Ultralytics downloads them
# automatically on first use if TRACE_DETECTOR_WEIGHTS points at a bare
# name like "yolov8n.pt" rather than a mounted file path. First run needs
# outbound network access; see the README for the one-time download note.

# Standard production hardening: the app never needs root once installed.
RUN useradd --create-home --uid 1000 trace \
    && chown -R trace:trace /app
USER trace

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# The default command runs the API. docker-compose.yml's `worker` service
# overrides this with `python scripts/persist_video.py` instead -- both
# processes ship in the same image since they share every dependency, per
# this phase's "Dockerfile (API + pipeline)" requirement.
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
