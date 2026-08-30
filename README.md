# Track — Real-Time Object Detection & Tracking System

A computer vision pipeline combining YOLO-based detection with ByteTrack for persistent multi-object tracking across video frames. Generates live analytics — line-crossing counts and zone dwell-time — through a lightweight interface displaying tracked bounding boxes and a real-time stats dashboard.

## Overview

Track takes a video stream (live camera or uploaded file) and performs detection + tracking on target objects (e.g. people or vehicles), producing real-time statistics such as counts, movement direction, and dwell time.

## Project Plan

### 1. Define Use Case & Data
Pick one specific scenario instead of "generic detection" — e.g. crowd counting in a space, vehicle tracking on a street, or customer movement in a store. The chosen scenario determines the right dataset and object classes. If no private data is available, use public videos (YouTube) or datasets like MOT Challenge for testing.

### 2. Choose the Detection Model
Use YOLOv8 or YOLOv11 (Ultralytics) — pretrained on COCO, covering common classes like `person` and `car` out of the box. If the use case needs a class not in COCO, fine-tune on a small custom dataset.

### 3. Add Tracking
Combine the detection model with a tracking algorithm such as ByteTrack or DeepSORT, so each object keeps a persistent ID across frames (not just per-frame detection). This is what turns the project from "detection" into real "tracking," enabling direction and count calculations.

### 4. Build the Analytics Layer
On top of tracking, implement:
- **Line crossing** — count objects that cross a defined line
- **Dwell time** — measure how long each object spends in a frame or zone

This layer is what turns the project from a technical demo into a tool with clear practical value.

### 5. Interface & Display
Build a lightweight interface (Streamlit, or FastAPI + simple frontend) that shows:
- Live video with bounding boxes and tracking IDs
- A small stats dashboard (counts, movement-over-time chart)

### 6. Documentation & Publishing
- Architecture diagram
- Trade-off notes (why YOLO over other models, why ByteTrack over DeepSORT)
- Short demo video or GIF

## Tech Stack

| Component | Choice |
|---|---|
| Detection | YOLOv8 / YOLOv11 (Ultralytics) |
| Tracking | ByteTrack or DeepSORT |
| Interface | Streamlit / FastAPI |
| Data | Custom footage or MOT Challenge dataset |

## Status

🚧 In planning / early development
