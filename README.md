# TRACE

TRACE is a real-time multi-object tracking and video intelligence system: it detects,
tracks, and analyzes objects across video streams, builds trajectories, geolocates
and calibrates scenes, detects events, and surfaces analytics through an API, a
dashboard, and a tool-using LLM agent grounded in real stored data. See
[`TRACE_STUDY_GUIDE.md`](./TRACE_STUDY_GUIDE.md) for the full technical write-up —
this file is just setup and run instructions.

## Quick start (Docker Compose — one command)

Requires Docker and Docker Compose. No `.env` file is required — every variable has
a working default (see `.env.example` if you want to override anything, e.g. to add
a real `ANTHROPIC_API_KEY` for the Vision Agent).

```bash
docker compose up --build
```

This builds and starts four services:

| Service | URL | What it is |
|---|---|---|
| `db` | `localhost:5433` (Postgres) | Schema is created automatically on first API/worker start |
| `api` | http://localhost:8000 | FastAPI backend — interactive docs at http://localhost:8000/docs |
| `dashboard` | http://localhost:5173 | The built React dashboard, served by nginx |
| `worker` | — (no exposed port) | Runs the CV pipeline against `data/sample.mp4` and persists tracks/events to Postgres |

First run downloads the detector's weights (`yolov8n.pt`, ~6MB, fetched automatically
by Ultralytics — not committed to the repo) inside the `api`/`worker` containers, so
it needs outbound network access the first time either one runs.

**The `worker` service needs its own video to process.** `data/` is gitignored (real
footage is never committed — see `TRACE_STUDY_GUIDE.md` Section 2) — a fresh clone
has nothing there, so `worker` will log `could not open frame source: 'data/sample.mp4'`
and exit until you provide one:

```bash
mkdir -p data
cp /path/to/your/video.mp4 data/sample.mp4
docker compose up worker   # or: docker compose restart worker
```

Or point it at a different file via `TRACE_CAMERA_SOURCE` in `.env` (copy
`.env.example` to `.env` first). The `api` and `dashboard` services work fully
without this — only `worker` needs real footage.

Stop everything with `docker compose down` (add `-v` to also drop the Postgres
volume and start clean next time).

### Environment variables

Copy `.env.example` to `.env` to override any of these; `docker compose up` reads
`.env` automatically. Every one of these can also be exported directly in your shell
for a manual (non-Docker) run — see below.

| Variable | Default | Used by |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `trace` / `trace` / `trace` | `db`; `api`/`worker` build `DATABASE_URL` from these |
| `DATABASE_URL` | derived from the three above | `api`, `worker` (direct override if you're not using `db`'s compose defaults) |
| `TRACE_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | `api` — CORS allowlist |
| `TRACE_LOG_LEVEL` | `INFO` | `api`, `worker` |
| `TRACE_DETECTOR_WEIGHTS` | `yolov8n.pt` | `api` (agent tools), `worker` — path/name of the detector weights to load |
| `TRACE_DETECTOR_CONFIDENCE` | `0.25` | `api`, `worker` — detection confidence threshold |
| `TRACE_CAMERA_SOURCE` | `data/sample.mp4` | `worker` — video file path (under the `./data` mount) or camera index |
| `TRACE_CAMERA_ID` | `demo` | `worker` — which `configs/cameras/<id>.json` to load |
| `TRACE_NUM_FRAMES` | unset (process until the source is exhausted) | `worker` |
| `ANTHROPIC_API_KEY` | unset | `api` — optional; `POST /agent/query` returns a clean `503` until this is set |
| `VITE_API_BASE_URL` | `http://localhost:8000` | `dashboard` — **baked in at image build time**, not read at container runtime; rebuild (`docker compose build dashboard`) after changing it |

## Manual setup (no Docker)

Useful for development — this is how every phase of TRACE was actually built and
tested.

**Requirements**: Python 3.10+, Node 20+, Docker (for Postgres only — or any
Postgres 16 reachable at the URL you configure).

```bash
# 1. Postgres (only the db container, not the full stack)
docker compose up -d db

# 2. Python environment
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev,agent]"

# 3. Run the API
uvicorn api.app:app --reload --app-dir src
# -> http://localhost:8000/docs

# 4. Run the dashboard (separate terminal)
cd dashboard
npm install
npm run dev
# -> http://localhost:5173

# 5. Run the pipeline against a video and persist to the database (separate terminal)
python scripts/persist_video.py data/sample.mp4 --camera-id demo
```

`DATABASE_URL` defaults to `postgresql://trace:trace@localhost:5433/trace` (matching
`docker compose up -d db`'s host port mapping) — export it to point anywhere else.
Every other environment variable in the table above works the same way outside
Docker as inside it.

### Running the tests

```bash
# Python (224 tests as of Phase 16; requires the db container running --
# TEST_DATABASE_URL defaults to postgresql://trace:trace@localhost:5433/trace_test)
pytest tests/ -v

# Dashboard (Vitest)
cd dashboard && npm test
```

## Project layout

- `src/` — the actual TRACE library: detection, tracking, trajectories, geometry,
  events, database, API, agent.
- `scripts/` — runnable CLIs wired to real video (`detect_video.py`, `track_video.py`,
  `event_video.py`, `persist_video.py`, ...).
- `dashboard/` — the React + Vite frontend.
- `training/`, `evaluation/`, `benchmarks/` — the detector fine-tuning pipeline, the
  accuracy evaluation harness (MOTA/IDF1, precision/recall/mAP), and the performance
  benchmarking harness (FPS/latency/CPU/GPU across PyTorch/ONNX/TensorRT), each with
  real measured results checked in under their own `results/`.
- `configs/cameras/` — per-camera calibration (homography), lines, and zones.
- `tests/` — the full test suite (backend); `dashboard/src/**/*.test.tsx` (frontend).

## What's built

TRACE was built phase by phase; `TRACE_STUDY_GUIDE.md` documents every phase's real
design decisions, measured results, and honest limitations — Section 19
(Implementation Map) is the authoritative file-by-file index, Section 17 (Failure
Cases & Debugging) is a real bug log, and Section 20 (Experiments) holds the
performance numbers.

- [x] Phase 0 — Repository bootstrap
- [x] Phase 1 — Computer vision foundations, project skeleton
- [x] Phase 2 — Object detection (`YoloDetector`, fine-tuning pipeline)
- [x] Phase 3 — Multi-object tracking (`ByteTracker`)
- [x] Phase 4 — Trajectory & motion analysis
- [x] Phase 5 — Camera geometry (homography, line/zone primitives)
- [x] Phase 6 — Speed estimation
- [x] Phase 7 — Event engine (`LINE_CROSSED`, `ZONE_ENTERED`/`EXITED`, `OVERSPEED`, `STOPPED`, `SUDDEN_STOP`, `LOITERING`, ...)
- [x] Phase 8 — Database layer (PostgreSQL, SQLAlchemy)
- [x] Phase 9 — Backend API (FastAPI)
- [x] Phase 10 — Dashboard (React + Vite: live view, analytics, event investigation)
- [x] Phase 11 — Vision Agent (tool-using LLM, grounded in real stored data)
- [x] Phase 12 — Agent actions & safety (propose/approve gate, real-time alerting)
- [x] Phase 13 — Detector fine-tuning (two-stage, real measured before/after)
- [x] Phase 14 — Evaluation (MOTA/IDF1, precision/recall/mAP, real ground truth)
- [x] Phase 15 — Performance engineering (FPS/latency/CPU/GPU benchmarking, ONNX/TensorRT export)
- [x] Phase 16 — Containerization & deployment (this phase)

## License

MIT — see [`LICENSE`](./LICENSE).
