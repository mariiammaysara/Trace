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

### Why we choose our detector for TRACE `[PLANNED — decision pending benchmarking, Section 20]`

- Default candidate: a YOLO variant, for tooling maturity, speed, and ease of export to ONNX/TensorRT (Section 14).
- RT-DETR kept as a documented alternative to benchmark against once the pipeline is running (Section 20 experiment).
- Decision criteria once both are tried: FPS on target hardware, accuracy on TRACE's actual scenes, ease of deployment.

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

### How the tracker in TRACE works, frame-by-frame `[PLANNED]`

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

### Centroids and position

- A box is reduced to a single representative point — usually the **centroid** `((x_min+x_max)/2, (y_min+y_max)/2)`, sometimes the bottom-center point (better approximates "where the object touches the ground," useful for geometry/speed later).
- **How TRACE uses it:** every trajectory is a time-ordered list of centroids per `object_id`, stored as `track_points`.

### Displacement, velocity, acceleration

- **Displacement** between two points in time: `Δposition = position(t2) - position(t1)`.
- **Velocity** (pixels/sec, or real-world units after geometry correction): `displacement / Δt`.
- **Acceleration**: rate of change of velocity — useful for detecting `SUDDEN_STOP` (large negative acceleration) as an event.

### Direction

- Computed from the displacement vector's angle, usually bucketed into compass-style categories (N, NE, E...) or kept as a raw angle for finer analytics.

### Stationary state and movement state

- An object is "stationary" if its velocity stays below a small noise-tolerant threshold for some duration — this threshold must account for natural detection/tracking jitter, or every parked object will falsely flicker between "moving" and "stationary."

### Dwell time

- Total time an object's track has spent inside a defined zone (or simply "present in frame," depending on the metric).
- Computed as `exit_timestamp - entry_timestamp` per zone-visit, summed if the object enters/exits multiple times.

### The math, at implementation level

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

### Homography and perspective transformation

- A **homography** is a 2D-to-2D projective transformation that maps points on a flat plane in the image (e.g., a road surface) to real-world coordinates on that same plane, given a handful of known correspondence points (e.g., 4 points whose real-world distances are known/measured).
- This is the **practical, lightweight calibration TRACE relies on** by default: mark 4+ reference points in the camera view whose real-world layout is known (e.g., measured lane markings), compute a homography, and use it to convert any pixel position on that ground plane to an approximate real-world position — without needing full intrinsic/extrinsic camera calibration.
- **Key limitation:** homography is only valid for points on the calibrated *plane* (typically the ground). It does not correctly map a point at head-height (a person's centroid) to ground-plane real-world coordinates without an added approximation (e.g., using the bottom-center of the box instead of the centroid, since it's closer to where the object contacts the ground).

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

### The correct(ed) approach TRACE uses `[PLANNED]`

```text
1. Pixel position (bottom-center of box) at t1 and t2
2. Apply homography → estimated ground-plane real-world position at t1, t2
3. real_distance = euclidean distance between the two world-plane points
4. elapsed_time  = t2 - t1   (from frame timestamps, not assumed constant FPS)
5. estimated_speed = real_distance / elapsed_time
```

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

### Event types — meaning, inputs, logic, edge cases `[PLANNED]`

| Event | Meaning | Required input | Core logic | Key edge case |
|---|---|---|---|---|
| `LINE_CROSSED` | Object crossed a configured virtual line | consecutive centroid pair, line geometry | check if the segment between two consecutive points intersects the line, determine side-before/side-after for direction | fast objects can "teleport" past a thin line between frames — must check segment intersection, not just point-in-front/behind |
| `ZONE_ENTERED` / `ZONE_EXITED` | Object crossed a polygon boundary | centroid, zone polygon | point-in-polygon test, compare current vs previous frame's containment | object flickering at a zone edge can fire enter/exit repeatedly — needs debounce/hysteresis |
| `OVERSPEED` | Estimated speed exceeds a configured limit | estimated speed (Section 6), configured limit | simple threshold compare | noisy single-frame speed spikes must be smoothed before comparing, or false alerts spike |
| `STOPPED` | Object stationary beyond a threshold duration | velocity history | velocity below noise threshold sustained over N seconds | must distinguish "genuinely stopped" from tracker jitter (Section 4) |
| `SUDDEN_STOP` | Rapid deceleration | velocity/acceleration history | large negative acceleration within a short window | must use real elapsed time, not frame count, given variable FPS |
| `LOITERING` | Present/stationary in an area beyond a threshold | dwell time, zone or general presence | dwell time exceeds configured threshold | requires deciding whether brief tracking loss resets the timer or not (see Failure Cases, Section 17) |
| `OBJECT_APPEARED` | A new track was created | track lifecycle state | new `object_id` created this frame | distinguishing a genuinely new object from a re-identification after occlusion |
| `OBJECT_DISAPPEARED` | A track was terminated | track lifecycle state | track exceeds missed-frame timeout | premature termination on brief occlusion produces false disappear/reappear pairs |

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

### Where it's implemented `[PLANNED]`

`src/events/` — one rule module per event type, all consuming the same per-frame track update stream and writing to a shared event sink (database, Section 9).

### What I should know
- [ ] I can explain why the event engine must be deterministic, not LLM-based.
- [ ] I can explain the debounce/hysteresis problem at zone boundaries.
- [ ] I can explain why `LINE_CROSSED` needs segment-intersection logic, not just point comparison.
- [ ] I can describe the shared event schema and why a common envelope matters.

### Questions to test myself
1. Why would checking "is the point past the line this frame" (instead of segment intersection) miss fast-moving objects?
2. What causes an object to flicker `ZONE_ENTERED`/`ZONE_EXITED` repeatedly, and how do you prevent it?
3. Why keep event-specific fields inside a `metadata` object rather than flattening everything into top-level columns?

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
- **Timestamps** — every table that represents something that happened needs one, stored consistently (UTC) to avoid timezone bugs across cameras/deployments.

### Why PostgreSQL

Mature, free, strong support for relational integrity, indexing, and time-range queries — a solid default for a system whose core value is structured, queryable history. (Not chosen for anything exotic like PostGIS/geo features at this stage, though zone polygons could eventually benefit from them — flagged as `[OPTIONAL]` future work.)

### The TRACE schema `[PLANNED]`

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

### Validation and error handling

- Validation happens automatically at the API boundary via Pydantic schemas (reject malformed input early).
- Error handling: convert internal exceptions (not-found, invalid zone geometry, database errors) into meaningful HTTP status codes and structured error responses, not raw stack traces.

### The actual TRACE API `[PLANNED]`

| Endpoint | Purpose | Input | Output |
|---|---|---|---|
| `POST /videos` | Register/ingest a video file for offline processing | file reference/path, camera_id | video record |
| `POST /cameras` | Register a camera source (live or file-backed) | name, location, calibration info | camera record |
| `GET /cameras/{id}/events` | List events for a camera, filterable by time range/type | camera_id, query params | list of events |
| `GET /objects/{id}/trajectory` | Full trajectory of one tracked object | object_id | ordered list of track_points |
| `GET /analytics` | Aggregated stats (Section 11) | filters (camera, time range) | aggregated metrics |
| `POST /zones` | Configure a polygon zone on a camera | camera_id, polygon coordinates | zone record |
| `POST /lines` | Configure a virtual line on a camera | camera_id, line coordinates | line record |
| `POST /agent/query` | Ask the Vision Agent a natural-language question | question text, optional context | agent's grounded answer |
| `POST /alerts` | Configure or trigger an alert rule | rule definition | alert/rule record |

*(Implementation locations to be filled in Section 19 once code exists.)*

---

> **Note:** Sections 11–18, 20, and 21 (listed in the Table of Contents) have not been written yet — only Sections 0–10 exist below this point, plus Section 19 (Implementation Map), added here ahead of the sections it numerically follows so completed work has somewhere to be recorded. Fill in 11–18/20/21 as those phases are planned; renumber/reorder at that point if needed.

## 19. Implementation Map

*Updated phase-by-phase as real code lands. Only rows for phases that are actually `[IMPLEMENTED]` belong here — see each section's own `[PLANNED]`/`[IMPLEMENTED]` tags for design-only content.*

| Concept (guide section) | Status | File(s) | Key symbols |
|---|---|---|---|
| Video ingestion / frame loop, frame skipping, BGR→RGB boundary (Section 8) | `[IMPLEMENTED]` | `src/detection/frame_source.py` | `Frame` (dataclass: `image`, `frame_id`, `timestamp`, `source_id`), `FrameSource(source: str \| int, source_id: str \| None = None, frame_skip: int = 1)` with `.read() -> Frame \| None`, `.release()`, `.is_live` |
| Frame preview / sanity-check CLI (Section 8) | `[IMPLEMENTED]` | `scripts/preview_frames.py` | `main()` — prints `frame_id` + `timestamp` for the first N frames of a file or camera source |
| FrameSource test coverage (Section 8, Section 16) | `[IMPLEMENTED]` | `tests/test_frame_source.py`, `tests/conftest.py` | fixtures `sample_video_path`, `sample_video_frame_count`; synthetic video generated at `tests/fixtures/sample_video.mp4` |

### What I should know
- [ ] I can explain why the API sits between the pipeline/database and every consumer (dashboard, agent).
- [ ] I can explain what Pydantic validation buys you that plain dict-based JSON handling doesn't.
- [ ] I can explain the API → service → repository layering and why route handlers shouldn't contain SQL.

### Questions to test myself
1. Why should `POST /zones` validate polygon geometry at the API boundary rather than deep inside the event engine?
2. What's the risk of skipping the service layer and calling the database directly from route handlers?
3. Why does the agent talk to the same API/database as the dashboard, instead of having its own private data path?
