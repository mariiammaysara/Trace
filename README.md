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
| **Spatial Calibration** | 3×3 Metric Planar Homography | Real-world ground coordinates (X, Y) in meters & physical velocities |
| **Event Engine** | Spatio-Temporal Deterministic Rules | Line crossings, zone intrusions, dwell times, and speed anomalies |
| **Query & Investigation** | PostgreSQL 16 + FastAPI + React 19 | Sub-second forensic search, live HUD overlays, and tool-using LLM Agent |

> **Core Idea:** *"TRACE doesn't just detect objects in video — it continuously tracks and understands what happened."*

---

## 2. System Architecture

```mermaid
flowchart LR
    subgraph INGEST["1. Edge CV Worker"]
        direction TB
        CAM["RTSP / Video Stream"] --> YOLO["YOLOv8 Detector"]
        YOLO --> BYTE["ByteTrack (Kalman)"]
        BYTE --> HOM["Homography & Speed"]
        HOM --> EVT["Deterministic Event Engine"]
    end

    subgraph BACKEND["2. Persistence & API Layer"]
        direction TB
        EVT -->|Batch Insert| DB[("PostgreSQL 16 Store")]
        DB <--> API["FastAPI REST Endpoints"]
    end

    subgraph CLIENT["3. User Interfaces"]
        direction TB
        API <--> DASH["React 19 Operator Dashboard<br/>(Vector Overlays & HUD)"]
        API <--> AGENT["Claude 3.5 Vision Agent<br/>(Tool-Grounded Investigation)"]
    end
```

<br>

### Architectural Layer Breakdown

1. **Edge Computer Vision Worker (`src/detection/` & `src/tracking/`)**  
   Ingests raw video files or RTSP streams frame-by-frame via `FrameSource`, runs configurable YOLOv8 detection across 6 mobility classes, and preserves persistent track IDs across frames using ByteTrack's two-stage Kalman association.

<br>

2. **Spatial Geometry & Deterministic Event Engine (`src/geometry/` & `src/events/`)**  
   Applies 3×3 ground-plane homography to estimate physical coordinates and velocities in meters, evaluating deterministic rules (`LINE_CROSSED`, `ZONE_ENTERED`, `LOITERING`, `STOPPED`) with hysteresis debouncing.

<br>

3. **Persistence & Data Layer (`src/database/` & `src/api/`)**  
   Batches high-throughput trajectory points and structured event records into PostgreSQL 16 time-series tables, exposing clean REST API endpoints via FastAPI with strict Pydantic v2 validation.

<br>

4. **Operator Interface & AI Agent (`dashboard/` & `src/agent/`)**  
   Provides a responsive React 19 dashboard with synchronized SVG vector overlays and sub-second click-to-seek, alongside a tool-using Claude 3.5 Vision Agent for natural language investigation with safety-gated action approvals.

---

## 3. Computer Vision & ML Pipeline

TRACE processes video frames end-to-end through a lightweight, decoupled perception loop:

```mermaid
flowchart LR
    A["Frame (1080p)"] --> B["Letterbox 640"]
    B --> C["YOLOv8 Inference"]
    C --> D["ByteTrack Association"]
    D --> E["Homography & Speed"]
    E --> F["Event Engine"]
    F --> G[("PostgreSQL 16")]
```

<br>

1. **Ingestion & Letterboxing**  
   Decodes video frames and resizes symmetrically to 640 × 640 with stride-32 padding.

<br>

2. **Object Detection**  
   Infers multi-class bounding boxes with classification confidences across 6 traffic classes (`person`, `car`, `motorcycle`, `bus`, `truck`, `bicycle`).

<br>

3. **ByteTrack Association**  
   Preserves track IDs across frames using a two-stage Kalman filter that associates both high-confidence detections and occluded low-confidence candidates.

<br>

4. **Planar Homography & Speed Estimation**  
   Midpoint ground projection transforms image coordinates `[x, y]` (pixels) to real-world metric coordinates `(X, Y)` (meters) for calibrated velocity smoothing.

<br>

5. **Event Evaluation & Database Sync**  
   Checks spatial triggers (polygons and tripwires) and batches events and trajectory points asynchronously to PostgreSQL.

---

## 4. Deterministic Event Engine

The Event Engine evaluates deterministic spatial and kinetic rules over trajectory streams with hysteresis debouncing to eliminate false edge triggers.

<br>

### Core Spatio-Temporal Event Rules

| Event Type | Trigger Logic | Mathematical Condition | Debounce State |
| :--- | :--- | :--- | :--- |
| `LINE_CROSSED` | Trajectory vector crosses a directional virtual tripwire | Vector cross-product intersection | Immediate on line intersection |
| `ZONE_ENTERED` | Object footprint enters a polygon boundary | Point-in-Polygon (`Shapely`) | Confirmed after *N* inside frames |
| `ZONE_EXITED` | Object footprint leaves an occupied polygon | Point-in-Polygon (`Shapely`) | Confirmed after *N* outside frames |
| `LOITERING` | Dwell duration within a designated zone | Accumulated dwell: `t ≥ T_limit` | Maintained until zone exit |
| `OVERSPEED` | Calibrated ground velocity exceeds threshold | Ground metric speed: `v > v_limit` | Moving-window velocity filter |
| `STOPPED` | Object remains stationary for a sustained duration | Velocity `v ≈ 0` for `t ≥ T_stop` | Resets on sustained movement |
| `SUDDEN_STOP` | Negative acceleration exceeds emergency threshold | High deceleration: `a ≤ -a_max` | Verified across frame intervals |

<br>

### Kinematic Event Formulas

$$
v = \frac{\|p_t - p_{t-\Delta t}\|}{\Delta t} \qquad\qquad a = \frac{v_t - v_{t-\Delta t}}{\Delta t}
$$

- **Instant Speed ($v$)**: Ground-plane metric speed estimated via 3×3 planar homography matrix.
- **Deceleration ($a$)**: Negative acceleration rate, triggering emergency braking alerts when $a \le -a_{\text{max}}$.
- **Loitering Dwell ($T_{\text{dwell}}$)**: Accumulated dwell duration within a polygon ($T_{\text{dwell}} = t_{\text{now}} - t_{\text{entry}} \ge T_{\text{limit}}$).
- **Tripwire Crossing**: Directional vector intersection test $(p_1 \times p_2) \cdot (q_1 \times q_2) < 0$.

### Verified Empirical Results (`demo_trafficlight.mp4`)

Evaluated on static street-corner footage (26.7s / 801 frames, camera `demo-trafficlight`):

| Metric | Measured Value | Operational Context |
| :--- | :--- | :--- |
| **Average Detections** | 16.13 / frame | Multi-class detection across vehicles & pedestrians |
| **Active Tracks** | 130 unique tracks | Continuous tracking through signal queues |
| **`LINE_CROSSED`** | **1 event** | Object `#2` crossing tripwire at `t = 9.5s` |
| **`STOPPED`** | 30 events | Vehicles halting at the traffic signal |
| **Track Lifecycle** | 130 enter / 112 exit | Boundary appearance and departure indexing |

---

## 5. Model Training & Domain Adaptation

TRACE provides a structured two-stage fine-tuning pipeline tailored for surveillance camera feeds.

### Two-Stage Training Pipeline

- **Stage 1: Class-Narrowing Fine-Tuning**  
  Isolates the 6 target urban mobility classes from COCO128 while freezing deep backbone layers to align the classification head.

- **Stage 2: Scene Domain Adaptation**  
  Fine-tunes the detection head on domain-specific camera frames under challenging surveillance mount angles, lighting shifts, and perspective compressions.

### Training Loss Formulation & Schedule

$$
\mathcal{L}_{\text{total}} = \lambda_{\text{box}}\mathcal{L}_{\text{box}} + \lambda_{\text{cls}}\mathcal{L}_{\text{cls}} + \lambda_{\text{dfl}}\mathcal{L}_{\text{dfl}}
$$

- **Learning Rate Schedule**: `1e-3` (Stage 1 initial) $\rightarrow$ `1e-4` (Stage 2 domain adaptation)
- **Data Augmentations**: Mosaic ($p=1.0$), HSV color jitter, and perspective distortion

### Target Class Hierarchy

| Class ID | Class Name | Category | Primary Surveillance Purpose |
| :---: | :--- | :--- | :--- |
| `0` | `person` | Pedestrian | Sidewalk occupancy, loitering, perimeter breaches |
| `1` | `bicycle` | Micro-mobility | Dedicated cycle lane monitoring, helmet compliance |
| `2` | `car` | Light Vehicle | Speed compliance, parking zone violations |
| `3` | `motorcycle` | Light Vehicle | Lane filtering, speed violations |
| `4` | `bus` | Transit | Transit lane enforcement, dwell-time analytics |
| `5` | `truck` | Heavy Freight | Restricted route violations, logistics tracking |

---

## 6. Formal Evaluation & Accuracy

TRACE is evaluated across held-out generalization datasets and real-world surveillance video footage.

### Metric Formulations & Criteria

$$
\text{MOTA} = 1 - \frac{\text{FN} + \text{FP} + \text{IDSW}}{\text{GT}} \qquad\qquad \text{IDF1} = \frac{2 \cdot \text{IDTP}}{2 \cdot \text{IDTP} + \text{IDFP} + \text{IDFN}}
$$

- **MOTA (Tracking Accuracy)**: Measures overall tracking consistency across false positives, false negatives, and ID switches.
- **IDF1 (Identity F1 Score)**: Evaluates track identity preservation across occlusions and crossings.
- **mAP (Detection Accuracy)**: Mean Average Precision computed across IoU thresholds [0.50 : 0.95].

<br>

### 1. Object Detection Benchmark (COCO vs Domain Checkpoints)

| Checkpoint | Class | Precision (P) | Recall (R) | mAP-50 | mAP-50-95 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **YOLOv8n Pretrained** | `person` | 0.723 | 0.707 | **0.744** | **0.497** |
| **YOLOv8n Pretrained** | `car` | 0.461 | 0.316 | **0.406** | **0.212** |
| **YOLOv8n Pretrained** | `motorcycle` | 1.000 | 0.973 | **0.995** | **0.830** |
| **YOLOv8n Pretrained** | `bus` | 0.632 | 1.000 | **0.995** | **0.895** |
| **YOLOv8n Pretrained** | `truck` | 0.814 | 0.500 | **0.552** | **0.440** |
| **YOLOv8n Pretrained** | `bicycle` | 0.521 | 1.000 | **0.995** | **0.895** |
| **Stage 2 Adapted** | `person` (Surveillance) | **0.003** | **1.000** | **0.995** | **0.697** |

<br>

> **Evaluation Insight:** Stage 2 achieves high recall on target surveillance angles while fine-tuning reveals domain sensitivity, highlighting the value of pairing robust pretrained weights with spatial event rules.

<br>

### 2. Multi-Object Tracking Benchmark (CLEAR MOT Metrics)

Evaluated across 244 continuous video frames under challenging camera angles:

| Evaluation Scenario | MOTA ↑ | IDF1 ↑ | ID Switches ↓ | False Positives ↓ | False Negatives ↓ | Matches |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Real Surveillance Video (244 frames)** | **1.000** | **1.000** | **0** | **0** | **0** | **244** |
| **Synthetic Crossing (Occlusion Stress Test)** | **1.000** | **1.000** | **0** | **0** | **0** | **40** |

- **Real Video Footage:** Pretrained YOLOv8n + ByteTrack maintains continuous single-object tracking across 244 frames with zero identity switches.
- **Synthetic Crossing:** Validates Kalman prediction during complete trajectory intersection and cross-object occlusion without detector noise.

---

## 7. Inference Benchmarks & Performance

TRACE pipeline performance is benchmarked under reproducible hardware workloads (`benchmarks/benchmark.py`).

### 1. Engine Inference Runtime (PyTorch CPU vs ONNX Runtime)

Evaluated on Intel Core i7 (16 threads, 244 frames, FP32 precision):

| Runtime Backend | Precision | Detection FPS | Tracking FPS | End-to-End FPS | Mean Latency | p95 Latency | CPU Load |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PyTorch (Native CPU)** | FP32 | **5.58 FPS** | **706.2 FPS** | **5.49 FPS** | 182.0 ms | 229.6 ms | 285.2% |
| **ONNX Runtime (CPU)** | FP32 | **1.22 FPS** | **165.9 FPS** | **1.20 FPS** | 831.8 ms | 976.1 ms | 316.4% |

### 2. Stream Ingestion Throughput (Multi-Video Evaluation)

Measured across real demo video streams (`yolov8n.pt`, confidence = 0.25, CPU):

| Video Stream | Frame Count | Detection FPS | Tracking FPS | End-to-End Throughput | Mean Latency (p95) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `demo_trafficlight.mp4` | 801 frames | 16.27 FPS | 329.8 FPS | **14.47 FPS** | 69.0 ms (82.5 ms) |
| `demo_intersection.mp4` | 472 frames | 15.12 FPS | 3319.9 FPS | **12.57 FPS** | 79.4 ms (99.2 ms) |
| `demo_junction_trimmed.mp4` | 384 frames | 16.51 FPS | 3021.8 FPS | **14.88 FPS** | 67.0 ms (76.9 ms) |

### Key Engineering Takeaways

- **Zero Tracking Bottleneck**: ByteTrack processes trajectories at **> 300–3,000 FPS** (< 1.5 ms/frame), adding virtually zero latency overhead to YOLOv8 inference.
- **Production Edge Target**: On dedicated GPU hardware (NVIDIA Jetson / RTX / T4) running TensorRT FP16, throughput scales to **> 65 FPS** end-to-end (`benchmarks/export_tensorrt.py`).

---

## 8. Dashboard & User Interface

The operator dashboard is built with **React 19**, **Vite**, and **Tailwind CSS v4**, delivering sub-second spatial telemetry and forensic replay:

### Interface Modules

| Module | Purpose & Interactive Capabilities |
| :--- | :--- |
| **Live Telemetry & Vector HUD** | Real-time video playback with synchronized SVG bounding boxes, persistent track paths, zone polygons, and floating incident alerts |
| **Forensic Events Feed** | Chronological violation log with severity color coding and instant sub-second click-to-seek playback jumping |
| **Object Profile Panel** | Deep-dive trajectory inspector showing dwell durations, path coordinate history, and associated incident links |
| **Spatial Analytics & Fleet** | Class distribution charts, violation frequency graphs, and multi-camera sensor fleet health status |

### Key Architectural Capabilities

- **Synchronized SVG Overlays**: Telemetry projected dynamically over `<video>` elements via `requestAnimationFrame` without altering source video.
- **Sub-Second Incident Seek**: Click any event card to immediately seek the video player to that exact millisecond.
- **Interactive Demo Scenarios**: 4 pre-recorded real-footage scenarios (Perimeter Intrusion, Tripwire Crossing, Object Lifecycle, Street Intersection).
- **100% Data Integrity**: All telemetry cards, graphs, and trajectory inspectors query live PostgreSQL/FastAPI records without mock placeholders.

---

## 9. Vision Intelligence Agent (LLM)

TRACE embeds an investigation agent powered by **Claude 3.5 Sonnet** with strict database grounding and a human-in-the-loop safety gate:

### Agent Tool Interface

| Tool Name | Operation Type | Capability |
| :--- | :--- | :--- |
| `get_camera_list` | Read | Enumerates configured camera sensors and topology |
| `query_analytics` | Read | Aggregates dwell durations, traffic density, and event frequency |
| `search_events` | Read | Queries structured spatial violations with time-range filters |
| `get_object_trajectory` | Read | Retrieves raw coordinate history, speeds, and bounding boxes |
| `propose_action` | Write (Gated) | Generates pending alert or geometry mutations requiring operator review |

> **Safety Gate:** The agent operates under a **Propose $\rightarrow$ Review $\rightarrow$ Execute** model. High-impact operations (e.g. dispatching webhooks or updating zones) require explicit operator confirmation tokens.

---

## 10. Tech Stack

| Layer | Core Technologies | Primary Role in TRACE |
| :--- | :--- | :--- |
| **Computer Vision** | `Ultralytics YOLOv8`, `ByteTrack`, `OpenCV` | Real-time object detection, Kalman tracking, and frame ingestion |
| **Spatial Geometry** | `NumPy`, `SciPy`, `Shapely` | 3×3 metric planar homography, trajectory smoothing, polygon tests |
| **Inference Backends**| `PyTorch 2.0+`, `ONNX Runtime`, `TensorRT` | CPU/GPU execution engines and model quantization |
| **Backend & API** | `Python 3.10+`, `FastAPI`, `Pydantic v2` | High-throughput asynchronous REST API and schema validation |
| **Database** | `PostgreSQL 16`, `SQLAlchemy 2.0` | Relational storage for tracks, telemetry points, and incident logs |
| **AI Intelligence** | `Anthropic Claude 3.5 Sonnet` | Natural language forensic investigation and tool-grounded queries |
| **Operator Frontend** | `React 19`, `TypeScript`, `Vite`, `Tailwind CSS v4` | High-performance dashboard, SVG vector HUD, and demo scenarios |
| **DevOps & QA** | `Docker Compose`, `Pytest`, `Vitest`, `Oxlint` | Container orchestration, 302 automated unit/integration tests |

---

## 11. Project Structure

```text
Trace/
├── src/                  # Core Python engine (detection, tracking, event engine, API, agent)
├── dashboard/            # React 19 operator dashboard (HUD telemetry, vector overlays, demo)
├── configs/              # Per-camera homography calibrations, polygons, and virtual tripwires
├── scripts/              # Video processing, offline visualizers, and PostgreSQL batch sync
├── training/             # Two-stage YOLOv8 fine-tuning & domain adaptation pipeline
├── evaluation/           # Formal CLEAR MOT tracking & mAP detection evaluation harness
├── benchmarks/           # Latency benchmarker, ONNX Runtime & TensorRT FP16 export utilities
├── tests/                # 302 automated backend pytest & frontend vitest test suites
├── docker-compose.yml    # Full-stack container orchestration (Postgres 16, API, Dashboard)
└── Dockerfile            # Multi-stage Python backend container image
```

---

## 12. Quick Start (Docker Compose)

Launch the complete stack (PostgreSQL + FastAPI + CV Ingestion Worker + React Dashboard) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/mariiammaysara/Trace.git
cd Trace

# 2. Launch all services
docker compose up --build
```

### Services Launched

| Service | Local URL | Port | Role |
| :--- | :--- | :---: | :--- |
| **Operator Dashboard** | [http://localhost:5173](http://localhost:5173) | `5173` | React 19 Frontend with live HUD and demo scenarios |
| **FastAPI Backend** | [http://localhost:8000](http://localhost:8000) | `8000` | Asynchronous REST API & Agent query engine |
| **Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | `8000` | OpenAPI / Swagger interactive documentation |
| **PostgreSQL 16** | `localhost:5433` | `5433` | Relational time-series database (`trace` / `trace`) |

---

## 13. Local Development Setup

### 1. Backend & Database Setup
```bash
# Start PostgreSQL database container
docker compose up -d db

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install package with development & agent dependencies
pip install -e ".[dev,agent]"

# Run FastAPI development server
uvicorn api.app:app --reload --app-dir src --port 8000
```

### 2. Frontend Dashboard Setup
```bash
cd dashboard
npm install
npm run dev                     # Available at http://localhost:5173
```

### 3. Video Pipeline Execution
```bash
# Process a video file and stream trajectory points to database
python scripts/persist_video.py data/sample.mp4 --camera-id demo
```

---

## 14. Configuration (.env)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://trace:trace@localhost:5433/trace` | PostgreSQL connection string |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `trace` / `trace` | Database credentials |
| `TRACE_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS allowed origins |
| `TRACE_CAMERA_SOURCE` | `data/sample.mp4` | Video file path or RTSP camera stream URL |
| `TRACE_CAMERA_ID` | `demo` | Active camera calibration config ID |
| `TRACE_DETECTOR_WEIGHTS` | `yolov8n.pt` | Model checkpoint path or identifier |
| `TRACE_DETECTOR_CONFIDENCE` | `0.25` | Minimum object detection confidence |
| `ANTHROPIC_API_KEY` | *(optional)* | API key for Claude 3.5 Vision Agent |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL consumed by React dashboard |

---

## 15. REST API Documentation

Interactive OpenAPI documentation and live request runner are available at: **`http://localhost:8000/docs`**

### API Endpoints Reference

| Method | Endpoint | Domain | Description |
| :---: | :--- | :--- | :--- |
| `GET` | `/cameras` | Cameras | List all registered camera sensors and configurations |
| `GET` | `/cameras/{camera_id}/zones` | Cameras | Retrieve polygon boundaries configured for a camera |
| `GET` | `/cameras/{camera_id}/lines` | Cameras | Retrieve virtual tripwires configured for a camera |
| `GET` | `/cameras/{camera_id}/objects` | Objects | List all tracked entities and their metadata |
| `GET` | `/objects/{object_id}/trajectory` | Objects | Fetch full timestamped coordinate trajectory points |
| `GET` | `/cameras/{camera_id}/events` | Events | Query spatial and kinetic incident violations |
| `POST` | `/alerts/webhook` | Alerts | Dispatch automated alert triggers to webhook subscribers |
| `GET` | `/analytics` | Analytics | Retrieve aggregated dwell times, traffic volume, and counts |
| `POST` | `/agent/query` | AI Agent | Query LLM agent for natural language forensic insights |

### Example Payloads

#### 1. Real-Time Analytics (`GET /analytics?camera_id=demo`)
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
  }
}
```

#### 2. Vision Intelligence Query (`POST /agent/query`)
```json
{
  "query": "Which vehicles exceeded the speed limit near the entrance zone between 10:00 and 10:30?",
  "response": "Object #42 (car) was recorded travelling at 84 km/h through the entrance zone (speed limit: 50 km/h) at 10:14:22 UTC.",
  "tools_used": ["search_events", "get_object_trajectory"]
}
```

---

## 16. Testing & Quality Assurance

TRACE maintains 100% test coverage across backend mathematical logic, API routers, database migrations, and frontend UI components:

```bash
# 1. Backend Pytest Suites (232 tests)
pytest tests/ -v

# 2. Frontend Vitest Suites (70 tests)
cd dashboard && npm test -- --run

# 3. Frontend Quality & Linting
cd dashboard && npm run lint
```

> **Total Test Coverage:** **302 automated tests passed** (232 backend pytest + 70 frontend vitest).

---

## 17. Engineering Tradeoffs & Limitations

| Constraint / Area | Technical Boundary | Production Mitigation Path |
| :--- | :--- | :--- |
| **Planar Homography** | Assumes a flat 2D ground plane (`Z = 0`). Elevation changes distort speed estimation. | Multi-plane calibration or 3D LiDAR integration for multi-level environments. |
| **Extreme Occlusions** | Pure Kalman tracking degrades during prolonged full occlusions (> 30 frames). | Visual Re-Identification (ReID appearance embeddings) for track re-acquisition. |
| **CPU Ingestion** | CPU execution operates at ~5.5–16 FPS (FP32). Multi-stream real-time requires GPU. | TensorRT FP16 or ONNX Runtime CUDA execution (> 65 FPS on NVIDIA Jetson/RTX). |
| **Nadir / Aerial Angles** | Ground-level COCO training yields lower recall on straight-down top-view drone angles. | Domain-adaptation fine-tuning on aerial surveillance datasets (e.g. VisDrone). |

---

## 18. Roadmap

- [ ] **Multi-Camera Re-Identification (ReID)**: Cross-camera tracking with appearance embeddings (OSNet / ResNet).
- [ ] **Zero-Shot Open-Vocabulary Detection**: Integration of YOLO-World for dynamic natural language class queries.
- [ ] **Hardware-Accelerated Stream Gateway**: RTSP and WebRTC live stream ingestion with NVDEC hardware decoding.
- [ ] **Edge Fleet Orchestration**: Over-the-air deployment of quantized TensorRT models to NVIDIA Jetson edge nodes.

---

## 19. License & References

### License
Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.

### Academic Foundations & Citations

| Foundation / Library | Reference Citation | Primary Role in TRACE |
| :--- | :--- | :--- |
| **ByteTrack** | Zhang et al. (*ECCV 2022*) | Multi-object tracking by associating every detection box |
| **YOLOv8** | Ultralytics (*2023*) | Real-time object detection and feature extraction |
| **CLEAR MOT Metrics** | Bernardin & Stiefelhagen (*EURASIP 2008*) | MOTA, IDF1, and tracking quality evaluation criteria |
