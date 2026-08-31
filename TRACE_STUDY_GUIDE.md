# TRACE — Study Guide

> **Status legend used throughout this document:**
> `[IMPLEMENTED]` — exists in the current codebase and works.
> `[PLANNED]` — designed, not yet built.
> `[OPTIONAL]` — nice-to-have, not required for the core system.
>
> **Current project status: pre-implementation.** Everything below is `[PLANNED]` unless a later update marks it `[IMPLEMENTED]`. This file is meant to be updated phase-by-phase as TRACE is actually built — treat any `[IMPLEMENTED]` tag you see later as a promise that the described code really exists at the referenced path.

## Table of Contents

0. [TRACE at a Glance](#0-trace-at-a-glance)
1. [Computer Vision Foundations](#1-computer-vision-foundations)
2. [Object Detection](#2-object-detection)
3. [Multi-Object Tracking](#3-multi-object-tracking)
4. [Trajectory & Motion Analysis](#4-trajectory--motion-analysis)
5. [Camera Geometry](#5-camera-geometry)
6. [Speed Estimation](#6-speed-estimation)
7. [Event Engine](#7-event-engine)
8. [Video Processing](#8-video-processing)
9. [Data & Database](#9-data--database)
10. [Backend](#10-backend)
11. [Analytics](#11-analytics)
12. [Vision Agent](#12-vision-agent)
13. [Agent Actions & Safety](#13-agent-actions--safety)
14. [Production Computer Vision](#14-production-computer-vision)
15. [Evaluation](#15-evaluation)
16. [Testing](#16-testing)
17. [Failure Cases & Debugging](#17-failure-cases--debugging)
18. [TRACE Architecture Deep Dive](#18-trace-architecture-deep-dive)
19. [Implementation Map](#19-implementation-map)
20. [Experiments](#20-experiments)
21. [Interview Preparation](#21-interview-preparation)

---

## 0. TRACE at a Glance

### What TRACE is

TRACE is a real-time **video intelligence system**: it watches video (live camera or file), detects objects, tracks them frame-to-frame with stable IDs, turns their motion into structured events (crossed a line, entered a zone, sped, loitered...), stores everything in a queryable database, and lets a user — human or LLM agent — ask questions about what happened and get evidence-backed answers.

It is **not** "run YOLO on a video." The detector is the smallest, most replaceable part of the system. The value is in everything built on top of it: tracking, semantics, storage, and querying.

### What problem it solves

Raw video is not data. A security guard staring at 12 monitors cannot reconstruct "how many people entered the loading dock between 2–3pm" without watching hours of footage. TRACE converts continuous pixels into discrete, queryable facts, so that question becomes a database query (or a sentence to an agent) instead of a manual review task.

### Real-world use cases

| Use case | Example event |
|---|---|
| Perimeter / restricted-area security | `ZONE_ENTERED` on a restricted zone at night |
| Traffic monitoring | `OVERSPEED`, vehicle counts per lane |
| Retail / footfall analytics | dwell time in front of a display, queue length |
| Parking / access control | `LINE_CROSSED` at a gate, IN/OUT counts |
| Loitering / suspicious behavior detection | `LOITERING` near an entrance |

### Final capabilities (target state)

- Detect and track multiple object classes in real time.
- Maintain per-object trajectories and derive motion statistics.
- Detect configurable semantic events (lines, zones, speed, loitering, stops).
- Persist everything relationally for later investigation.
- Serve analytics and raw data over a REST API.
- Visualize live detections/tracks/zones and browse events in a dashboard.
- Answer natural-language questions about the video history via a tool-using LLM agent, grounded in real stored data — never hallucinated.
- Take approved, validated actions (alerts, configuration changes) triggered by the agent.
- Report real, measured performance numbers (FPS, latency, memory) and real tracking/detection accuracy metrics.

### Complete architecture (high level)

```text
                    ┌──────────────┐
Camera / Video ────►│  CV Pipeline │  (detector + tracker + trajectory + geometry)
                    └──────┬───────┘
                           ↓
                     Event Engine   (deterministic, rule-based, no LLM)
                           ↓
                     PostgreSQL     (cameras, tracks, events, zones, lines...)
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
         FastAPI + Dashboard       Vision Agent (LLM + tools)
              ↓                         ↓
          Analytics UI            Grounded answers / approved actions
```

### End-to-end data flow (one frame's journey)

1. A frame arrives from a video file or camera (`src/detection` input layer).
2. The detector returns boxes + classes + confidences for that frame.
3. The tracker matches these detections against existing tracks (or creates new ones), producing stable `object_id`s.
4. Trajectory module appends the new point to that object's track history and recomputes velocity/direction/dwell time.
5. Geometry module can convert pixel positions to real-world estimates if calibration is configured.
6. Event engine evaluates rules against the updated track (crossed a line? entered a zone? overspeed?) and emits structured events.
7. Events + track points are written to PostgreSQL.
8. Analytics queries and the dashboard read from the same database.
9. The agent, when asked a question, calls tools that query this same database — it never looks at raw video itself.

### Why each component exists (one line each)

- **Detector** — turns pixels into "there is an object here."
- **Tracker** — turns "an object here" into "this specific object, over time."
- **Trajectory module** — turns positions-over-time into motion facts (speed, direction, dwell).
- **Geometry module** — corrects for the fact that pixels ≠ real-world distances.
- **Event engine** — turns motion facts into business-meaningful, discrete events.
- **Database** — makes events and tracks queryable and investigable after the fact.
- **API** — exposes the database and pipeline in a standard, decoupled way.
- **Dashboard** — makes the system usable by a human without writing queries.
- **Agent** — makes the system usable in natural language, grounded in the same data everyone else uses.

### What I should know
- [ ] I can describe TRACE's pipeline end-to-end from memory, in order.
- [ ] I can explain why TRACE is a "system," not a "model."
- [ ] I can name every major component and its single responsibility.

### Questions to test myself
1. Why is the detector described as "the smallest, most replaceable part" of TRACE?
2. What is the difference between raw tracking data and an "event" in TRACE's vocabulary?
3. Why does the agent query the database instead of looking at video frames directly?

---

## 1. Computer Vision Foundations

*Only what TRACE actually needs — not a full CV course.*

### 1.1 Images, pixels, RGB/BGR

- A digital image is a grid of pixels; each pixel holds intensity values per channel.
- Color images: 3 channels. OpenCV loads/stores as **BGR**, not RGB — a classic bug source. Most deep learning frameworks (PyTorch, YOLO) expect **RGB**, so a BGR→RGB conversion is a required, easy-to-forget step at the detector's input boundary.
- **How TRACE uses it:** every frame read via OpenCV must be converted before being handed to the detector; every frame drawn on for the dashboard must stay in the color space OpenCV expects for `imshow`/encoding.

### 1.2 Frames, resolution, FPS

- A video is a sequence of frames sampled at a rate (**FPS** = frames per second).
- Resolution (e.g., 1920×1080) affects both accuracy (more detail) and compute cost (more pixels to process) — a core trade-off TRACE has to make explicit per camera.
- **How TRACE uses it:** the "processing FPS" (how fast the pipeline can run) is almost always lower than "video FPS" (how the video was recorded) unless hardware is fast enough — see [Section 8](#8-video-processing).

### 1.3 Bounding boxes and coordinates

- A bounding box locates an object: typically `(x_min, y_min, x_max, y_max)` or `(x_center, y_center, width, height)` — formats differ by framework and this is a common integration bug.
- Origin `(0,0)` is the **top-left** corner in image coordinates; y increases *downward* — the opposite of standard math/graph convention. This matters for every direction/velocity calculation later.
- **How TRACE uses it:** detector output → tracker input → trajectory module all pass boxes/centroids around; a single unnoticed format mismatch (xyxy vs xywh) silently corrupts everything downstream.

### 1.4 Image preprocessing

- Typical steps before feeding a model: resize, normalize (scale pixel values, e.g., to 0–1), color conversion, sometimes padding to preserve aspect ratio ("letterboxing").
- **How TRACE uses it:** the detector's preprocessing must exactly match what it was trained with (image size, normalization stats), or accuracy silently degrades without throwing an error.

### 1.5 Perspective (preview — full treatment in Section 5)

- A camera projects a 3D world onto a 2D image; equal pixel distances do **not** correspond to equal real-world distances unless the camera is perfectly overhead and the scene is flat.
- **How TRACE uses it:** this is *the* reason naive pixel-based speed estimation is wrong without calibration — flagged here early because it affects trajectory math, not just the dedicated geometry section.

### 1.6 IoU (Intersection over Union)

- Measures overlap between two boxes: `IoU = area(A ∩ B) / area(A ∪ B)`. Ranges 0 (no overlap) to 1 (identical).
- **Why it matters:** it is the core similarity metric used to (a) suppress duplicate detections (NMS, Section 2) and (b) match detections to existing tracks frame-to-frame (Section 3).

```text
        ┌─────────┐
        │    A    │
        │   ┌─────┼───┐
        │   │ ∩   │ B │
        └───┼─────┘   │
            └─────────┘

IoU = area(∩) / area(A ∪ B)
```

### 1.7 Basic OpenCV concepts

- `VideoCapture` — reads frames from a file or camera device/stream.
- `imshow` / `imwrite` — display/save frames (mostly for debugging, not production).
- Drawing primitives (`rectangle`, `circle`, `polylines`, `putText`) — used to render boxes, trajectories, zones, and lines onto frames for the dashboard's live view.

### What I should know
- [ ] I can explain BGR vs RGB and why it matters for TRACE's pipeline.
- [ ] I can compute IoU between two boxes by hand.
- [ ] I can explain why image coordinates have y increasing downward and why that matters for direction math.
- [ ] I can explain the difference between video FPS and processing FPS at a high level.

### Questions to test myself
1. Why does mismatched color-channel order (BGR/RGB) not throw an error, but still break the model?
2. What two box formats might a detector and tracker disagree on, and what breaks if you don't convert?
3. Why is IoU used both in NMS and in tracking — what's the common underlying need?

### Practical exercise
- Given box A = `(10, 10, 50, 50)` and box B = `(30, 30, 70, 70)`, calculate IoU by hand.

---

## 2. Object Detection

### Classification vs Detection vs Segmentation

| Task | Output |
|---|---|
| Classification | One label for the whole image |
| Detection | Boxes + labels for each object instance |
| Segmentation | Pixel-level mask per object (instance) or per class (semantic) |

TRACE needs **detection**: it must localize multiple objects per frame, not just say "a car is somewhere in this image."

### Modern object detection: YOLO family & RT-DETR

- **YOLO** ("You Only Look Once"): a single-stage CNN detector — one forward pass predicts boxes + classes + confidences directly on a grid. Fast, mature tooling, huge community — the pragmatic default for real-time systems.
- **RT-DETR**: a transformer-based real-time detector; removes the hand-tuned NMS step (end-to-end set prediction) and can match/exceed YOLO accuracy at comparable speed on some benchmarks. Newer, smaller ecosystem.
- **Why this matters for TRACE:** the detector is treated as a swappable interface (`detect(frame) -> [Detection]`), so the specific model choice should not leak into tracking/event code.

### Bounding boxes, confidence scores, NMS

- Detectors typically propose many overlapping candidate boxes per real object.
- **NMS (Non-Maximum Suppression):** keep the highest-confidence box, suppress other boxes that overlap it above an IoU threshold, repeat. This is where Section 1's IoU is used directly.
- **Confidence score:** the model's estimated probability the box contains the class it predicts; TRACE filters detections below a configurable confidence threshold before they ever reach the tracker.

### Precision, Recall, mAP

- **Precision** = TP / (TP + FP) — of everything detected, how much was correct.
- **Recall** = TP / (TP + FN) — of everything that should have been detected, how much was found.
- **mAP (mean Average Precision)** — averages precision across recall levels and classes; **mAP50** uses IoU≥0.5 to count a detection as correct, **mAP50-95** averages over IoU thresholds 0.5→0.95 (stricter, more standard for modern benchmarks).
- **Why it matters:** a high-confidence-threshold detector that misses small/occluded people (low recall) will silently under-count in TRACE's analytics — this is a real, reportable limitation, not just an academic number.

### Inference vs training

- Training: the model learns weights from labeled data (gradient descent, backprop) — TRACE does **not** train a detector from scratch by default; it uses a pretrained model and may fine-tune later if needed.
- Inference: running the already-trained model forward on new frames — this is the only thing the real-time pipeline does.

### Why we choose our detector for TRACE `[IMPLEMENTED — provisional, pending benchmarking, Section 20]`

- **Chosen for now: YOLOv8n (Ultralytics, COCO-pretrained, `yolov8n.pt`)** — the nano variant, for the same reasons Section 2 always named as the default candidate: tooling maturity, speed, ease of export to ONNX/TensorRT later (Section 14), and it needed zero training to get a working Phase 2 pipeline end-to-end.
- **This is a provisional pick, not a final one.** It has not been benchmarked against RT-DETR or larger YOLO variants (s/m/l) on real TRACE-like scenes — that comparison is still `[PLANNED]` for Section 20. Nano was chosen purely to get inference working fast; Phase 13 (Benchmarks) is where FPS/accuracy trade-offs actually get measured and this choice gets revisited.
- RT-DETR remains the documented alternative to benchmark against once real accuracy/FPS numbers are needed.

### Where this is implemented `[IMPLEMENTED]`

- `src/detection/detector.py` — `Detection` (dataclass: `bbox`, `class_name`, `confidence`, `frame_id`, `timestamp`) and the abstract `Detector` interface (`detect(frame: Frame) -> list[Detection]`), so the concrete model stays swappable per this section's design decision above.
- `src/detection/yolo_detector.py` — `YoloDetector(Detector)`: `__init__(model_path: str = "yolov8n.pt", confidence_threshold: float = 0.25, class_allowlist: tuple[str, ...] | None = DEFAULT_CLASS_ALLOWLIST, device: str | None = None)`. `DEFAULT_CLASS_ALLOWLIST = ("person", "car", "motorcycle", "bus", "truck", "bicycle")`. Confidence filtering is delegated to Ultralytics' own `conf=` parameter (NMS included); class-allowlist filtering happens after, by class name.
- `Detection.bbox` is **xyxy**: `(x_min, y_min, x_max, y_max)` in absolute pixel coordinates of the source frame, top-left origin — documented explicitly in the dataclass docstring since Section 1.3 flags xyxy/xywh mismatches as a classic bug.
- **A real color-space trap found and handled here:** `Frame.image` is RGB (Phase 1's boundary conversion), but Ultralytics' numpy-array `predict()` path assumes a BGR array and flips it internally (`BasePredictor.preprocess`, confirmed by reading the Ultralytics source) — feeding it `Frame.image` directly would silently double-flip the channels. `YoloDetector.detect()` converts RGB back to BGR immediately before calling `predict()` for exactly this reason. This is the same class of bug Section 1.1 describes in the abstract; this is where it actually showed up.
- `scripts/detect_video.py` — CLI wiring `FrameSource` → `YoloDetector` → drawn boxes, either saved to `--output <path>` (`cv2.VideoWriter`) and/or shown live with `--display`; also takes `--frame-skip`, `--confidence`, `--classes`, `--model`.
- `tests/test_detector.py` — 5 tests against a fake `ultralytics.YOLO` (monkeypatched, no weights download) covering allowlist filtering, confidence-threshold pass-through, and invalid-input errors; 1 integration test running the real pretrained model against real fixture frames, asserting only that returned `Detection` objects are well-formed (valid bbox ordering, confidence in `[0, 1]`, non-empty class name) — never asserting specific detections, since YOLO output on arbitrary frames isn't deterministic enough to pin down.
- Downloaded weights (e.g. `yolov8n.pt`) are gitignored (`*.pt`, `*.onnx`, `*.engine`) — Ultralytics fetches them on first use, they are not committed as source.

### Observed limitations (Phase 2 testing)

*Recorded here from manual testing of `YoloDetector`/`scripts/detect_video.py` against a real ~8s/244-frame webcam clip (`data/sample.mp4`, gitignored/local-only), person class only. Not yet moved into Section 17 (Failure Cases & Debugging) because that section doesn't exist in this guide yet — link/move these there once it does.*

- **Vertical box undershoot.** Across every sampled frame, the bottom edge of the `person` box consistently lands around mouth/chin height instead of extending to include the visible chin/neck — a small but consistent bias toward a too-short box on a close, partially-out-of-frame subject.
- **Duplicate detection at frame 241** (t≈16.067s): two overlapping `person` boxes returned for the same real person in the same frame — one at confidence 0.7x covering the full head, and a second at confidence 0.28 covering just the left portion of the hair. Looks like an NMS near-miss: the two candidate boxes' IoU likely sat just under the suppression threshold, plausibly triggered by hair motion blur in that frame.
- **No false positives on background** — the wardrobe, ceiling fan, and wall were never spuriously boxed in any sampled frame across the clip.

### What I should know
- [ ] I can explain detection vs classification vs segmentation in one sentence each.
- [ ] I can explain what NMS removes and why it's needed.
- [ ] I can explain mAP50 vs mAP50-95 and why the stricter one is more informative.
- [ ] I can explain why TRACE treats the detector as swappable rather than hard-wired.

### Questions to test myself
1. Why would two overlapping boxes for the same real object appear before NMS?
2. If precision is high but recall is low, what does that mean is happening in TRACE's counts?
3. What's the practical (not academic) reason to keep the detector behind an interface?

---

## 3. Multi-Object Tracking

*One of the deepest sections — this is TRACE's technical core.*

### Detection vs tracking

- Detection answers "what's in this frame" independently, frame by frame — it has **no memory**.
- Tracking answers "which object in frame N is the same object as in frame N-1" — it adds **identity over time**. Without tracking, TRACE cannot compute trajectories, dwell time, or "this same person crossed the line."

### Single-object vs multi-object tracking (SOT vs MOT)

- SOT: track one target given an initial box (common in surveillance-follow use cases).
- MOT: track an unknown, changing number of objects simultaneously — this is TRACE's requirement, and it's substantially harder because of the **data association** problem below.

### Track IDs and track lifecycle

Every tracked object has a lifecycle:

```text
New detection, no match → Track CREATED (new ID)
Matched to existing track each frame → Track UPDATED
No matching detection for N frames → Track LOST (may be re-found)
Lost beyond a timeout → Track TERMINATED
```

### Data association: the core MOT problem

Given a set of new detections and a set of existing tracks, decide which detection belongs to which track. Two ingredients:

1. **Similarity/cost between a detection and a track** — commonly IoU between the track's *predicted* box and the new detection's box, sometimes combined with appearance embeddings.
2. **Optimal assignment** — the **Hungarian Algorithm** solves this as a bipartite matching problem, minimizing total cost (or maximizing total IoU) in polynomial time, instead of greedily and sub-optimally pairing them.

### Kalman Filter

- A recursive estimator that predicts an object's next position/velocity from its motion history, then corrects that prediction once a real detection arrives.
- **Why it matters for tracking:** it gives the tracker a *predicted* box to match against even when detection is momentarily noisy, and it lets a track survive a frame or two of missed detection (brief occlusion) by coasting on the prediction.
- Intuition: predict → measure → blend (weighted by how much you trust each) → repeat.

### SORT → DeepSORT → ByteTrack → BoT-SORT (evolution)

| Tracker | Key idea | Limitation it fixes |
|---|---|---|
| **SORT** | Kalman filter + IoU + Hungarian algorithm, nothing else | Very fast but loses identity easily under occlusion (no appearance info) |
| **DeepSORT** | Adds a learned appearance embedding (re-ID) to the matching cost | Reduces ID switches under occlusion, at the cost of extra compute |
| **ByteTrack** | Key insight: **don't throw away low-confidence detections** — match high-confidence boxes first, then try to match remaining tracks against the low-confidence leftovers (often real but partially-occluded objects) | Recovers objects that would otherwise be dropped as "noise," without needing an appearance model |
| **BoT-SORT** | ByteTrack's association strategy + stronger motion compensation (handles camera movement) + optional appearance embedding | Better under camera motion / crowded scenes than plain ByteTrack |

TRACE's default candidates are **ByteTrack** and **BoT-SORT** specifically because both are fast enough for real-time and don't strictly require a heavy re-ID network to get good results — matching the "real-time" constraint in TRACE's name.

### Occlusion, ID switches, track fragmentation

- **Occlusion** — an object is temporarily hidden behind another; a naive tracker will terminate its track and assign a **new ID** when it reappears.
- **ID switch** — the tracker assigns one object's established ID to a *different* object (common when two similar objects cross paths).
- **Track fragmentation** — one real object's continuous presence gets split into several separate track IDs over time. All three degrade every downstream calculation (dwell time, trajectory, "count of unique people") and must be reported as real, measured limitations, not hidden.

### MOTA and IDF1

- **MOTA (Multi-Object Tracking Accuracy)** — combines false positives, missed detections (misses), and ID switches into one score; heavily influenced by detection quality, not just tracking quality.
- **IDF1** — measures how well predicted IDs match ground-truth identities over the *whole* track lifetime (harmonic mean of ID-precision and ID-recall) — more sensitive specifically to identity consistency than MOTA.
- **Why both:** MOTA can look fine even with several ID switches if detection is otherwise strong; IDF1 exposes identity-consistency problems that matter most for TRACE's "same object over time" use cases (dwell time, unique counts).
- **`[PLANNED]` — not computed yet.** MOTA/IDF1 both require ground-truth tracking annotations (which real object each track_id *should* be, frame by frame) that TRACE does not have yet. Phase 3 testing checked only qualitative ID stability on synthetic sequences and one real clip (see Observed limitations below), never a numeric MOTA/IDF1 score. Computing these for real is explicitly deferred to the evaluation phase (Section 15) once an annotated tracking dataset exists — no numbers are faked or estimated here in the meantime.

### Why we choose our tracker for TRACE `[IMPLEMENTED — provisional, pending benchmarking, Section 20]`

- **Chosen for now: ByteTrack**, over BoT-SORT, because this phase's target scene (a mostly-static single camera, no significant camera motion) doesn't need BoT-SORT's extra machinery (camera-motion compensation, optional appearance/ReID embedding) — ByteTrack's plain motion (Kalman) + IoU + Hungarian matching, plus its core trick of giving low-confidence detections a second chance instead of discarding them, is the simpler tool that already fits. Revisit if/when TRACE needs to handle real camera motion or heavier occlusion.
- **Build vs. reuse:** implemented by wrapping `ultralytics.trackers.byte_tracker.BYTETracker` — the same, already-battle-tested implementation that backs `model.track()` everywhere Ultralytics is used — rather than writing our own Kalman filter and Hungarian-algorithm matching from scratch. This was a deliberate trade-off, decided explicitly rather than defaulted into: a from-scratch implementation would have real learning/portfolio value (Section 3 is TRACE's technical core, and its own self-check list below expects genuine understanding of the Kalman predict→correct cycle and why Hungarian beats greedy matching), but a hand-rolled tracker is also meaningfully more code and more surface area for the exact subtle bugs (ID switches, track drift) a mature library has already had years to shake out. Reuse won for Phase 3; understanding what's inside `BYTETracker` remains a "should be able to explain this" goal regardless of who wrote the code running it.
- This is a provisional pick like the detector choice in Section 2 — not yet benchmarked (MOTA/IDF1, real occlusion-heavy footage) against BoT-SORT or a from-scratch implementation. That comparison is `[PLANNED]` for Section 20.

### Where this is implemented `[IMPLEMENTED]`

- `src/tracking/tracker.py` — `Track` (dataclass: `object_id`, `class_name`, `bbox` xyxy pixel coords, `confidence`, `timestamp`, `frame_id`) and the abstract `Tracker` interface (`update(detections: list[Detection]) -> list[Track]`), so the concrete algorithm stays swappable, mirroring Section 2's detector interface.
- `src/tracking/byte_tracker.py` — `ByteTracker(Tracker)`: `__init__(track_high_thresh=0.25, track_low_thresh=0.1, new_track_thresh=0.25, track_buffer=30, match_thresh=0.8, fuse_score=True)`. `track_buffer` is the configurable missed-frame tolerance (consecutive frames a lost track survives before termination) mentioned throughout this section.
- **`update()` must be called exactly once per video frame, in order — including empty-detections frames.** ultralytics' `BYTETracker` advances its internal Kalman time step once per `update()` call; skipping a call for a frame with zero detections would desync the tracker's notion of elapsed time from the real frame count. Documented on `Tracker.update()`'s docstring and followed in `scripts/track_video.py`.
- **A real confirmation-latency behavior found and documented here:** a brand-new track is only auto-confirmed (returned from `update()`) on the *very first* `update()` call the tracker ever receives; any track created later needs a second consecutive match before it's reported at all — standard tentative-track confirmation, so one noisy detection can't spawn a phantom track. This tripped up the first draft of Phase 3's own unit tests (an object reappearing after `track_buffer` expired was expected to be reported immediately with a new id; it actually takes one more frame to confirm) — fixed in the tests, not the tracker, since the behavior is correct.
- Matching inside `BYTETracker` is **IoU-only, not class-aware** — a detection's class never affects which track it's assigned to. `ByteTracker._to_boxes()` passes a dummy constant class id into ultralytics' `Boxes` for this reason; the real `class_name` is recovered afterward from the originating `Detection`, looked up via the source index ultralytics reports for each match — never from the dummy class id.
- `scripts/track_video.py` — CLI wiring `FrameSource` → `YoloDetector` → `ByteTracker` → drawn `id=<n> <class> <confidence>` labels, to `--output` and/or `--display`; also takes `--track-buffer`.
- `tests/test_tracker.py` — 6 tests against `ByteTracker` directly (no mocking needed — it's pure algorithm, no model weights) covering: empty-input handling, single-object id stability, field propagation from the source `Detection`, two objects crossing paths without an id swap, same-id recovery after a short occlusion, and new-id assignment after occlusion exceeds `track_buffer`; 1 integration test running `YoloDetector` → `ByteTracker` on real fixture frames, asserting only well-formed `Track` output.
- `lap` (the Hungarian-assignment library ultralytics' tracker code needs) is now pinned explicitly in `pyproject.toml` — it had been silently auto-installed by ultralytics on first import otherwise.

### Observed limitations (Phase 3 testing)

*From the same real ~8s/244-frame webcam clip used in Phase 2 testing (`data/sample.mp4`), run through `YoloDetector` → `ByteTracker` end to end.*

- **The frame-241 duplicate detection from Phase 2 testing did not produce a duplicate track.** At timestamp≈16.067s, `YoloDetector` returned 2 overlapping `person` detections that frame (confidence 0.7x and 0.28); `ByteTracker` still reported exactly 1 track (`id=1`) for that frame. Tracking absorbed a single-frame detector glitch that would have been a visible false positive at the detection layer alone — a concrete example of why Section 0 treats tracking as adding real value over raw per-frame detection, not just relabeling boxes.
- **Single stable id for the entire clip.** `id=1` was the only track id used across all 244 frames — no id switches, no fragmentation, observed in this specific low-motion, single-subject, mostly-static-camera clip. This is not evidence ByteTrack is switch-free in general; it's a clip with none of the conditions (fast motion, occlusion, multiple similar objects) that typically cause switches. Untested here: real occlusion, multiple simultaneous people, and camera motion — exactly the gaps Section 20/Phase 13 benchmarking needs to cover before this tracker choice is trusted beyond this narrow case.

### How the tracker in TRACE works, frame-by-frame `[IMPLEMENTED — this is exactly what ultralytics' BYTETracker.update() does internally]`

```text
New frame
   ↓
Run detector → raw detections (boxes, classes, confidences)
   ↓
For each existing track: Kalman filter PREDICTS its next box
   ↓
Compute cost matrix (IoU) between predicted track boxes and new detections
   ↓
Hungarian algorithm → optimal detection↔track assignment
   ↓
Matched:   Kalman filter UPDATES the track with the real detection
Unmatched detections: → new track CREATED
Unmatched tracks:     → marked missed; Kalman coasts on prediction
   ↓
Tracks missed too many frames in a row → track TERMINATED
   ↓
Output: stable object_id per surviving/updated track this frame
```

### What I should know
- [ ] I can explain why detection alone cannot produce identity over time.
- [ ] I can explain the Kalman filter's predict→correct cycle in plain language.
- [ ] I can explain why the Hungarian algorithm is used instead of greedy matching.
- [ ] I can explain ByteTrack's core innovation over SORT.
- [ ] I can distinguish MOTA from IDF1 and say which is more sensitive to identity consistency.
- [ ] I can define ID switch, occlusion, and track fragmentation distinctly.

### Questions to test myself
1. Why can't you just match "closest box" greedily instead of using the Hungarian algorithm?
2. What specific problem does ByteTrack solve that plain SORT does not?
3. If MOTA is high but IDF1 is low, what does that suggest is going wrong?
4. Why does TRACE prefer ByteTrack/BoT-SORT over DeepSORT as a default?

### Practical exercise
- Given a 3×3 cost matrix of IoU values between 3 predicted tracks and 3 new detections, solve the optimal assignment by hand (or trace through the Hungarian algorithm's logic) and compare it to the greedy "pick best match per row" result.

---

## 4. Trajectory & Motion Analysis

### Centroids and position `[IMPLEMENTED]`

- A box is reduced to a single representative point — usually the **centroid** `((x_min+x_max)/2, (y_min+y_max)/2)`, sometimes the bottom-center point (better approximates "where the object touches the ground," useful for geometry/speed later).
- **How TRACE uses it:** every trajectory is a time-ordered list of centroids per `object_id`, stored as `track_points`.

### Displacement, velocity, acceleration `[IMPLEMENTED — pixel-space only]`

- **Displacement** between two points in time: `Δposition = position(t2) - position(t1)`.
- **Velocity** (pixels/sec, or real-world units after geometry correction): `displacement / Δt`.
- **Acceleration**: rate of change of velocity — useful for detecting `SUDDEN_STOP` (large negative acceleration) as an event.
- Real-world unit correction (homography) is `[PLANNED]` — Phase 5/6. Everything computed in Phase 4 stays in raw pixels/second, deliberately, per this phase's scope.

### Direction `[IMPLEMENTED]`

- Computed from the displacement vector's angle, usually bucketed into compass-style categories (N, NE, E...) or kept as a raw angle for finer analytics.
- **How TRACE uses it (for now):** raw `atan2(dy, dx)` radians, not yet bucketed into compass categories — bucketing is straightforward to add later against real use cases (e.g. `LINE_CROSSED` direction) once Section 7 needs it; adding it now would be speculative.

### Stationary state and movement state `[IMPLEMENTED — simple per-step threshold, no duration smoothing yet]`

- An object is "stationary" if its velocity stays below a small noise-tolerant threshold for some duration — this threshold must account for natural detection/tracking jitter, or every parked object will falsely flicker between "moving" and "stationary."
- **How TRACE uses it (for now):** a single configurable speed threshold (px/s) applied per step, no sustained-duration/hysteresis logic yet — that's Section 7's `LOITERING`/`STOPPED` territory (deciding whether a brief tracking loss resets a duration timer, etc.), not this module's job. The threshold has no single correct default — it depends on frame rate and camera distance/resolution, since a few pixels of normal jitter maps to very different px/s depending on fps.

### Dwell time `[IMPLEMENTED — bookkeeping only; real zone-membership detection is still [PLANNED]]`

- Total time an object's track has spent inside a defined zone (or simply "present in frame," depending on the metric).
- Computed as `exit_timestamp - entry_timestamp` per zone-visit, summed if the object enters/exits multiple times.
- **Where:** `src/trajectories/dwell.py` — `ZoneVisit` (dataclass: `object_id`, `zone_id`, `entry_timestamp`, `exit_timestamp`, `.duration` property) and `DwellTracker` (`update(object_id, zone_id, is_inside: bool, timestamp) -> ZoneVisit | None`, returning the completed visit exactly when a call transitions inside→outside; `.visits(object_id, zone_id)`; `.total_dwell_time(object_id, zone_id, include_open=True, current_timestamp=None)`).
- **Deliberately decoupled from *how* zone membership is determined.** Real point-in-polygon zone detection (Section 7's `ZONE_ENTERED`/`ZONE_EXITED`) is still `[PLANNED]` — that geometric check was scoped for a "Phase 5: line crossing and zone detection" that hasn't been implemented yet (its requirements were never fully specified). Rather than block dwell-time bookkeeping on that, `DwellTracker` takes a plain `is_inside` boolean per call — whatever eventually computes real zone membership just needs to call `update()` with that boolean; this module doesn't change. Tested with a hand-authored `is_inside` sequence (`tests/test_dwell.py`), not real geometry.

### The math, at implementation level `[IMPLEMENTED — matches the code exactly]`

```text
Given track points: (x0,t0), (x1,t1), ..., (xn,tn)

velocity_i = (position_i - position_{i-1}) / (t_i - t_{i-1})
speed_i    = magnitude(velocity_i)
direction_i = atan2(dy, dx)   # angle of the displacement vector
acceleration_i = (velocity_i - velocity_{i-1}) / (t_i - t_{i-1})
```

**Why per-step, not "start to end":** using only the first and last point hides direction changes, stops, and speed variation — real events (SUDDEN_STOP, LOITERING) only show up when computed on consecutive points, not the whole track's endpoints.

### Connecting to TRACE

- Every trajectory calculation feeds the **Event Engine** (Section 7): stationary-too-long → `LOITERING`; large deceleration → `SUDDEN_STOP`; zone dwell time crossing a threshold → an alertable condition.
- Trajectory points, once stored, also power the dashboard's path-overlay visualization and the agent's `get_object_stats()` tool.

### Where this is implemented `[IMPLEMENTED]`

- `src/trajectories/trajectory.py` — `centroid(bbox)` and `magnitude(vector)` helpers; `MotionStep` (dataclass: `object_id`, `frame_id`, `timestamp`, `position`, `displacement`, `velocity`, `speed`, `direction`, `acceleration`, `is_stationary`); `Trajectory` (per-object point history + per-step motion, `update(position, timestamp, frame_id) -> MotionStep | None`); `TrajectoryManager` (per-`object_id` `Trajectory` registry fed directly by `Tracker` output, `update(tracks: list[Track]) -> list[MotionStep]`, `get_path(object_id) -> list[Tuple[float, float]]`).
- `MotionStep.acceleration` is `None` until a second velocity sample exists (needs 3 positions) — matches the guide's own formula, which needs `velocity_{i-1}` to exist.
- `TrajectoryManager.update()` returns a step only for tracks that already had at least one prior point — an object's very first-ever appearance produces no `MotionStep` (nothing to diff against yet), consistent with "per-step, not start/end" above.
- `scripts/trajectory_video.py` — CLI wiring `FrameSource` → `YoloDetector` → `ByteTracker` → `TrajectoryManager` → drawn path (polyline over `get_path()`) + box (red when stationary, green when moving) + `id=<n> <class> <speed>px/s <state>` label, to `--output` and/or `--display`; takes `--stationary-threshold`.
- `tests/test_trajectory.py` — 6 tests: first-point-produces-no-step, constant velocity (consistent speed/direction, ~zero acceleration), a stop (large deceleration then reads stationary), a direction change (angle actually shifts), jitter around a stationary point (reads stationary despite nonzero per-step speed), and `TrajectoryManager` routing tracks to per-object trajectories via centroid.

### What I should know
- [ ] I can compute velocity and direction from two consecutive track points.
- [ ] I can explain why a stationary-detection threshold needs tolerance for jitter.
- [ ] I can explain why dwell time is computed per zone-visit, not just "time since first seen."

### Questions to test myself
1. Why is per-step velocity more useful for event detection than a single start-to-end average?
2. What could cause a truly stationary object to appear to "jitter" in velocity, and how do you compensate?
3. How would you detect a U-turn from a sequence of direction values?

### Practical exercise
- Given track points `(100,200)@t=0.0s`, `(115,205)@t=0.5s`, `(130,210)@t=1.0s`, compute velocity and direction between each consecutive pair.

---

## 5. Camera Geometry

### Image coordinates vs world coordinates

- **Image coordinates**: pixel positions in the 2D frame — what the detector/tracker actually outputs.
- **World coordinates**: real-world positions (meters) in the physical scene the camera observes.
- These are related by the camera's **projection**, and that projection is generally *not* linear across the whole image — a car near the camera moves many pixels for a small real distance; the same car far away moves few pixels for the same real distance.

### Perspective, distortion

- **Perspective**: farther objects appear smaller and closer together; parallel real-world lines can appear to converge in the image (vanishing points). This is why "pixels per second" is not a real speed without correction.
- **Lens distortion** (radial/tangential): straight real-world lines can appear curved near image edges, especially with wide-angle lenses; corrected via distortion coefficients from calibration.

### Intrinsic vs extrinsic parameters

- **Intrinsic parameters**: properties of the camera/lens itself — focal length, optical center, distortion coefficients. Independent of where the camera is placed.
- **Extrinsic parameters**: the camera's position and orientation (rotation + translation) relative to the world. Changes if you move or re-aim the camera.
- Full 3D calibration (checkerboard-based, OpenCV `calibrateCamera`) recovers both — but is often more than TRACE needs for a fixed, roughly-planar-ground scene.

### Homography and perspective transformation `[IMPLEMENTED]`

- A **homography** is a 2D-to-2D projective transformation that maps points on a flat plane in the image (e.g., a road surface) to real-world coordinates on that same plane, given a handful of known correspondence points (e.g., 4 points whose real-world distances are known/measured).
- This is the **practical, lightweight calibration TRACE relies on** by default: mark 4+ reference points in the camera view whose real-world layout is known (e.g., measured lane markings), compute a homography, and use it to convert any pixel position on that ground plane to an approximate real-world position — without needing full intrinsic/extrinsic camera calibration.
- **Key limitation:** homography is only valid for points on the calibrated *plane* (typically the ground). It does not correctly map a point at head-height (a person's centroid) to ground-plane real-world coordinates without an added approximation (e.g., using the bottom-center of the box instead of the centroid, since it's closer to where the object contacts the ground).

### Where this is implemented `[IMPLEMENTED]`

- `src/geometry/homography.py` — `ground_contact_point(bbox)` (bottom-center, `((x_min+x_max)/2, y_max)`, deliberately not the centroid — the docstring cites this exact section as the reason); `GroundPlaneHomography` (`__init__(pixel_points, world_points)`, wraps `cv2.findHomography` + `cv2.perspectiveTransform`, `.pixel_to_world(pixel_point) -> (x, y)`, `.from_correspondences(...)`, `.from_config(path)`); `load_camera_homography(camera_id, configs_dir="configs/cameras")`.
- Correspondences are stored per camera as JSON under `configs/cameras/<camera_id>.json` (`{"camera_id": ..., "correspondences": [{"pixel": [x, y], "world": [X, Y]}, ...]}`) — plain JSON, no new dependency, matching this repo's existing config conventions. `configs/cameras/demo.json` ships as a worked, clearly-labeled **illustrative example only** (a uniform 20px = 1m plane, chosen so the mapping is easy to hand-verify) — not a real calibration; using it for an actual camera would be meaningless.
- **Real, tested tolerance**: on the demo config's synthetic 20px = 1m plane, `pixel_to_world()` recovers both the calibration points themselves and held-out points within `1e-6` absolute error (`tests/test_homography.py`) — but that number reflects `cv2.findHomography`'s numerical precision on a clean, noise-free synthetic correspondence set, not real-world calibration accuracy. A real camera's actual error is dominated by how precisely the reference points were measured (Section 6's error table), which this test cannot speak to.
- `GroundPlaneHomography` requires at least 4 correspondences and raises `ValueError` on too few or mismatched pixel/world point counts — enforced, not just documented.
- **Line-crossing and zone (point-in-polygon) detection also live in `src/geometry/`** (`line_crossing.py`, `zone.py`) as siblings of this homography code, and are configured in the same per-camera JSON. They're the geometric primitives Section 7's `LINE_CROSSED`/`ZONE_ENTERED`/`ZONE_EXITED` rows describe — see Section 7 for the full writeup (this section stays focused on homography/calibration itself).

### Why pixel movement ≠ real-world movement

```text
Near the camera:  small real distance → LARGE pixel displacement
Far from camera:  same real distance  → SMALL pixel displacement
```

Any speed/distance calculation done directly in pixels will be systematically wrong and *inconsistent* across the frame unless corrected via homography (or full calibration). This directly motivates Section 6.

### What I should know
- [ ] I can explain the difference between intrinsic and extrinsic camera parameters.
- [ ] I can explain what a homography does and what plane assumption it relies on.
- [ ] I can explain why the same real-world distance produces different pixel distances depending on position in the frame.
- [ ] I can explain why TRACE prefers homography-based ground-plane calibration over full 3D calibration for most cameras.

### Questions to test myself
1. Why can't you just multiply pixel distance by a single fixed "meters per pixel" constant across the whole frame?
2. What real-world information do you need to compute a homography for a road scene?
3. Why is using the bottom-center of a box, not its centroid, more appropriate for ground-plane homography mapping?

---

## 6. Speed Estimation

### Why speed cannot simply be calculated from pixel displacement

As established in Section 5, pixel displacement is a *distorted, position-dependent* proxy for real-world displacement. Naively computing `speed = pixels_moved / seconds` produces numbers with no consistent real-world meaning and — if reported as km/h without qualification — is **misleading**, not just imprecise.

### The correct(ed) approach TRACE uses `[IMPLEMENTED]`

```text
1. Pixel position (bottom-center of box) at t1 and t2
2. Apply homography → estimated ground-plane real-world position at t1, t2
3. real_distance = euclidean distance between the two world-plane points
4. elapsed_time  = t2 - t1   (from frame timestamps, not assumed constant FPS)
5. estimated_speed = real_distance / elapsed_time
```

### Where this is implemented `[IMPLEMENTED]`

- `src/geometry/speed.py` — `EstimatedSpeedSample` (dataclass: `object_id`, `frame_id`, `timestamp`, `world_position`, `estimated_speed`) and `SpeedEstimator` (`__init__(homography: GroundPlaneHomography)`, `update(tracks: list[Track]) -> list[EstimatedSpeedSample]`), implementing the 5-step algorithm above exactly.
- Lives in `src/geometry/`, not `src/trajectories/` — a deliberate call, not a default: it's meaningless without a homography, whereas `trajectories/` (Phase 4) is deliberately pixel-space-only. Keeping it in `geometry/` also keeps this section and Section 5 co-located in one module, since neither means anything without the other.
- `elapsed_time` comes from `Track.timestamp` (real per-frame timestamps from Phase 1's `FrameSource`, not `1/FPS`) — `tests/test_speed_estimator.py::test_uses_real_elapsed_time_not_assumed_fps` checks this directly: identical pixel displacement over 2x the elapsed time yields exactly half the `estimated_speed`.
- **The "estimated_speed" naming convention below is enforced, not just documented convention**: `test_estimated_speed_field_name_is_the_documented_convention` asserts the dataclass field is literally named `estimated_speed` and that no field is named bare `speed`.
- **Real, tested tolerance**: on the same synthetic 20px = 1m plane as Section 5, a known 1 m/s ground-truth motion is recovered as `estimated_speed` within `rel=1e-3` (`tests/test_speed_estimator.py`). Same caveat as Section 5 — this validates the arithmetic pipeline on clean synthetic input, not real-world accuracy, which is governed by the error sources below.

### Time / FPS considerations

- `elapsed_time` should come from actual frame timestamps, not `1/nominal_fps`, because dropped/skipped frames (Section 8) make nominal FPS an unreliable clock under real-world load.

### Error sources — documented, not hidden

| Source | Effect |
|---|---|
| Homography calibration error (imprecise reference points) | Systematic bias in all speed estimates from that camera |
| Detection/tracking jitter (box wobble frame to frame) | Random noise, worse at low frame rates |
| Non-planar ground (slopes, stairs) | Homography assumption violated locally |
| Using centroid instead of ground-contact point | Height-dependent bias (taller objects distort more) |
| Frame drops under load | Incorrect elapsed_time if not measured directly |
| Low FPS relative to object speed | Fewer samples → coarser, noisier speed estimate |

### True measured speed vs estimated speed — TRACE's explicit distinction

TRACE's outputs and documentation always label this value **"estimated speed"**, never "measured speed" or "actual speed," and every dashboard/API/agent surface that reports it must carry that qualifier. This is a deliberate, documented engineering and communication choice, not an oversight — overclaiming accuracy here is the kind of mistake that undermines trust in the whole system.

### What I should know
- [ ] I can explain, precisely, why raw pixel-based speed is wrong.
- [ ] I can list at least 3 independent error sources in TRACE's speed pipeline.
- [ ] I can explain why TRACE always labels this "estimated," never "measured."

### Questions to test myself
1. If a camera's homography reference points are measured slightly wrong, what kind of error results — random or systematic?
2. Why does elapsed_time need to come from real frame timestamps rather than `1/FPS`?
3. How would you validate an `OVERSPEED` alert before trusting/publishing it?

---

## 7. Event Engine

### Raw tracking data vs semantic events

- Raw tracking data: `object_id=31, bbox=(...), timestamp=..., frame=...` — true, but meaningless to a business user.
- A semantic event: `ZONE_ENTERED, object_id=31, zone="restricted_area", timestamp=...` — a fact someone can act on.
- **The event engine's entire job** is this translation, and it must be **deterministic and rule-based** — no LLM involved — so its output is auditable and reproducible (per the spec's Engineering Rule #4: the LLM reasons over structured data, it does not produce it).

### Event types — meaning, inputs, logic, edge cases `[IMPLEMENTED — all nine event types; database sink is still [PLANNED], Phase 8]`

| Event | Meaning | Required input | Core logic | Key edge case |
|---|---|---|---|---|
| `LINE_CROSSED` | Object crossed a configured virtual line | consecutive centroid pair, line geometry | check if the segment between two consecutive points intersects the line, determine side-before/side-after for direction | fast objects can "teleport" past a thin line between frames — must check segment intersection, not just point-in-front/behind. **As predicted, confirmed by test** (`tests/test_events_line_crossed.py`, and Section 5's own `test_fast_moving_point_pair_caught_by_segment_intersection_not_naive_proximity`). |
| `ZONE_ENTERED` / `ZONE_EXITED` | Object crossed a polygon boundary | centroid, zone polygon | point-in-polygon test, compare current vs previous frame's containment | object flickering at a zone edge can fire enter/exit repeatedly — needs debounce/hysteresis. **As predicted, confirmed by test** (`tests/test_events_zone.py::test_flicker_at_zone_boundary_produces_no_spurious_events_through_the_engine`, run through the full `EventEngine`, not just the raw zone geometry). |
| `OVERSPEED` | Smoothed estimated_speed exceeds a configured limit | estimated_speed (Section 6), configured limit | moving-average smoothing over the last `window` samples, then threshold compare, fires once per over-limit period | noisy single-frame speed spikes must be smoothed before comparing, or false alerts spike. **As predicted, confirmed by test** — but real footage testing (below) shows even smoothing doesn't fully save a poorly-calibrated camera: OVERSPEED fired twice on a subject who never actually moved fast, purely from the *demo* (illustrative, not real) homography combined with ordinary bbox jitter. |
| `STOPPED` | Object stationary beyond a threshold duration | velocity history | velocity below noise threshold ( `MotionStep.is_stationary`, Section 4) sustained over N real seconds, one continuous streak, resets on any single moving step | must distinguish "genuinely stopped" from tracker jitter (Section 4). **As predicted, confirmed by test**, including a literal jitter sequence (`tests/test_events_stopped.py::test_jittery_but_effectively_stationary_object_still_fires_stopped`) reusing Section 4's own jitter-tolerance test data. |
| `SUDDEN_STOP` | Rapid deceleration | velocity/acceleration history (`MotionStep.acceleration`, Section 4) | fires when acceleration magnitude exceeds a threshold **and** speed actually dropped (distinguishes a stop from "large acceleration while speeding up") | must use real elapsed time, not frame count — inherited for free from `MotionStep`. **Real testing revealed something the original edge case didn't anticipate**: see "What real testing found" below — the default threshold is far too sensitive to ordinary pixel-space bbox jitter on real footage. |
| `LOITERING` | Cumulative dwell time in a zone exceeds a threshold | dwell time (`DwellTracker`, Section 4/6), zone containment (`ZoneDetector.is_inside()`, Section 5) | fires once, ever, per (object, zone) when cumulative dwell first crosses the threshold — never resets, since dwell time is defined cumulatively (Section 4) | requires deciding whether brief tracking loss resets the timer or not. **Answered by construction, not left open**: `LoiteringRule` is fed `ZoneDetector`'s already-*debounced* containment, not raw per-frame containment, so a tracking loss briefer than the zone's own debounce window never reaches `DwellTracker` as an exit at all. |
| `OBJECT_APPEARED` | A new track was created | track lifecycle state | fires once, the first time this `EventEngine` instance ever sees a given `object_id` | distinguishing a genuinely new object from a re-identification after occlusion. **Deferred to Phase 3's own finding, not re-solved here**: ByteTrack keeps the same `object_id` through a brief occlusion (within its `track_buffer`), so no duplicate fires there; a longer occlusion gets ByteTrack's own fresh `object_id` on reappearance, which correctly reads as new to this rule too. |
| `OBJECT_DISAPPEARED` | A track was terminated | track lifecycle state | fires once an `object_id` has been absent from `Tracker.update()`'s output for `missing_timeout_seconds` of real elapsed time | premature termination on brief occlusion produces false disappear/reappear pairs. **As predicted, confirmed by test** (`tests/test_events_lifecycle.py::test_disappeared_does_not_fire_for_a_brief_absence_under_timeout`) — but this only holds if `missing_timeout_seconds` is set comfortably longer than ByteTrack's own `track_buffer` converted to seconds; misconfigured, it would fire *before* ByteTrack even gives up on the track. |

### What real testing found that the table above didn't originally predict

Running the full pipeline (`scripts/event_video.py`) against a real ~16s/244-frame webcam clip (`data/sample.mp4`, same clip used in Phases 2–4 testing) with default thresholds: **36 `SUDDEN_STOP` events fired** from a subject who spends nearly the entire clip essentially sitting still — roughly one `SUDDEN_STOP` every 6–7 frames. The original edge case only anticipated "must use real elapsed time, not frame count"; it didn't anticipate that **ordinary pixel-space bounding-box jitter alone produces acceleration magnitudes in the thousands of px/s²** at typical webcam resolution/frame rate, which blows straight through a `min_deceleration_magnitude` default of 500.0 — a value that looked reasonable against Phase 4's clean synthetic test data (where a real, deliberate stop produces acceleration around 5000 px/s², and non-stops produce exactly 0) but was never validated against noisy real detection output. `OVERSPEED` fired twice in the same run for the same underlying reason, compounded by `configs/cameras/demo.json` being an illustrative, not real, calibration. `STOPPED` (5 fires) and `OBJECT_APPEARED` (1 fire, correctly just once) matched expectations. This is a real, measured tuning problem, not a logic bug — `SuddenStopRule`'s threshold needs to be set from real per-camera acceleration-noise measurements (analogous to Section 4's own `DEFAULT_STATIONARY_SPEED_THRESHOLD` caveat), or the rule needs its own smoothing/duration-based confirmation the way `StoppedRule` already has. Neither fix is implemented yet — flagged here rather than silently tuned away, per the instruction to report what real testing actually showed.

### Where this is implemented `[IMPLEMENTED]`

- `src/events/event.py` — `Event` (dataclass: `event_type`, `object_id`, `class_name`, `timestamp`, `camera_id`, `confidence`, `metadata`), `.to_dict()` serializes `class_name` under the schema's `"class"` key. **Deliberately not the ISO8601 timestamp string shown below** — see "Structured output schema" for why.
- `src/events/line_crossed.py`, `zone_entered.py`, `zone_exited.py` — pure `build_event(track, <crossing/transition>, camera_id) -> Event` functions; the detection/debounce logic itself already lived in `geometry.line_crossing`/`geometry.zone` (Section 5), so these modules are only the translation to the Event schema.
- `src/events/overspeed.py` — `OverspeedRule` (moving-average smoothing, fires once per over-limit period).
- `src/events/stopped.py` — `StoppedRule` (streak-duration confirmation).
- `src/events/sudden_stop.py` — `SuddenStopRule` (acceleration-magnitude + speed-decrease confirmation).
- `src/events/loitering.py` — `LoiteringRule` (cumulative dwell, fires once ever per object/zone).
- `src/events/object_appeared.py` — `ObjectAppearedRule` (fires once per `object_id`, ever).
- `src/events/object_disappeared.py` — `ObjectDisappearedRule` (absence-duration confirmation, once per frame with the full track list).
- `src/events/engine.py` — `EventEngine`, the orchestrator: wires `TrajectoryManager` (Section 4), `SpeedEstimator` (Section 6), `LineCrossingDetector`/`ZoneDetector` (Section 5), and `DwellTracker` (Section 4) internally, and runs every rule above against their combined per-frame output. `update(tracks: list[Track], timestamp: float) -> list[Event]`.
- **`update()` takes `timestamp` as its own argument, separately from `tracks`** — the one place this phase's interface deviates from the "just pass tracks" pattern every earlier per-frame component uses (`Tracker`, `TrajectoryManager`, `SpeedEstimator`). This is necessary, not incidental: `OBJECT_DISAPPEARED` must keep advancing its missing-time bookkeeping on frames where zero objects are tracked, and there is no way to recover "what time is it now" from an empty `tracks` list.
- **Pure/deterministic, enforced by what's imported, not just by convention**: no module under `src/events/` imports anything LLM-related, an API client, or any other nondeterministic dependency — every `Event` is produced by fixed arithmetic/threshold rules over `Track`/`MotionStep`/`EstimatedSpeedSample`/`LineCrossing`/`ZoneTransition` output.
- `scripts/event_video.py` — the full end-to-end CLI: `FrameSource` → `YoloDetector` → `ByteTracker` → `EventEngine`, printing each `Event` as it's produced. No database wiring (Phase 8).
- Tests: `tests/test_events_line_crossed.py`, `test_events_zone.py`, `test_events_overspeed.py`, `test_events_stopped.py`, `test_events_sudden_stop.py`, `test_events_loitering.py`, `test_events_lifecycle.py` (one file per event type or closely related pair, matching the module layout), plus `tests/test_event_engine.py` for engine-level integration (including one real-fixture-video smoke test, structure-only assertions, same pattern as every earlier phase).

### Structured output schema

```json
{
  "event_type": "ZONE_ENTERED",
  "object_id": 31,
  "class": "person",
  "timestamp": "2026-08-31T10:42:13Z",
  "camera_id": "gate_2",
  "zone": "restricted_area",
  "confidence": 0.93,
  "metadata": { "...event-specific fields..." }
}
```

Every event type shares the common envelope (`event_type`, `object_id`, `class`, `timestamp`, `camera_id`) and adds event-specific fields inside `metadata` (e.g., `speed`/`limit` for `OVERSPEED`, `dwell_seconds` for `LOITERING`).

**Two deliberate deviations from this illustration, in the actual implementation:**
- `Event.confidence` is part of the common envelope (a real dataclass field), not folded into `metadata` — matching how it's drawn top-level above, and how it's genuinely common to every event type.
- `Event.timestamp` is a `float` (seconds), never the ISO8601 string shown above. That string implicitly assumes a real calendar time; file-based sources don't have one (Phase 1: file timestamps are video-relative, not wall-clock), so forcing ISO8601 here would silently misrepresent video-relative time as if it were a real timestamp. Convert at the point you actually know the anchor — e.g. when writing to a database in Phase 8 — not inside the event engine itself. `zone`/`line` identifiers likewise live inside `metadata` (`{"zone_id": ...}`), not as a top-level field, per the prose envelope definition rather than this one illustrative example.

### Where it's implemented `[PLANNED — database sink only; the rule/schema layer above is [IMPLEMENTED]]`

Writing `Event` records to a database (`src/database/`, Section 9) is Phase 8, not this phase. `scripts/event_video.py` currently prints events; nothing persists them yet.

### What I should know
- [ ] I can explain why the event engine must be deterministic, not LLM-based.
- [ ] I can explain the debounce/hysteresis problem at zone boundaries.
- [ ] I can explain why `LINE_CROSSED` needs segment-intersection logic, not just point comparison.
- [ ] I can describe the shared event schema and why a common envelope matters.
- [ ] I can explain why `EventEngine.update()` needs an explicit `timestamp` argument when every earlier per-frame component only needs a tracks/detections list.
- [ ] I can explain why `SUDDEN_STOP`'s default threshold turned out to be wrong against real footage, and what class of fix that implies (per-camera tuning from measured noise, or added smoothing).

### Questions to test myself
1. Why would checking "is the point past the line this frame" (instead of segment intersection) miss fast-moving objects?
2. What causes an object to flicker `ZONE_ENTERED`/`ZONE_EXITED` repeatedly, and how do you prevent it?
3. Why keep event-specific fields inside a `metadata` object rather than flattening everything into top-level columns?
4. Why does `LOITERING` fire only once, ever, per object/zone pair, rather than every frame the dwell time stays over threshold?
5. Why did a threshold that looked reasonable against Phase 4's clean synthetic test data (`min_deceleration_magnitude=500.0`) turn out to be far too sensitive against real footage — what's different about the two?

---

## 8. Video Processing

### Where this is implemented `[IMPLEMENTED]`

- `src/detection/frame_source.py` — `Frame` (dataclass: `image`, `frame_id`, `timestamp`, `source_id`) and `FrameSource` (`__init__(source: str | int, source_id: str | None = None, frame_skip: int = 1)`, `.read() -> Frame | None`, `.release()`, context-manager support).
- `scripts/preview_frames.py` — CLI: `python scripts/preview_frames.py <path-or-camera-index> [--num-frames N] [--frame-skip N] [--source-id ID]`, prints `frame_id` + `timestamp` for the first N frames.
- `tests/test_frame_source.py` + `tests/conftest.py` — unit tests against a synthetic sample video generated on first run at `tests/fixtures/sample_video.mp4`.
- Lives in `src/detection/` rather than a new `src/video/` module, matching this guide's own Section 0 data-flow description ("a frame arrives from a video file or camera — `src/detection` input layer").
- `source: str | int` is what unifies file and camera input — `cv2.VideoCapture` itself accepts either, so `FrameSource` just passes it through and exposes `.is_live` (`isinstance(source, int)`) for callers that need to know which clock a `Frame.timestamp` came from.
- Frame skipping: `frame_skip=N` reads (and discards) `N-1` frames before returning the Nth; `frame_id` always reflects the true position in the source (including skipped frames), not a count of frames returned.
- Timestamps: file sources use `cv2.CAP_PROP_POS_MSEC` (video-relative seconds, monotonically increasing from 0 at the start of the file); camera sources use `time.time()` (wall-clock). `FrameSource.is_live` tells you which one a given `Frame.timestamp` is.
- BGR→RGB conversion happens once, inside `FrameSource.read()`, via `cv2.cvtColor(..., cv2.COLOR_BGR2RGB)` — every `Frame.image` downstream is already RGB; nothing else in the pipeline should call `cvtColor` for this purpose.

### OpenCV VideoCapture and the frame loop

- `cv2.VideoCapture` abstracts both video files and camera devices/streams behind one read interface — this is what lets TRACE support "file or live camera" via the same pipeline code (Section 0 design decision).
- Basic loop: read frame → process → (optionally) display/store → repeat until the source ends or is stopped.

### Frame skipping and batch inference

- **Frame skipping**: process every Nth frame instead of every frame, trading temporal resolution for throughput when the pipeline can't keep up with the video's native FPS.
- **Batch inference**: running the detector on multiple frames at once on GPU can improve throughput but adds latency (must wait to fill a batch) — a genuine trade-off for a system whose name promises "real-time."

### Buffering, real-time processing, latency vs throughput

- **Throughput**: how many frames processed per second, averaged.
- **Latency**: how long a single frame takes from capture to result — critical for alerts ("`OVERSPEED` fired 4 seconds after it happened" may be too slow for some use cases).
- A buffered pipeline can have high throughput but poor per-event latency if frames queue up under load.

### Processing FPS vs video FPS vs end-to-end latency — the distinction that matters

| Metric | What it measures |
|---|---|
| Video FPS | The rate frames were recorded/encoded at (a property of the source) |
| Processing FPS | How fast TRACE's pipeline can consume and fully process frames on the current hardware |
| End-to-end latency | Wall-clock time from a real-world event happening to TRACE producing/storing the corresponding event record |

If processing FPS < video FPS on a live feed, TRACE must either drop frames (frame skipping) or fall permanently behind — this is a real, must-be-measured constraint (Section 14/16), not an implementation detail to gloss over.

### What I should know
- [ ] I can explain why VideoCapture unifies file and camera input.
- [ ] I can explain the throughput vs latency trade-off with a concrete TRACE example.
- [ ] I can explain what happens when processing FPS falls behind video FPS on a live feed.

### Questions to test myself
1. Why might frame skipping be an acceptable trade-off for analytics but a bad one for `OVERSPEED` alerting?
2. What's the practical difference between "TRACE processes 30 FPS" and "TRACE has 200ms latency"?
3. On a live camera feed running slower than its native FPS, what are TRACE's options and what does each cost?

---

## 9. Data & Database

### Why TRACE needs a database

Live pipeline state (in-memory tracks) disappears the moment the process stops. Investigation, analytics, and the agent all need to query **history** — "what happened last Tuesday at 2pm" is impossible without persistence. A relational database also enforces structure and relationships (an event *belongs to* an object *belongs to* a camera), which raw log files don't give you for free.

### Relational concepts used

- **Tables** — structured collections of rows with a fixed schema.
- **Primary keys** — unique identifier per row (e.g., `event.id`).
- **Foreign keys** — link rows across tables (e.g., `event.object_id → objects.id`), enforcing that events always reference a real tracked object.
- **Indexes** — speed up lookups/filters on specific columns (e.g., indexing `events.timestamp` and `events.camera_id` since almost every analytics/agent query filters by time range and camera).
- **Timestamps** — every table that represents something that happened needs one, stored consistently (UTC) to avoid timezone bugs across cameras/deployments. **Implemented deviation, documented, not an oversight**: per-frame timestamps (`track_points.timestamp`, `events.timestamp`, `objects.first_seen`/`last_seen`) are stored as `Float` seconds, matching the convention used everywhere in this codebase since Phase 1 — not a UTC `DateTime`. File-based sources are video-relative (Phase 1), not wall-clock; a `DateTime` column would silently misrepresent that. `videos.started_at` is the one genuine `DateTime` — it records when the file was registered for processing, a real wall-clock moment, not a per-frame value.

### Why PostgreSQL

Mature, free, strong support for relational integrity, indexing, and time-range queries — a solid default for a system whose core value is structured, queryable history. (Not chosen for anything exotic like PostGIS/geo features at this stage, though zone polygons could eventually benefit from them — flagged as `[OPTIONAL]` future work.)

### The TRACE schema `[IMPLEMENTED]`

| Table | Purpose |
|---|---|
| `cameras` | One row per camera/source: name, location, calibration/homography reference |
| `videos` | One row per ingested video file (for offline/file-based runs) |
| `objects` | One row per tracked object's lifetime (a track, from creation to termination), with class |
| `tracks` / `track_points` | Time-series of positions per object — the raw trajectory data |
| `zones` | Configured polygons per camera |
| `lines` | Configured virtual lines per camera |
| `events` | Structured event records (Section 7's schema), foreign-keyed to `objects` and `cameras`, optionally `zones`/`lines` |

### Why each table exists (relationship view)

```text
cameras 1──* videos
cameras 1──* zones
cameras 1──* lines
cameras 1──* objects        (an object is tracked on one camera's feed)
objects 1──* track_points   (an object's trajectory over time)
objects 1──* events         (every semantic event references the object it happened to)
zones   1──* events         (zone-related events reference which zone)
lines   1──* events         (line-crossing events reference which line)
```

This structure is exactly what lets an event be traced back to "reconstruct an object's history" (spec requirement) — from an `events` row you can join to `objects` and `track_points` to get the full trajectory around that moment, and to `videos`/`cameras` to locate the actual footage (Section 8's investigation feature).

### Where this is implemented `[IMPLEMENTED]`

- `src/database/models.py` — SQLAlchemy 2.0 declarative models for exactly the seven tables above: `Camera`, `Video`, `Zone`, `Line`, `TrackedObject` (Python class name for the `objects` table — `object` collides with a Python builtin), `TrackPoint`, `Event`. Foreign keys match the relationship diagram above exactly, enforced by Postgres itself (verified by test, not just declared — `tests/test_database_schema.py` inserts a duplicate `(camera_id, object_id)` pair and confirms Postgres raises `IntegrityError`, same for duplicate `camera_id`).
- `Event.event_metadata` is the Python attribute name for the actual DB column `metadata` (`Base.metadata` is a reserved SQLAlchemy name on every model, so the column needed an explicit name override) — the JSON contents match Section 7's `Event.metadata` exactly, just accessed under a different attribute name in Python.
- `src/database/db.py` — `get_engine(database_url=None)` (defaults to `DEFAULT_DATABASE_URL`, the docker-compose `db` service as reachable from the host), `create_all(engine)` (schema setup for dev/tests — explicitly *not* a migration tool; a real migration tool like Alembic would be the next step for evolving an already-deployed schema, out of scope here), `get_session_factory(engine)`.
- `src/database/repository.py` — the repository layer requested for Phase 9 reuse: `get_or_create_camera`, `create_video`, `get_or_create_zone`, `get_or_create_line`, `get_or_create_object`, `add_track_point`, `add_event`, `add_event_from_pipeline` (resolves an `events.event.Event`'s zone/line foreign keys automatically from its `metadata`), `get_events_for_object`, `get_track_points_for_object`. Pure data access — no business logic, no HTTP, matching Section 10's layering discussion.
- **Known, documented limitation**: `objects.object_id` is the Tracker's own per-camera id (Section 3), which restarts from 1 on every new `ByteTracker` instance. `(camera_id, object_id)` is a stable key only *within one continuous pipeline run* — a process restart that starts a fresh tracker and reuses `object_id=1` gets merged into the same existing row rather than starting a new one, rather than being solved with a session/run identifier this phase didn't build.
- **docker-compose.yml**: the `db` service (postgres:16) already existed from Phase 0 bootstrap; Phase 8 added a `ports: ["5433:5432"]` mapping so the host (and this repo's tests) can reach it directly, and removed the obsolete top-level `version:` key docker compose itself flagged as deprecated.
- `scripts/persist_video.py` — the full pipeline wired to write, not just print: `FrameSource` → `YoloDetector` → `ByteTracker` → `EventEngine` → `repository` calls per frame (`get_or_create_object` + `add_track_point` for every track, `add_event_from_pipeline` for every event), committing every `--commit-every` frames (default 20). Verified against real footage: 100 frames of `data/sample.mp4` persisted 100 `track_points` and 18 `events`, then read back correctly through the analytics layer (Section 11) — including `busiest_hours` correctly landing everything in the 1970-01-01 UTC hour bucket, exactly per that function's documented video-relative-timestamp caveat, not a bug.
- Tests: `tests/test_database_schema.py` (schema/constraint tests against real Postgres), `tests/test_repository.py` (insert a fake object + events, query back, confirm relationships resolve — the exact scenario requested), `tests/test_analytics.py` (see Section 11). All three use a `db_session` fixture (`tests/conftest.py`) built on SQLAlchemy 2.0's "join a session to an external transaction" pattern — every test runs inside a rolled-back transaction, so no test's data ever leaks into another's, even across `session.commit()` calls inside the code under test. Tests against the database **skip** (not fail) if `trace_test` isn't reachable, so the rest of the suite still runs without Docker up.

### What I should know
- [ ] I can explain why in-memory-only tracking state is insufficient for TRACE's goals.
- [ ] I can explain the foreign-key relationships between `events`, `objects`, and `cameras`.
- [ ] I can explain why `timestamp` columns need consistent timezone handling.
- [ ] I can explain what an index on `events.timestamp` buys you.

### Questions to test myself
1. Why does an `event` row need a foreign key to `objects` rather than just storing a raw `object_id` integer with no constraint?
2. What query would you run to reconstruct everything a specific object did during its lifetime?
3. Why might `track_points` become the largest table in the system, and what does that imply for indexing/retention?

---

## 10. Backend

### API, REST, and why TRACE has one at all

An API decouples the CV/database internals from anything that consumes them — dashboard, agent, or a future external integrator all talk to the same stable interface instead of poking the database directly. REST (resource-oriented URLs + HTTP verbs) is a simple, well-understood convention for this.

### FastAPI, Pydantic, request/response

- **FastAPI**: a Python web framework built for building APIs quickly, with automatic request/response validation and interactive docs generated from type hints.
- **Pydantic**: the data-validation library FastAPI uses under the hood — define a schema as a Python class with typed fields, and incoming/outgoing JSON is automatically validated/serialized against it. This catches malformed requests (e.g., a missing required field) before they ever reach business logic.

### Services / repository layering

A clean separation: **API layer** (routes, request/response shapes) → **service layer** (business logic: "what does creating a zone actually involve") → **database/repository layer** (raw queries/ORM calls). This is what Engineering Rule #3 ("keep CV, business logic, database, API, and agent layers modular") means concretely for the backend — a route handler should not contain raw SQL, and a database function should not know about HTTP.

**Implemented simplification, not an oversight**: TRACE's API routes call the Phase 8 repository/analytics layers *directly*, with no separate service-layer module in between. At this scope, every route's "business logic" is either a single repository call plus a not-found check (cameras, videos, zones, lines, object trajectory) or a fixed bundle of analytics queries (`GET /analytics`) — a service layer that only ever forwards one call 1:1 would be pure indirection, not a real separation of concerns. The layering principle still holds where it matters: no route handler contains raw SQL or ORM queries of its own (Section 10's actual rule) — `api/common.py`'s `get_camera_or_404` and every route call into `database.repository`/`analytics.queries` for that. Revisit if a route ever needs real multi-step business logic beyond "look up, maybe 404, delegate."

### Validation and error handling `[IMPLEMENTED]`

- Validation happens automatically at the API boundary via Pydantic schemas (reject malformed input early).
- Error handling: convert internal exceptions (not-found, invalid zone geometry, database errors) into meaningful HTTP status codes and structured error responses, not raw stack traces.
- **How TRACE does each of the three required cases**: 422 for a malformed body/query param is automatic (Pydantic + FastAPI, including a custom `field_validator` for domain rules like "a zone needs ≥3 points" or "a line's start/end must differ" — a plain `ValueError` inside a validator becomes a 422 with no extra code). 404 is raised explicitly once a repository lookup returns `None` (`api/common.py::get_camera_or_404`, and inline in `objects.py` for an unknown trajectory id) — never silently returning an empty/default value. 500 is caught by one global handler (`app.exception_handler(Exception)` in `api/app.py`) that logs the real exception server-side and always returns the same clean `{"detail": "internal server error"}` body — verified by test (`tests/test_api.py::test_unexpected_error_returns_clean_500_not_a_stack_trace`, which monkeypatches a repository function to raise and asserts the response body never contains the exception's class name or a traceback).

### The actual TRACE API `[IMPLEMENTED — all seven Section 8/9 CRUD/query endpoints; agent/alerts are [PLANNED], Phases 11–12]`

| Endpoint | Purpose | Input | Output | Route function |
|---|---|---|---|---|
| `POST /videos` | Register/ingest a video file for offline processing | `VideoCreate` (camera_id, path, started_at?) | `VideoRead` | `api/routers/videos.py::create_video` |
| `POST /cameras` | Register a camera source (live or file-backed) | `CameraCreate` (camera_id, name?, location?, calibration_reference?) | `CameraRead` | `api/routers/cameras.py::create_camera` |
| `GET /cameras/{camera_id}/events` | List events for a camera, filterable by time range/type | path `camera_id` (string), query `event_type?`/`start_time?`/`end_time?` | `list[EventRead]` | `api/routers/cameras.py::list_camera_events` |
| `GET /objects/{id}/trajectory` | Full trajectory of one tracked object | path `id` (int, internal DB PK — see note below) | `TrajectoryRead` | `api/routers/objects.py::get_object_trajectory` |
| `GET /analytics` | Aggregated stats (Section 11) | query `camera_id?`/`start_time?`/`end_time?` | `AnalyticsSummary` (bundles 7 of Section 11's 8 functions) | `api/routers/analytics.py::get_analytics` |
| `POST /zones` | Configure a polygon zone on a camera | `ZoneCreate` (camera_id, zone_id, polygon — validated ≥3 points) | `ZoneRead` | `api/routers/zones.py::create_zone` |
| `POST /lines` | Configure a virtual line on a camera | `LineCreate` (camera_id, line_id, start, end — validated start≠end) | `LineRead` | `api/routers/lines.py::create_line` |
| `POST /agent/query` | Ask the Vision Agent a natural-language question | question text, optional context | agent's grounded answer | `[PLANNED]` — Phase 11, depends on the not-yet-built Vision Agent |
| `POST /alerts` | Configure or trigger an alert rule | rule definition | alert/rule record | `[PLANNED]` — Phase 12, depends on a not-yet-built alert-rule system |

**Two deliberate path-parameter decisions, since the table above only wrote `{id}` generically:**
- `GET /cameras/{camera_id}/events` uses the camera's human-readable **string** id (`"demo"`, `"gate_2"`) — the identifier already used everywhere else in this codebase (config filenames, `EventEngine(camera_id=...)`, the event schema itself).
- `GET /objects/{id}/trajectory` uses the object's **internal integer database primary key** (`TrackedObject.id`), not the Tracker's own per-camera `object_id` (Section 3) — that id is only unique within one camera's tracker instance (Phase 8's own documented limitation), so it can't identify a REST resource unambiguously across cameras. The internal PK can.

**`POST /cameras`, `/zones`, `/lines` are idempotent by their string id**, inheriting `get_or_create_*` semantics directly from the Phase 8 repository — posting the same `camera_id`/`zone_id`/`line_id` twice returns/updates the existing row rather than erroring with a conflict. A deliberate simplification at this scope, not an oversight.

### Where this is implemented `[IMPLEMENTED]`

- `src/api/app.py` — the FastAPI app, router registration, the global 500 handler.
- `src/api/deps.py` — `get_db()`, one SQLAlchemy session per request (overridden in tests to reuse the same rolled-back-transaction session as the repository/analytics tests).
- `src/api/schemas.py` — every Pydantic request/response model, including the two custom validators described above.
- `src/api/common.py` — `get_camera_or_404`, the one small piece of shared "look up or fail" logic every camera-scoped route needs.
- `src/api/routers/` — `cameras.py`, `videos.py`, `zones.py`, `lines.py`, `objects.py`, `analytics.py`, one module per resource.
- Tests: `tests/test_api.py`, using FastAPI's `TestClient` — one success and one failure case per endpoint (15 tests total), plus the 500-handler test. **Real finding while writing these, not a framework bug**: Starlette's `TestClient` re-raises the original exception for debuggability by default (`raise_server_exceptions=True`) even when a registered exception handler already produced a real response — the 500 test needed `TestClient(app, raise_server_exceptions=False)` to actually observe the clean response instead of the raw exception. Also verified against a real running `uvicorn` server with `curl` (not just `TestClient`), including the 404 and 422 paths, since this environment's FastAPI/Starlette versions turned out newer than expected and `TestClient`-only verification felt worth double-checking.

---

## 11. Analytics

*Added in Phase 8 alongside Section 9, since implementing the schema and querying it went together in one phase. Sections 12–18, 20, and 21 (listed in the Table of Contents) are still not written — see the note below.*

### What analytics is, here

Every function in this section is a read-only SQL query against the tables Section 9 defines — never a hardcoded or estimated number, and never computed by an LLM (the same determinism requirement Section 7's event engine has: an LLM may *ask* an analytics question later via a tool call, Section 12, but it never computes the answer itself).

### The eight analytics functions `[IMPLEMENTED]`

| Function | Answers | Computed from |
|---|---|---|
| `object_count` | How many distinct objects were tracked (optionally by camera/class/time range)? | `COUNT` over `objects`, filtered on `first_seen` |
| `line_crossing_count` | How many raw line-crossing events happened? | `COUNT` of `LINE_CROSSED` events |
| `zone_violation_count` | How many times was a configured zone entered? | `COUNT` of `ZONE_ENTERED` events — see the naming caveat below |
| `average_dwell_time` | On average, how long do objects stay in a zone per visit? | Paired `ZONE_ENTERED`/`ZONE_EXITED` events per object per zone, matched in timestamp order, durations averaged |
| `traffic_volume` | How many *distinct* objects passed a line (not double-counting repeat crossings)? | `COUNT(DISTINCT object_id)` of `LINE_CROSSED` events |
| `busiest_hours` | Which hour(s) had the most events? | `Event.timestamp` bucketed by hour, counted, sorted — see the wall-clock caveat below |
| `event_frequency` | How often does each event type happen? | `COUNT` of `events`, grouped by `event_type` |
| `per_class_stats` | Per detected class, how many objects and events? | `COUNT` of `objects` and `events`, both grouped by `class_name` |

**Naming note on `zone_violation_count`**: `ZONE_ENTERED`/`ZONE_EXITED` (Section 7) don't distinguish a "restricted" zone from any other configured zone — TRACE doesn't currently model that distinction. "Violation" here is the domain framing Section 0 uses for the same underlying event (a `ZONE_ENTERED` on a security-relevant zone *reads* as a violation), not a separate event_type. If TRACE later needs to distinguish restricted from non-restricted zones, that's a `Zone` schema change (e.g. a `restricted: bool` column), not an analytics-layer one.

**`busiest_hours`'s real, tested limitation**: it treats `Event.timestamp` as Unix epoch seconds (UTC). That's exactly correct for live-camera events (Phase 1: `FrameSource` uses `time.time()` for camera sources) but **not** for file-based sources, whose timestamps are video-relative (Phase 1) — bucketing those by "hour" doesn't correspond to any real calendar hour. Confirmed empirically, not just reasoned about: persisting `data/sample.mp4` (a file source, timestamps starting near 0.0) and calling `busiest_hours` returns everything in the `1970-01-01T00:00 UTC` bucket — the Unix epoch, because a near-zero video-relative timestamp interpreted as epoch seconds *is* near the epoch. `videos.started_at` exists in the schema for exactly this kind of anchor but isn't wired into `busiest_hours` yet — `[PLANNED]`.

### Where this is implemented `[IMPLEMENTED]`

- `src/analytics/queries.py` — all eight functions above, plus a shared `_camera_pk()` helper that resolves a human-readable `camera_id` string to its internal integer primary key (or a sentinel that matches nothing, for an unknown `camera_id`, rather than raising or silently ignoring the filter).
- Every function takes a SQLAlchemy `Session` as its first argument and keyword-only filters (`camera_id`, `class_name`, `zone_id`, `line_id`, `start_time`, `end_time` where relevant) — no hidden global state, no ORM session management inside the analytics layer itself.
- `tests/test_analytics.py` — seeds a fully deterministic scenario (2 objects, 7 events, one completed 3.0s zone visit, 3 line crossings from 2 distinct objects) via the real repository layer, then asserts every one of the 8 functions against the exact expected number computed by hand from that scenario — not just "it returns something," a specific known value per function.

> **Note:** Sections 12–18, 20, and 21 (listed in the Table of Contents) have not been written yet — only Sections 0–11 exist below this point, plus Section 19 (Implementation Map), added here ahead of the sections it numerically follows so completed work has somewhere to be recorded. Fill in 12–18/20/21 as those phases are planned; renumber/reorder at that point if needed.

## 19. Implementation Map

*Updated phase-by-phase as real code lands. Only rows for phases that are actually `[IMPLEMENTED]` belong here — see each section's own `[PLANNED]`/`[IMPLEMENTED]` tags for design-only content.*

| Concept (guide section) | Status | File(s) | Key symbols |
|---|---|---|---|
| Video ingestion / frame loop, frame skipping, BGR→RGB boundary (Section 8) | `[IMPLEMENTED]` | `src/detection/frame_source.py` | `Frame` (dataclass: `image`, `frame_id`, `timestamp`, `source_id`), `FrameSource(source: str \| int, source_id: str \| None = None, frame_skip: int = 1)` with `.read() -> Frame \| None`, `.release()`, `.is_live` |
| Frame preview / sanity-check CLI (Section 8) | `[IMPLEMENTED]` | `scripts/preview_frames.py` | `main()` — prints `frame_id` + `timestamp` for the first N frames of a file or camera source |
| FrameSource test coverage (Section 8, Section 16) | `[IMPLEMENTED]` | `tests/test_frame_source.py`, `tests/conftest.py` | fixtures `sample_video_path`, `sample_video_frame_count`; synthetic video generated at `tests/fixtures/sample_video.mp4` |
| Detector interface + Detection schema (Section 2) | `[IMPLEMENTED]` | `src/detection/detector.py` | `Detection` (dataclass: `bbox` xyxy pixel coords, `class_name`, `confidence`, `frame_id`, `timestamp`), `Detector` (ABC, `detect(frame: Frame) -> list[Detection]`) |
| Concrete detector — YOLOv8n, pretrained, provisional (Section 2) | `[IMPLEMENTED — provisional, see Section 2 for the benchmarking caveat]` | `src/detection/yolo_detector.py` | `YoloDetector(Detector)` — `__init__(model_path="yolov8n.pt", confidence_threshold=0.25, class_allowlist=DEFAULT_CLASS_ALLOWLIST, device=None)`; `DEFAULT_CLASS_ALLOWLIST = ("person", "car", "motorcycle", "bus", "truck", "bicycle")` |
| Detection sanity-check CLI (Section 2, Section 8) | `[IMPLEMENTED]` | `scripts/detect_video.py` | `main()` — wires `FrameSource` → `YoloDetector` → drawn boxes, to `--output` and/or `--display` |
| Detector test coverage (Section 2, Section 16) | `[IMPLEMENTED]` | `tests/test_detector.py` | mocked-model tests (`_FakeYOLO`, monkeypatches `ultralytics.YOLO`) + one real-model integration test (`test_yolo_detector_returns_well_formed_detections_on_real_frames`) against `sample_video_path` |
| Tracker interface + Track schema (Section 3) | `[IMPLEMENTED]` | `src/tracking/tracker.py` | `Track` (dataclass: `object_id`, `class_name`, `bbox` xyxy pixel coords, `confidence`, `timestamp`, `frame_id`), `Tracker` (ABC, `update(detections: list[Detection]) -> list[Track]`) |
| Concrete tracker — ByteTrack via ultralytics' BYTETracker, provisional (Section 3) | `[IMPLEMENTED — provisional, see Section 3 for the reuse-vs-build and benchmarking trade-offs]` | `src/tracking/byte_tracker.py` | `ByteTracker(Tracker)` — `__init__(track_high_thresh=0.25, track_low_thresh=0.1, new_track_thresh=0.25, track_buffer=30, match_thresh=0.8, fuse_score=True)`, wraps `ultralytics.trackers.byte_tracker.BYTETracker` |
| Tracking sanity-check CLI (Section 3, Section 8) | `[IMPLEMENTED]` | `scripts/track_video.py` | `main()` — wires `FrameSource` → `YoloDetector` → `ByteTracker` → drawn `id=<n> <class> <confidence>` labels, to `--output` and/or `--display` |
| Tracker test coverage (Section 3, Section 16) | `[IMPLEMENTED]` | `tests/test_tracker.py` | 6 tests directly against `ByteTracker` (id stability, crossing paths, occlusion recovery vs. timeout, field propagation) + 1 integration test (`test_detector_to_tracker_pipeline_on_real_fixture_frames`) chaining `YoloDetector` → `ByteTracker` on `sample_video_path` |
| MOTA / IDF1 tracking accuracy metrics (Section 3, Section 15) | `[PLANNED]` | — | requires ground-truth tracking annotations TRACE does not have yet; deliberately not computed or estimated this phase |
| Trajectory / per-step motion analysis (Section 4) | `[IMPLEMENTED — pixel-space only]` | `src/trajectories/trajectory.py` | `centroid(bbox)`, `magnitude(vector)`, `MotionStep` (dataclass: `object_id`, `frame_id`, `timestamp`, `position`, `displacement`, `velocity`, `speed`, `direction`, `acceleration`, `is_stationary`), `Trajectory` (`update(position, timestamp, frame_id) -> MotionStep \| None`), `TrajectoryManager` (`update(tracks: list[Track]) -> list[MotionStep]`, `get_path(object_id)`) |
| Trajectory sanity-check CLI (Section 4, Section 8) | `[IMPLEMENTED]` | `scripts/trajectory_video.py` | `main()` — wires `FrameSource` → `YoloDetector` → `ByteTracker` → `TrajectoryManager` → drawn path + box (color signals stationary/moving) + speed/state label, to `--output` and/or `--display` |
| Trajectory test coverage (Section 4, Section 16) | `[IMPLEMENTED]` | `tests/test_trajectory.py` | constant velocity, a stop (deceleration signal), a direction change, jitter-tolerant stationary classification, `TrajectoryManager` routing via centroid |
| Dwell time (Section 4, Section 9) | `[PLANNED]` | — | inherently zone-relative; deferred until zones exist in the Event Engine (Section 7) |
| Ground-plane homography calibration (Section 5) | `[IMPLEMENTED]` | `src/geometry/homography.py` | `ground_contact_point(bbox)`, `GroundPlaneHomography` (`.pixel_to_world()`, `.from_correspondences()`, `.from_config()`), `load_camera_homography(camera_id, configs_dir)`; example config `configs/cameras/demo.json` |
| Real-world estimated_speed (Section 6) | `[IMPLEMENTED]` | `src/geometry/speed.py` | `EstimatedSpeedSample` (dataclass, field is `estimated_speed`, never bare `speed`), `SpeedEstimator` (`update(tracks: list[Track]) -> list[EstimatedSpeedSample]`) |
| Homography + speed test coverage (Section 5, Section 6, Section 16) | `[IMPLEMENTED]` | `tests/test_homography.py`, `tests/test_speed_estimator.py` | synthetic 20px=1m plane: known-point recovery within `1e-6` abs, known 1 m/s motion recovered within `rel=1e-3`, real-elapsed-time (not FPS) check, `estimated_speed` naming enforced by a dedicated test |
| Dwell-time bookkeeping (Section 4) | `[IMPLEMENTED — bookkeeping only, real zone detection is [PLANNED]]` | `src/trajectories/dwell.py` | `ZoneVisit`, `DwellTracker` (`update(object_id, zone_id, is_inside, timestamp)`, `.visits()`, `.total_dwell_time()`); consumes a plain `is_inside` boolean, decoupled from the point-in-polygon geometry that would produce it |
| Line-crossing detection — geometric primitive only (Section 5, Section 7) | `[IMPLEMENTED]` | `src/geometry/line_crossing.py` | `Line`, `segments_intersect()`, `detect_line_crossing(line, point_before, point_after) -> LineCrossing \| None`, `LineCrossingDetector` (`.update(object_id, point) -> list[LineCrossing]`), `load_camera_lines(camera_id, configs_dir)` |
| Zone (point-in-polygon) detection with debounce — geometric primitive only (Section 5, Section 7) | `[IMPLEMENTED]` | `src/geometry/zone.py` | `Zone`, `point_in_polygon()`, `ZoneDetector` (`.update(object_id, point, timestamp, frame_id) -> list[ZoneTransition]`, `debounce_frames` config), `load_camera_zones(camera_id, configs_dir)` |
| Line/zone config format (Section 5, Section 7) | `[IMPLEMENTED]` | `configs/cameras/demo.json` | optional `"lines"`/`"zones"` arrays alongside `"correspondences"` in the same per-camera JSON file |
| Line/zone test coverage (Section 5, Section 7, Section 16) | `[IMPLEMENTED]` | `tests/test_line_crossing.py`, `tests/test_zone.py` | fast-moving point pair caught by segment intersection (missed by naive proximity), false-positive avoidance (infinite-line-extension crossing without touching the finite segment), zone-boundary flicker suppressed by debounce, sustained entry after flicker still confirms |
| Event schema (Section 7) | `[IMPLEMENTED]` | `src/events/event.py` | `Event` (dataclass: `event_type`, `object_id`, `class_name`, `timestamp`, `camera_id`, `confidence`, `metadata`), `.to_dict()` |
| `LINE_CROSSED` event (Section 5, Section 7) | `[IMPLEMENTED]` | `src/events/line_crossed.py` | `build_event(track, crossing, camera_id) -> Event` — pure translation of `geometry.line_crossing.LineCrossing` |
| `ZONE_ENTERED` / `ZONE_EXITED` events (Section 5, Section 7) | `[IMPLEMENTED]` | `src/events/zone_entered.py`, `src/events/zone_exited.py` | `build_event(track, transition, camera_id) -> Event` — pure translation of `geometry.zone.ZoneTransition` |
| `OVERSPEED` event (Section 6, Section 7) | `[IMPLEMENTED — default threshold not yet validated against real footage]` | `src/events/overspeed.py` | `OverspeedRule` (`update(track, sample) -> Event \| None`; moving-average smoothing over `window` samples, fires once per over-limit period) |
| `STOPPED` event (Section 4, Section 7) | `[IMPLEMENTED]` | `src/events/stopped.py` | `StoppedRule` (`update(track, step) -> Event \| None`; sustained-duration streak confirmation) |
| `SUDDEN_STOP` event (Section 4, Section 7) | `[IMPLEMENTED — default threshold found too sensitive against real footage, see Section 7]` | `src/events/sudden_stop.py` | `SuddenStopRule` (`update(track, step) -> Event \| None`; acceleration-magnitude + speed-decrease confirmation) |
| `LOITERING` event (Section 4, Section 7) | `[IMPLEMENTED]` | `src/events/loitering.py` | `LoiteringRule` (`update(track, zone_id, dwell_tracker, timestamp) -> Event \| None`; cumulative dwell, fires once ever per object/zone) |
| `OBJECT_APPEARED` event (Section 3, Section 7) | `[IMPLEMENTED]` | `src/events/object_appeared.py` | `ObjectAppearedRule` (`update(track) -> Event \| None`; fires once per `object_id`, ever) |
| `OBJECT_DISAPPEARED` event (Section 3, Section 7) | `[IMPLEMENTED]` | `src/events/object_disappeared.py` | `ObjectDisappearedRule` (`update(tracks, current_timestamp) -> list[Event]`; absence-duration confirmation) |
| Event Engine orchestrator (Section 7) | `[IMPLEMENTED]` | `src/events/engine.py` | `EventEngine` — wires `TrajectoryManager`, `SpeedEstimator`, `LineCrossingDetector`, `ZoneDetector`, `DwellTracker` internally; `update(tracks: list[Track], timestamp: float) -> list[Event]` |
| End-to-end event pipeline CLI (Section 7, Section 8) | `[IMPLEMENTED]` | `scripts/event_video.py` | `main()` — `FrameSource` → `YoloDetector` → `ByteTracker` → `EventEngine`, printing each event |
| Event engine test coverage (Section 7, Section 16) | `[IMPLEMENTED]` | `tests/test_events_*.py` (7 files), `tests/test_event_engine.py` | one file per event type/pair; engine-level flicker suppression, lifecycle timeout behavior, jitter-tolerant STOPPED, and a real-fixture-video structure-only smoke test |
| Database schema — `cameras`, `videos`, `zones`, `lines`, `objects`, `track_points`, `events` (Section 9) | `[IMPLEMENTED]` | `src/database/models.py` | `Camera`, `Video`, `Zone`, `Line`, `TrackedObject`, `TrackPoint`, `Event` (SQLAlchemy 2.0 declarative) |
| Database engine/session setup (Section 9) | `[IMPLEMENTED]` | `src/database/db.py` | `get_engine(database_url=None)`, `create_all(engine)`, `get_session_factory(engine)` |
| Repository layer (Section 9, Section 10) | `[IMPLEMENTED]` | `src/database/repository.py` | `get_or_create_camera`, `create_video`, `get_or_create_zone`, `get_or_create_line`, `get_or_create_object`, `add_track_point`, `add_event`, `add_event_from_pipeline`, `get_events_for_object`, `get_track_points_for_object` |
| Event database sink — Phase 7's Event Engine now actually persists, not just prints (Section 7, Section 9) | `[IMPLEMENTED]` | `scripts/persist_video.py` | `main()` — `FrameSource` → `YoloDetector` → `ByteTracker` → `EventEngine` → `repository` calls per frame |
| Database schema/repository test coverage (Section 9, Section 16) | `[IMPLEMENTED]` | `tests/test_database_schema.py`, `tests/test_repository.py` | FK/constraint enforcement verified against real Postgres; repository round-trip (insert object + events, query back, relationships resolve) |
| Postgres service exposed to the host (Section 9) | `[IMPLEMENTED]` | `docker-compose.yml` | `db` service (already existed from Phase 0) gained `ports: ["5433:5432"]`; obsolete top-level `version:` key removed |
| Analytics — all 8 Section 11 functions (Section 11) | `[IMPLEMENTED]` | `src/analytics/queries.py` | `object_count`, `line_crossing_count`, `zone_violation_count`, `average_dwell_time`, `traffic_volume`, `busiest_hours`, `event_frequency`, `per_class_stats` |
| Analytics test coverage, seeded with known expected results (Section 11, Section 16) | `[IMPLEMENTED]` | `tests/test_analytics.py` | deterministic seed scenario (2 objects, 7 events, one 3.0s zone visit, 3 crossings from 2 objects), every function asserted against its hand-computed expected value |
| Migration tooling (e.g. Alembic) for evolving an already-deployed schema (Section 9) | `[PLANNED]` | — | `create_all()` is schema *setup* (dev/tests), not a migration tool; out of scope for Phase 8 |
| `busiest_hours` wall-clock anchoring for file-based (video-relative) sources (Section 11) | `[PLANNED]` | — | `videos.started_at` exists in the schema for this but isn't wired in yet; confirmed real limitation, see Section 11 |
| `ZoneDetector.is_inside()` accessor (Section 5) | `[IMPLEMENTED — added in Phase 7]` | `src/geometry/zone.py` | purely additive read-only method exposing debounced containment state, needed to feed `LOITERING`'s `DwellTracker`; existing `ZoneDetector` tests and behavior unchanged |
| FastAPI app + global error handling (Section 10) | `[IMPLEMENTED]` | `src/api/app.py` | `app` (FastAPI instance), `handle_unexpected_error` (catches `Exception`, returns clean `{"detail": "internal server error"}`, never a stack trace) |
| Request-scoped DB session dependency (Section 10) | `[IMPLEMENTED]` | `src/api/deps.py` | `get_db()` |
| API request/response schemas + validation (Section 10) | `[IMPLEMENTED]` | `src/api/schemas.py` | `CameraCreate`/`Read`, `VideoCreate`/`Read`, `ZoneCreate`/`Read` (≥3-point polygon validator), `LineCreate`/`Read` (start≠end validator), `EventRead`, `TrackPointRead`, `TrajectoryRead`, `AnalyticsSummary` |
| `POST /cameras`, `POST /videos` (Section 10) | `[IMPLEMENTED]` | `src/api/routers/cameras.py`, `src/api/routers/videos.py` | `create_camera`, `create_video` |
| `GET /cameras/{camera_id}/events` (Section 7, Section 10) | `[IMPLEMENTED]` | `src/api/routers/cameras.py` | `list_camera_events` |
| `GET /objects/{id}/trajectory` (Section 4, Section 10) | `[IMPLEMENTED]` | `src/api/routers/objects.py` | `get_object_trajectory` — `{id}` is the internal DB PK, not the Tracker's per-camera `object_id` |
| `POST /zones`, `POST /lines` (Section 5, Section 10) | `[IMPLEMENTED]` | `src/api/routers/zones.py`, `src/api/routers/lines.py` | `create_zone`, `create_line` |
| `GET /analytics` (Section 11, Section 10) | `[IMPLEMENTED]` | `src/api/routers/analytics.py` | `get_analytics` — bundles 7 of Section 11's 8 functions (`busiest_hours` omitted from the default bundle; callable directly from `analytics.queries` if needed) |
| API test coverage — 1 success + 1 failure per endpoint, plus the 500 handler (Section 10, Section 16) | `[IMPLEMENTED]` | `tests/test_api.py` | 15 tests via FastAPI's `TestClient`; also manually verified against a real running `uvicorn` server with `curl` |
| `POST /agent/query` (Section 10, Section 12) | `[PLANNED]` | — | depends on the not-yet-built Vision Agent |
| `POST /alerts` (Section 10) | `[PLANNED]` | — | depends on a not-yet-built alert-rule system |

### What I should know
- [ ] I can explain why the API sits between the pipeline/database and every consumer (dashboard, agent).
- [ ] I can explain what Pydantic validation buys you that plain dict-based JSON handling doesn't.
- [ ] I can explain the API → service → repository layering and why route handlers shouldn't contain SQL.

### Questions to test myself
1. Why should `POST /zones` validate polygon geometry at the API boundary rather than deep inside the event engine?
2. What's the risk of skipping the service layer and calling the database directly from route handlers?
3. Why does the agent talk to the same API/database as the dashboard, instead of having its own private data path?
