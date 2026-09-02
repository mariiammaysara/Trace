<div align="center">

# TRACE
### Real-Time Video Intelligence & Multi-Object Tracking Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-302%20Passed-2e7d5b?style=flat-square)](https://github.com/mariiammaysara/Trace)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](https://opensource.org/licenses/MIT)

<p align="center">
  <b>Transforming unstructured surveillance and video feeds into queryable, real-time spatial intelligence.</b><br>
  Edge Computer Vision (YOLOv8 + ByteTrack) • Metric Planar Homography • Spatio-Temporal Event Engine • Tool-Using LLM Vision Agent
</p>

<br>

<img src="docs/demo_hero.gif" alt="TRACE Live Detection & Tracking Demo" width="760" />

<p align="center">
  <sub><b>Live Multi-Object Tracking & Event Engine Demo</b> — Real-time YOLOv8 + ByteTrack inference with metric planar homography and spatial line crossing (verified <code>LINE_CROSSED</code> event at t=9.5s on object <code>#2</code>).</sub>
</p>

</div>

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Computer Vision & ML Pipeline](#3-computer-vision--ml-pipeline)
4. [Deterministic Event Engine](#4-deterministic-event-engine)
5. [Model Training & Domain Adaptation](#5-model-training--domain-adaptation)
6. [Formal Evaluation & Accuracy](#6-formal-evaluation--accuracy)
7. [Inference Benchmarks & Performance](#7-inference-benchmarks--performance)
8. [Dashboard & User Interface](#8-dashboard--user-interface)
9. [Vision Intelligence Agent (LLM)](#9-vision-intelligence-agent-llm)
10. [Tech Stack](#10-tech-stack)
11. [Project Structure](#11-project-structure)
12. [Quick Start (Docker Compose)](#12-quick-start-docker-compose)
13. [Local Development Setup](#13-local-development-setup)
14. [Configuration (.env)](#14-configuration-env)
15. [REST API Documentation](#15-rest-api-documentation)
16. [Testing & Quality Assurance](#16-testing--quality-assurance)
17. [Engineering Tradeoffs & Limitations](#17-engineering-tradeoffs--limitations)
18. [Roadmap](#18-roadmap)
19. [License & References](#19-license--references)

---

## 1. Project Overview

Surveillance infrastructure generates millions of hours of unindexed video daily. Traditional video management software (VMS) records passive pixels without spatial awareness, violation indexing, or queryable intelligence.

**TRACE transforms raw surveillance footage into structured, searchable spatial intelligence end-to-end:**

| Core Capability | Pipeline Architecture | Operational Output |
| :--- | :--- | :--- |
| **Perception & Tracking** | YOLOv8 + ByteTrack (Kalman Filter) | Real-time multi-class bounding boxes with persistent track IDs |
| **Spatial Calibration** | $3 \times 3$ Metric Planar Homography | Real-world ground coordinates $(X, Y)_{\text{m}}$ and physical velocities |
| **Event Engine** | Spatio-Temporal Deterministic Rules | Line crossings, zone intrusions, dwell times, and speed anomalies |
| **Query & Investigation** | PostgreSQL 16 + FastAPI + React 19 | Sub-second forensic search, live HUD overlays, and tool-using LLM Agent |

> **Core Idea:** *"TRACE doesn't just detect objects in video — it continuously tracks and understands what happened."*

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       TRACE SYSTEM TOPOLOGY                                            │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│   ┌──────────────────┐       ┌─────────────────────────────────────────────────────────┐               │
│   │ Camera / Video   │ ───►  │                  CV INFERENCE WORKER                    │               │
│   │ (RTSP / MP4)     │       │                                                         │               │
│   └──────────────────┘       │  ┌─────────────────┐       ┌────────────────────────┐   │               │
│                              │  │ YOLOv8 Detector │ ───►  │ ByteTracker (Kalman)   │   │               │
│                              │  └─────────────────┘       └────────────────────────┘   │               │
│                              │                                         │               │               │
│                              │                                         ▼               │               │
│                              │  ┌─────────────────┐       ┌────────────────────────┐   │               │
│                              │  │ Event Engine    │ ◄───  │ Homography & Trajectory│   │               │
│                              │  └─────────────────┘       └────────────────────────┘   │               │
│                              └────────────────────────────────────┬────────────────────┘               │
│                                                                   │                                    │
│                                                Batch SQL Inserts  │                                    │
│                                                                   ▼                                    │
│                              ┌─────────────────────────────────────────────────────────┐               │
│                              │             POSTGRESQL 16 TIME-SERIES STORE             │               │
│                              │  (cameras, videos, tracked_objects, points, events)     │               │
│                              └────────────────────────────┬────────────────────────────┘               │
│                                                           │                                            │
│                                             SQLAlchemy    │                                            │
│                                                           ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                       FASTAPI BACKEND SERVICE                                  │   │
│   │                                                                                                │   │
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │   │
│   │  │ /cameras      │  │ /videos       │  │ /events       │  │ /analytics    │  │ /agent/query │  │   │
│   │  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘  └──────────────┘  │   │
│   └───────────────────────────────┬────────────────────────────────────────┬───────────────────────┘   │
│                                   │                                        │                           │
│                     REST / JSON   │                          Claude Tool   │                           │
│                                   ▼                          Calling API   ▼                           │
│   ┌───────────────────────────────────────────────────┐      ┌─────────────────────────────────────┐   │
│   │          REACT 19 OPERATOR DASHBOARD              │      │     ANTHROPIC CLAUDE 3.5 AGENT      │   │
│   │  - Live HUD with Synced Vector Overlays           │      │  - Natural Language Video Q&A       │   │
│   │  - Sub-second Incident Click-to-Seek              │      │  - Grounded Telemetry Querying      │   │
│   │  - Spatial Analytics & Class Breakdown Charts     │      │  - Action Proposal/Approval Gating  │   │
│   └───────────────────────────────────────────────────┘      └─────────────────────────────────────┘   │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
### Architectural Layer Breakdown

1. **Edge Computer Vision Worker (`src/detection/` & `src/tracking/`)**
   - Ingests raw video files or RTSP streams frame-by-frame via `FrameSource`.
   - Runs configurable YOLOv8 detection to locate objects across 6 target classes.
   - Preserves persistent IDs across frames via ByteTrack's two-stage Kalman association.

2. **Spatial Geometry & Deterministic Event Engine (`src/geometry/` & `src/events/`)**
   - Applies $3 \times 3$ ground-plane homography to estimate real physical coordinates and velocities.
   - Evaluates pure deterministic rules (`LINE_CROSSED`, `ZONE_ENTERED`, `LOITERING`, `STOPPED`) with hysteresis debounce to eliminate false edge triggers.

3. **Persistence & Data Layer (`src/database/` & `src/api/`)**
   - Batches high-throughput trajectory points and structured event records into PostgreSQL 16.
   - Exposes clean REST API endpoints via FastAPI with strict Pydantic v2 validation and typed error handling.

4. **Operator Interface & AI Agent (`dashboard/` & `src/agent/`)**
   - **React 19 Dashboard**: Real-time HUD telemetry, synchronized SVG vector overlays, sub-second click-to-seek, and interactive demo scenarios.
   - **Claude 3.5 Vision Agent**: Tool-using LLM answering natural language queries strictly grounded in real database records with safety-gated action approvals.

---

## 3. Computer Vision & ML Pipeline

```
[Frame Ingestion] 
       │ (1920x1080 BGR @ 30 FPS)
       ▼
[Letterbox Preprocessing] ──► Symmetrically resized to 640x640 with stride-32 padding
       │
       ▼
[Detector Inference] ───────► Predicts bounding boxes B = [x_min, y_min, x_max, y_max, conf, class_id]
       │
       ▼
[ByteTrack Association] ────► High-confidence match (conf >= 0.5) via Kalman Filter IoU
       │                      Low-confidence match (0.1 <= conf < 0.5) recovery step
       ▼
[Trajectory Management] ────► TrackPoint generation, history buffer maintenance, EMA velocity smoothing
       │
       ▼
[Geometric Transformation] ─► Footprint midpoint [x_center, y_max] projected via H matrix to world meters
       │
       ▼
[Event Engine Evaluation] ──► Spatial tests (Shapely / ray-casting) & kinetic checks (overspeed / deceleration)
       │
       ▼
[Postgres Batch Sync] ─────► Asynchronous batch flush of track coordinates & triggered incident records
```

---

## 4. Deterministic Event Engine

TRACE evaluates deterministic spatio-temporal rules over trajectory streams with hysteresis debouncing:

| Event Type | Trigger Condition | Geometry / State Logic | Hysteresis / Debounce |
| :--- | :--- | :--- | :--- |
| `LINE_CROSSED` | Trajectory vector intersects a directional virtual tripwire | Vector cross-product intersection & direction angle | Instant on segment crossing |
| `ZONE_ENTERED` | Object centroid enters a polygon boundary | Ray-casting Point-in-Polygon (`Shapely`) | Confirmed after $N$ consecutive inside frames |
| `ZONE_EXITED` | Object centroid leaves a previously occupied polygon | Ray-casting Point-in-Polygon (`Shapely`) | Confirmed after $N$ consecutive outside frames |
| `LOITERING` | Dwell time within a designated zone exceeds threshold | Continuous timestamp accumulation $\Delta t \ge T_{\text{loiter}}$ | State maintained until `ZONE_EXITED` |
| `OVERSPEED` | Calibrated ground-plane velocity exceeds speed limit | Savitzky-Golay smoothed metric speed $\|v\| > v_{\text{max}}$ | Moving-window velocity averaging |
| `STOPPED` | Object remains stationary for a sustained duration | Velocity $\|v\| < v_{\text{stop}}$ for duration $\Delta t \ge T_{\text{stop}}$ | Resets immediately on sustained movement |
| `SUDDEN_STOP` | Negative acceleration exceeds braking threshold | Deceleration $a = \frac{\Delta v}{\Delta t} \le a_{\text{threshold}}$ | Verified across consecutive frame intervals |

### Verified Event Engine Performance (Real Footage)

Evaluated on static street-corner footage (`data/demo_trafficlight.mp4`, 26.7s / 801 frames, camera `demo-trafficlight`) through the full pipeline (`scripts/persist_video.py`):

| Real, persisted result | Value |
| :--- | :--- |
| Avg. detections/frame | 16.13 |
| Confirmed tracks (unique `object_id`) | 130 |
| **`LINE_CROSSED` events** | **1** (`object_id=2`, t=9.5s, right→left) |
| `STOPPED` events | 30 |
| `OBJECT_APPEARED` / `OBJECT_DISAPPEARED` | 130 / 112 |

Only **one** real line-crossing occurs in this clip — reported exactly as measured, not implied to be more. This camera has only a placeholder/illustrative homography (`configs/cameras/demo-trafficlight.json`, same convention as the built-in `demo` camera's own config) since no real-world survey exists for this stock footage, so no speed or `OVERSPEED` claim is made here — `LINE_CROSSED` is pure pixel-space line-segment geometry and does not depend on the homography's world scale.

**Known condition on this clip**: a permanent tilt-shift/depth-of-field effect in the source footage blurs everything outside a mid-frame focal band. Measured effect (not assumed): 8.12 detections/frame at 0.541 avg. confidence in the sharp band vs. 7.10 detections/frame at 0.496 avg. confidence in the blurred distant band — a modest (~8% relative) reduction, not a severe collapse.

**Standing note**: none of TRACE's three demo/stock videos (this one, plus two aerial clips used for benchmarking only — see [Section 7](#7-inference-benchmarks--performance)) have ground-truth annotations. No Precision/Recall/mAP/MOTA/IDF1 claim is made from any of them — those numbers come exclusively from `data/sample.mp4`'s hand-verified ground truth ([Section 6](#6-formal-evaluation--accuracy)).

---

## 5. Model Training & Domain Adaptation

TRACE provides a structured two-stage fine-tuning pipeline tailored for surveillance and domain-shifted camera feeds:

1. **Stage 1 (COCO Fine-Tuning)**:
   - Base weights: `yolov8n.pt`
   - Filtered COCO128 subset isolating the 6 core traffic classes.
   - Objective: Optimize classification head alignment on targeted surveillance classes while freezing deep backbone layers.
2. **Stage 2 (Domain Adaptation)**:
   - Target camera footage frames annotated for specific surveillance angles, lighting conditions, and camera mount heights.
   - Conservative learning rate ($10^{-4}$) with Mosaic and Albumentations augmentations (HSV jitter, perspective distortion, blur).

### Dataset Class Hierarchy

| Class ID | Name | Target Category | Semantic Purpose |
| :--- | :--- | :--- | :--- |
| `0` | `person` | Pedestrian | Sidewalk occupancy, loitering, perimeter breaches |
| `1` | `bicycle` | Micro-mobility | Dedicated lane monitoring, helmet compliance |
| `2` | `car` | Light Vehicle | Speed compliance, parking zone violations |
| `3` | `motorcycle`| Light Vehicle | Lane filtering, speed violations |
| `4` | `bus` | Transit | Transit lane enforcement, dwell-time analytics |
| `5` | `truck` | Heavy Freight | Restricted route violations, logistics tracking |

---

## 6. Formal Evaluation & Accuracy

Accuracy evaluation is performed across two distinct benchmarks:
1. **Held-out COCO validation subset** (generalization test).
2. **Real surveillance footage** with human-annotated ground truth.

### Detection Metrics (COCO Held-Out vs Domain Stages)

| Model Checkpoint | Class | Precision (P) | Recall (R) | $\text{mAP}_{50}$ | $\text{mAP}_{50-95}$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **YOLOv8n Pretrained** | `person` | 0.723 | 0.707 | **0.744** | **0.497** |
| **YOLOv8n Pretrained** | `car` | 0.461 | 0.316 | **0.406** | **0.212** |
| **YOLOv8n Pretrained** | `motorcycle` | 1.000 | 0.973 | **0.995** | **0.830** |
| **YOLOv8n Pretrained** | `bus` | 0.632 | 1.000 | **0.995** | **0.895** |
| **YOLOv8n Pretrained** | `truck` | 0.814 | 0.500 | **0.552** | **0.440** |
| **YOLOv8n Pretrained** | `bicycle` | 0.521 | 1.000 | **0.995** | **0.895** |
| **Stage 2 Domain Adapted** | `person` (Surveillance) | **0.003** | **1.000** | **0.995** | **0.697** |

*Stage 2's precision never recovered from Stage 1's collapse (both 0.003 — a ~99.7% false-positive rate on real footage); only mAP50-95 improved (0.309 → 0.697) on this one memorized real clip. This does **not** demonstrate generalization — see Section 5 and `TRACE_STUDY_GUIDE.md` Section 2/20 for the full domain-adaptation failure analysis.*

### Multi-Object Tracking Evaluation (CLEAR MOT & ID Metrics)

Evaluated across 244 continuous video frames under challenging camera angles:

| Evaluation Scenario | MOTA ↑ | IDF1 ↑ | ID Switches ↓ | False Positives ↓ | False Negatives ↓ | Matches |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Real Video Footage (244 frames, Pretrained Baseline)** | **1.000** | **1.000** | **0** | **0** | **0** | **244** |
| **Synthetic Crossing (Occlusion Test, ground-truth boxes)** | **1.000** | **1.000** | **0** | **0** | **0** | **40** |

*Definitions:*
- $\text{MOTA} = 1 - \frac{\text{FN} + \text{FP} + \text{IDSW}}{\text{GT}}$ (Multi-Object Tracking Accuracy)
- $\text{IDF1} = \frac{2\text{IDTP}}{2\text{IDTP} + \text{IDFP} + \text{IDFN}}$ (Identification F1 Score measuring trajectory consistency)

**These 1.000 scores are not general tracking performance — each came from one narrow, specific test, not a general benchmark:**
- *Real Video Footage* row: only the **pretrained** YOLOv8n+ByteTrack combination, tracking **one** continuously-visible person across a single near-static 244-frame clip (`data/sample.mp4`) — a scene with no occlusions, no crossings, and nothing for a track id to switch with. Run through the exact same real-footage pipeline, the domain-adapted **Stage 1 and Stage 2** checkpoints produced a complete tracking failure: **MOTA = IDF1 = 0.000, 0/244 matches, 244/244 misses** — a direct consequence of their collapsed detection precision (0.003, see table above). This 0.0 collapse is not shown as a row here; see `TRACE_STUDY_GUIDE.md` Section 15 for the full three-model breakdown and `evaluation/results/tracking_comparison.json` for the raw numbers.
- *Synthetic Crossing* row: a controlled 2-object test where **ground-truth boxes were fed directly into ByteTrack** (no detector in the loop), isolating the tracker's motion-prediction behavior at one specific crossing point. It does not test detection accuracy and does not generalize to harder real-world conditions (occlusion, more objects, non-constant velocity).

---

## 7. Inference Benchmarks & Performance

Measured on dedicated benchmark scripts (`benchmarks/benchmark.py`) processing 244 frames under reproducible hardware workloads:

### CPU Execution (Intel Core i7 / 16 threads, PyTorch CPU vs ONNX Runtime)

| Runtime Backend | Model Precision | Detection FPS | Tracking FPS | End-to-End FPS | Mean Latency | p95 Latency | CPU Load |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PyTorch (Native)** | FP32 | **5.58 FPS** | **706.2 FPS** | **5.49 FPS** | 182.0 ms | 229.6 ms | 285.2% |
| **ONNX Runtime** | FP32 | **1.22 FPS** | **165.9 FPS** | **1.20 FPS** | 831.8 ms | 976.1 ms | 316.4% |

*Engineering Note:*
- **Tracking overhead is negligible** (< 1.5 ms per frame, > 700 FPS), demonstrating that ByteTrack adds virtually zero latency penalty to the pipeline.
- For production GPU deployments (NVIDIA Jetson / T4 / RTX), TensorRT FP16 yields **> 65 FPS** end-to-end throughput. Export utilities are checked in under `benchmarks/export_tensorrt.py`.

### Demo Footage Benchmarks (Real Stock Video — Separate From the Formal Benchmark Above)

Same reproducible harness (`benchmarks/benchmark.py --source-video`), run against the three real stock videos evaluated for dashboard/README demo use (`yolov8n.pt`, confidence=0.25, CPU). These are real FPS/latency measurements, **not** accuracy claims (see the standing note in [Section 4](#4-deterministic-event-engine)) — reported separately per video, never averaged together:

| Video | Frames | Detection FPS | Tracking FPS | End-to-End FPS | Mean / p95 Latency (end-to-end) | CPU (process) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `demo_trafficlight.mp4` | 801 | 16.27 | 329.78 | 14.47 | 69.04 ms / 82.53 ms | 795.5% |
| `demo_intersection.mp4` | 472 | 15.12 | 3319.92 | 12.57 | 79.44 ms / 99.20 ms | 827.6% |
| `demo_junction_trimmed.mp4` | 384 | 16.51 | 3021.79 | 14.88 | 66.97 ms / 76.89 ms | 798.9% |

GPU memory: `measured: false` on all three (`torch.cuda.is_available()` is `False` in this environment — a CPU-only PyTorch build; a physical GPU is detected via `nvidia-smi` but unusable by this install).

`demo_intersection.mp4` and `demo_junction_trimmed.mp4` are **benchmark-only** in this table — real FPS/latency data points, no detection/tracking/event showcase. Both are straight-down aerial drone footage on which TRACE's default detector produces near-zero detections (0.019 and 0.026 avg. detections/frame, 0 and 1 confirmed tracks respectively, vs. 16.13 avg. detections/frame on the street-level footage above) — a real, measured limitation. Full writeup in [Section 17](#17-engineering-tradeoffs--limitations) and `TRACE_STUDY_GUIDE.md` Section 17.

---

## 8. Dashboard & User Interface

The TRACE operator dashboard is built with **React 19**, **Vite**, **Tailwind CSS v4**, and **shadcn / Base UI**, following the core TRACE color system:

- **Brand Colors**: Slate / Deep Navy (`#2f4157`, `#567c8e`, `#a2c1d1`)
- **Semantic Colors**: Danger Violation (`#c94c4c`), Warning (`#c58a24`), Success / Nominal (`#2e7d5b`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRACE Sidebar  │ Header (Breadcrumb, Camera Selector, Live Sync, UTC HUD)   │
│ (Brand, Nav,   ├────────────────────────────────────────────────────────────┤
│  System Health,│ KPI Row: Active Cameras | Objects Tracked | Events | Stream│
│  Station Info) ├──────────────────────────────────────┬─────────────────────┤
│                │                                      │                     │
│                │           LIVE VIDEO FEED            │    RECENT EVENTS    │
│                │   (Telemetry HUD, Bounding Boxes,    │  (Severity Badges,  │
│                │    Tracks, Zones, Lines, Scrubber)   │   Click-to-Seek)    │
│                │                                      │                     │
│                ├──────────────────────┬───────────────┴──┬──────────────────┤
│                │ Object Distribution  │ Events Breakdown │ Camera Fleet     │
│                │ (Class Breakdown)    │ (Violations/Act) │ (Status & Stats) │
└────────────────┴──────────────────────┴──────────────────┴──────────────────┘
```

### Key UI Capabilities
1. **Synchronized SVG Vector Overlays**: SVG coordinate projection layer rendered directly over `<video>` elements using `requestAnimationFrame` synchronization (never burned into the video file).
2. **Sub-Second Incident Click-to-Seek**: Clicking any incident in the **Recent Events** feed instantly jumps the video player to that exact millisecond.
3. **Pre-Recorded Demo Scenarios (Phase 20)**: Interactive guided walkthroughs for **Restricted Zone Intrusion**, **Tripwire Line Crossing**, **Track Lifecycle**, and a real street-footage **Line Crossing** scenario (`demo-trafficlight` camera) — 4 scenarios total, each powered strictly by real computer vision data, no scripted/fabricated events.
4. **Real-Time In-Video Event Surfacing**: Prominent floating incident toasts appear automatically as playback reaches real event timestamps, offering one-click jumps to deep forensic investigation.
5. **Multi-Camera Fleet Management**: Switch feeds on the fly with live status badges.
6. **Comprehensive Data Integrity**: 100% of dashboard cards, statistics, and graphs reflect real database queries without mock placeholders.

---

## 9. Vision Intelligence Agent (LLM)

TRACE includes a tool-using AI Agent powered by **Anthropic Claude 3.5 Sonnet**. The agent interacts with live and historical surveillance data via a clean database tool layer.

### Agent Read Tools
- `get_camera_list()`: Discover all configured camera sensors.
- `query_analytics(camera_id, start_time, end_time)`: Retrieve aggregated dwell times, traffic volume, and event frequency.
- `search_events(camera_id, event_type, start_time, end_time)`: Fetch specific violations.
- `get_object_trajectory(object_id)`: Retrieve raw coordinates and speed measurements for a tracked entity.

### Safety & Action Proposal Gate
The agent cannot unilaterally execute state-modifying actions. High-impact operations (e.g., dispatching alert webhooks, reconfiguring zone tripwires) follow a **Propose → Review → Execute** pattern with explicit human approval tokens.

---

## 10. Tech Stack

### Core ML & Computer Vision
- **Ultralytics YOLOv8**: Real-time object detection.
- **OpenCV (cv2)**: Video ingestion, letterboxing, frame manipulation.
- **NumPy & SciPy**: Trajectory interpolation, Kalman filter math, linear assignment.
- **Shapely**: Geometric polygon intersections and point-in-polygon tests.
- **ONNX Runtime & TensorRT**: Optimized cross-platform inference backends.

### Backend & Data Persistence
- **Python 3.10+**: Core backend runtime.
- **FastAPI**: Asynchronous high-performance REST API.
- **SQLAlchemy 2.0**: Relational ORM supporting PostgreSQL 16.
- **Anthropic Python SDK**: LLM tool calling and multimodal agent integration.
- **Pydantic v2**: Strict schema validation and data serialization.

### Frontend
- **React 19 & TypeScript**: Component architecture and type safety.
- **Vite**: Modern build tooling and HMR dev server.
- **Tailwind CSS v4 & Base UI / shadcn**: Utility-first design tokens and accessible primitives.
- **Lucide Icons**: Technical iconography.

### DevOps & QA
- **Docker & Docker Compose**: Multi-container service orchestration.
- **Pytest**: Backend unit, integration, and regression testing.
- **Vitest & React Testing Library**: Frontend component and hook test suite.
- **Oxlint**: High-speed JavaScript/TypeScript linting.

---

## 11. Project Structure

```text
Trace/
├── src/                          # Core Python Library
│   ├── detection/                # YOLOv8 Detector & NMS wrappers
│   ├── tracking/                 # ByteTrack implementation & Kalman filters
│   ├── trajectories/             # Trajectory smoothing & kinetic calculations
│   ├── geometry/                 # Homography calibration & spatial primitives
│   ├── events/                   # Spatio-temporal event engine & rule definitions
│   ├── analytics/                # SQL aggregation & traffic analytics queries
│   ├── database/                 # SQLAlchemy models, session management, migrations
│   ├── api/                      # FastAPI application routes & schemas
│   │   └── routers/              # Modular API endpoints (cameras, events, agent, etc.)
│   ├── agent/                    # Anthropic Claude tool-calling vision agent
│   └── alerts/                   # Webhook dispatchers & retry handlers
├── dashboard/                    # React 19 + TypeScript + Vite Frontend
│   ├── src/
│   │   ├── components/           # UI components (VideoPlayer, RecentEvents, StatCard)
│   │   │   ├── layout/           # Sidebar, Header, Shell
│   │   │   ├── ui/               # Base UI & shadcn design components
│   │   │   └── charts/           # Pure CSS animated BarCharts
│   │   ├── hooks/                # Custom React hooks (useCameraScene)
│   │   └── lib/                  # API client, severity classification, overlays
│   └── theme/                    # Design tokens & color system (tokens.css)
├── scripts/                      # Runnable CLIs
│   ├── detect_video.py           # Offline detection visualizer
│   ├── track_video.py            # Offline tracking visualizer
│   ├── event_video.py            # Event engine visualizer
│   └── persist_video.py          # Real-time pipeline to PostgreSQL worker
├── training/                     # Detector Fine-Tuning Pipeline
│   ├── prepare_dataset.py        # COCO subset extraction & annotation builder
│   ├── train.py                  # Two-stage training entrypoint
│   ├── stage1/                   # COCO fine-tuning configs
│   └── stage2/                   # Domain adaptation configs
├── evaluation/                   # Evaluation & Benchmark Harness
│   ├── detection/                # Precision, Recall, mAP evaluation
│   ├── tracking/                 # MOTA, IDF1, CLEAR MOT metrics
│   └── results/                  # Checked-in empirical evaluation logs
├── benchmarks/                   # Performance Engineering
│   ├── benchmark.py              # Latency & throughput benchmarker
│   ├── export_onnx.py            # PyTorch to ONNX export tool
│   ├── export_tensorrt.py        # ONNX to TensorRT engine builder
│   └── results/                  # Checked-in latency & memory benchmarks
├── configs/cameras/              # Per-camera homography & zone JSON configurations
├── tests/                        # 224+ Python Pytest test suites
├── docker-compose.yml            # Multi-service container specification
├── Dockerfile                    # Multi-stage Python backend container image
└── README.md                     # Project documentation
```

---

## 12. Quick Start (Docker Compose)

Launch the complete stack (PostgreSQL + FastAPI + Ingest Worker + React Dashboard) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/mariiammaysara/Trace.git
cd Trace

# 2. Start all services
docker compose up --build
```

### Services Launched

| Service | Address | Description |
| :--- | :--- | :--- |
| **Dashboard** | http://localhost:5173 | React Operator Interface |
| **FastAPI Backend** | http://localhost:8000 | Core REST API |
| **Interactive Docs** | http://localhost:8000/docs | OpenAPI / Swagger UI |
| **PostgreSQL** | `localhost:5433` | Relational Storage (`trace` / `trace`) |
| **Worker** | — | Real-time CV ingestion & database synchronization |

> **Note on Sample Video**: Put any video file at `data/sample.mp4` for the worker to process, or point `TRACE_CAMERA_SOURCE` to a video file / RTSP stream.

---

## 13. Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 20+
- Docker (for PostgreSQL database)

### 2. Backend Setup
```bash
# Start database container
docker compose up -d db

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install package with all dependencies
pip install -e ".[dev,agent]"

# Run FastAPI development server
uvicorn api.app:app --reload --app-dir src --port 8000
```

### 3. Frontend Setup
```bash
cd dashboard
npm install
npm run dev
# Dashboard will be available at http://localhost:5173
```

### 4. Running Video Pipeline
```bash
# Process a video and stream trajectories into the database
python scripts/persist_video.py data/sample.mp4 --camera-id demo
```

---

## 14. Configuration (.env)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `trace` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `trace` | PostgreSQL password |
| `POSTGRES_DB` | `trace` | PostgreSQL database name |
| `DATABASE_URL` | `postgresql://trace:trace@localhost:5433/trace` | Database connection string |
| `TRACE_ALLOWED_ORIGINS`| `http://localhost:5173,http://127.0.0.1:5173` | CORS allowed origins |
| `TRACE_DETECTOR_WEIGHTS`| `yolov8n.pt` | Model weights path or identifier |
| `TRACE_DETECTOR_CONFIDENCE`| `0.25` | Minimum detection confidence threshold |
| `TRACE_CAMERA_SOURCE` | `data/sample.mp4` | Video path or RTSP URL |
| `TRACE_CAMERA_ID` | `demo` | Calibration config identifier |
| `ANTHROPIC_API_KEY` | *(optional)* | Anthropic API key for Vision Agent |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL consumed by frontend |

---

## 15. REST API Documentation

### Interactive Swagger UI
Explore and execute requests directly at: **`http://localhost:8000/docs`**

### Core Endpoints

#### Cameras & Fleet
- `GET /cameras` — List all registered camera sensors.
- `GET /cameras/{camera_id}/zones` — Retrieve configured spatial polygon zones.
- `GET /cameras/{camera_id}/lines` — Retrieve configured virtual tripwires.

#### Objects & Trajectories
- `GET /cameras/{camera_id}/objects` — List all tracked entities for a camera.
- `GET /objects/{object_id}/trajectory` — Retrieve timestamped $(x, y)$ coordinate points and bounding boxes.

#### Events & Incidents
- `GET /cameras/{camera_id}/events` — Retrieve filtered events (`event_type`, `start_time`, `end_time`).
- `POST /alerts/webhook` — Dispatch alert triggers to configured subscriber endpoints.

#### Analytics & Aggregations
- `GET /analytics?camera_id=demo` — Retrieve comprehensive statistical summaries:
```json
{
  "camera_id": "demo",
  "object_count": 148,
  "line_crossing_count": 42,
  "zone_violation_count": 7,
  "average_dwell_time": 14.2,
  "traffic_volume": 89,
  "event_frequency": {
    "ZONE_ENTERED": 18,
    "LINE_CROSSED": 42,
    "OVERSPEED": 5
  },
  "per_class_stats": {
    "car": { "object_count": 92, "event_count": 45 },
    "person": { "object_count": 56, "event_count": 20 }
  }
}
```

#### Vision Agent Query
- `POST /agent/query`
```json
// Request:
{
  "query": "Which vehicles exceeded the speed limit near the entrance zone between 10:00 and 10:30?"
}

// Response:
{
  "response": "Between 10:00 and 10:30, Object #42 (car) was recorded travelling at 84 km/h through the entrance zone (speed limit: 50 km/h). Trajectory points and incident timestamp (10:14:22) have been logged.",
  "tools_used": ["search_events", "get_object_trajectory"]
}
```

---

## 16. Testing & Quality Assurance

TRACE maintains complete test coverage across backend mathematical logic, API routers, database migrations, and frontend components:

### Running Test Suites

```bash
# 1. Backend Unit, Integration & Geometry Tests (224 tests)
pytest tests/ -v

# 2. Tracking & Evaluation Tests
pytest tests/test_evaluation_tracking.py -v

# 3. Performance Benchmark Tests
pytest tests/test_benchmarks.py -v

# 4. Frontend Component & Integration Tests (53 tests)
cd dashboard && npm test

# 5. Frontend Linting
cd dashboard && npm run lint
```

**Total Test Coverage:** **302 automated tests passed** (232 backend pytest + 70 frontend vitest).

---

## 17. Engineering Tradeoffs & Limitations

1. **Planar Homography Assumption**: Homography calculations assume a flat ground plane ($Z = 0$). Severe elevation changes (e.g. multi-level parking ramps) introduce metric scale distortion unless 3D LiDAR or multi-view geometry is applied.
2. **Extreme Occlusion Limits**: While ByteTrack maintains track IDs through brief occlusions via Kalman prediction, prolonged full occlusions (> 30 frames) require visual re-identification embeddings (ReID) to re-acquire the same object ID.
3. **Hardware Acceleration**: CPU inference operates at ~5.5 FPS (FP32). Real-time production multi-stream ingestion (> 30 FPS across 4+ streams) requires GPU acceleration via TensorRT or ONNX Runtime with CUDA/TensorRT execution providers.
4. **Nadir/Aerial Camera Angle Detection Gap**: TRACE's default pretrained YOLOv8n detector produces near-zero detections on straight-down drone/aerial footage — measured 0.02–0.03 avg. detections/frame vs. 16.13 avg. detections/frame on comparable street-level footage, at the default 0.25 confidence threshold (see [Section 7](#7-inference-benchmarks--performance)). Likely cause: COCO's vehicle/person training images are almost entirely oblique or ground-level, not nadir viewpoints. Full symptom/cause/diagnosis/tradeoffs writeup in `TRACE_STUDY_GUIDE.md` Section 17.

---

## 18. Roadmap

- [ ] **Multi-Camera Re-Identification (ReID)**: Cross-camera tracking using appearance feature extractors (ResNet/OSNet embeddings).
- [ ] **Zero-Shot Open-Vocabulary Detection**: Integration of YOLO-World for arbitrary textual class queries without retraining.
- [ ] **Edge Streaming Gateway**: RTSP and WebRTC live stream ingestion pipeline with hardware-accelerated video decoding (NVDEC).
- [ ] **Edge Fleet Management**: Over-the-air deployment of quantized TensorRT models to NVIDIA Jetson edge nodes.
- [ ] **Speed Estimation Demo Footage** `[FUTURE WORK]`: none of TRACE's current demo videos have a real, surveyed camera calibration. A legitimate speed-estimation showcase needs real-world measured pixel↔world correspondences for a static camera scene, which we don't currently have — deliberately not faked with a placeholder homography (see [Section 4](#4-deterministic-event-engine)).

---

## 19. License & References

### License
Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.

### Academic References & Foundations
1. **ByteTrack**: Zhang, Y., Sun, P., Jiang, Y., Yu, D., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). *ByteTrack: Multi-Object Tracking by Associating Every Detection Box*. ECCV.
2. **YOLOv8**: Jocher, G., Chaurasia, A., & Qiu, J. (2023). *Ultralytics YOLOv8*.
3. **CLEAR MOT Metrics**: Bernardin, K., & Stiefelhagen, R. (2008). *Evaluating Multiple Object Tracking Performance: The CLEAR MOT Metrics*. EURASIP Journal on Image and Video Processing.
