"""Stage 2 data prep: domain adaptation on TRACE's own footage.

Stage 1 (stage1/) closes the "generic COCO, 80 classes" gap down to TRACE's
6 target classes, but every one of its images is still generic internet
photography -- different cameras, angles, lighting, resolution than what
TRACE actually deploys against. Stage 2's entire purpose is closing THAT
gap: adapting the Stage 1 model to TRACE's real deployment conditions (one
specific webcam, indoor lighting, 640x480, a person moving through frame) --
not just "more training data" in the abstract.

Source footage: data/sample.mp4 only (the real ~16s/244-frame/15fps webcam
clip already used throughout Phase 2/8/9/10 testing) -- confirmed with the
user rather than assumed: this machine's camera 0 opens but returns
essentially black frames (mean pixel value ~1.8/255), and activating it to
record a new scene without the user actively setting one up first would be
a real privacy action, not just a code change, so no new footage was
recorded this phase. This is a real, reportable scope limitation: Stage 2
adapts to ONE scene, not several.

Labeling approach, exactly: every 8th frame of sample.mp4 is extracted
(244 frames / 8 ~= 30 frames) via FrameSource(frame_skip=8) -- the same
frame-sampling primitive Section 8's pipeline already uses, not a new
mechanism. Each extracted frame is auto-labeled by running the Stage 1
model's own predictions on it (YoloDetector, same confidence threshold the
live pipeline uses, 0.25) and converting each Detection to a YOLO-format
label line. This is genuinely "auto-label with the Stage 1 model's own
predictions," not hand-drawn boxes -- errors Stage 1 makes can and do show
up here uncorrected for any frame not selected below for human review.

A SAMPLE of frames is then selected for human review/correction (not the
full ~30 -- see select_frames_for_review()) and annotated preview images are
written to review/ for a human to look at. training/stage2/apply_review.py
(a separate script) is what actually rewrites a reviewed frame's label file
once corrections are known -- this script only proposes.

Usage:
    python training/stage2/prepare_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import cv2

from detection.frame_source import FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector

STAGE2_DIR = Path(__file__).resolve().parent
DATA_DIR = STAGE2_DIR.parent / "data" / "stage2"
IMAGES_DIR = DATA_DIR / "images" / "all"
LABELS_DIR = DATA_DIR / "labels" / "all"
REVIEW_DIR = DATA_DIR / "review"

REPO_ROOT = STAGE2_DIR.parent.parent
SOURCE_VIDEO = REPO_ROOT / "data" / "sample.mp4"
STAGE1_WEIGHTS = REPO_ROOT / "models" / "yolov8n_trace_stage1.pt"

FRAME_SKIP = 8
CONFIDENCE_THRESHOLD = 0.25
REVIEW_BOX_COLOR = (0, 200, 255)  # BGR -- amber, distinct from any other script's box color


def _detection_to_yolo_line(det, image_width: int, image_height: int) -> str:
    class_id = DEFAULT_CLASS_ALLOWLIST.index(det.class_name)
    x_min, y_min, x_max, y_max = det.bbox
    cx = ((x_min + x_max) / 2) / image_width
    cy = ((y_min + y_max) / 2) / image_height
    w = (x_max - x_min) / image_width
    h = (y_max - y_min) / image_height
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def extract_and_autolabel() -> list[dict]:
    """Returns one dict per extracted frame: frame_id, image_path, label_path,
    detections (the raw Detection list, for review-selection/rendering)."""
    if not STAGE1_WEIGHTS.exists():
        raise FileNotFoundError(f"{STAGE1_WEIGHTS} not found -- run stage1/train.py then export_weights.py --stage 1 first.")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    detector = YoloDetector(model_path=str(STAGE1_WEIGHTS), confidence_threshold=CONFIDENCE_THRESHOLD)
    source = FrameSource(str(SOURCE_VIDEO), source_id="sample", frame_skip=FRAME_SKIP)

    frames = []
    try:
        while True:
            frame = source.read()
            if frame is None:
                break
            detections = detector.detect(frame)
            height, width = frame.image.shape[:2]

            image_name = f"frame_{frame.frame_id:04d}.jpg"
            image_path = IMAGES_DIR / image_name
            # frame.image is RGB (FrameSource's boundary conversion) -- cv2.imwrite expects BGR.
            cv2.imwrite(str(image_path), cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR))

            label_path = LABELS_DIR / f"frame_{frame.frame_id:04d}.txt"
            lines = [_detection_to_yolo_line(d, width, height) for d in detections]
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

            frames.append(
                {
                    "frame_id": frame.frame_id,
                    "timestamp": frame.timestamp,
                    "image_path": image_path,
                    "label_path": label_path,
                    "detections": detections,
                }
            )
    finally:
        source.release()

    return frames


def select_frames_for_review(frames: list[dict], max_review: int = 8) -> list[dict]:
    """Picks the frames most worth a human's time: every one with ZERO
    detections (real risk of a missed object) and every one whose highest
    detection confidence is below 0.5 (real risk of a wrong box), then fills
    up to max_review with frames evenly spaced across the clip so the sample
    isn't only the risky ones -- a sanity check on the "normal" case too.
    Never silently reviews fewer than requested if more genuinely risky
    frames exist; only pads with spaced frames if there's room left."""
    risky = [
        f for f in frames if not f["detections"] or max((d.confidence for d in f["detections"]), default=0.0) < 0.5
    ]

    selected: list[dict] = list(risky[:max_review])
    remaining_slots = max_review - len(selected)
    if remaining_slots > 0:
        candidates = [f for f in frames if f not in selected]
        if candidates:
            step = max(1, len(candidates) // remaining_slots)
            for i in range(0, len(candidates), step):
                if len(selected) >= max_review:
                    break
                selected.append(candidates[i])

    selected.sort(key=lambda f: f["frame_id"])
    return selected


def render_review_images(review_frames: list[dict]) -> list[Path]:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for frame in review_frames:
        image_bgr = cv2.imread(str(frame["image_path"]))
        for det in frame["detections"]:
            x_min, y_min, x_max, y_max = (int(round(v)) for v in det.bbox)
            cv2.rectangle(image_bgr, (x_min, y_min), (x_max, y_max), REVIEW_BOX_COLOR, 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(image_bgr, label, (x_min, max(0, y_min - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, REVIEW_BOX_COLOR, 2)
        out_path = REVIEW_DIR / f"review_frame_{frame['frame_id']:04d}.jpg"
        cv2.imwrite(str(out_path), image_bgr)
        written.append(out_path)
    return written


def main() -> None:
    frames = extract_and_autolabel()
    print(f"extracted + auto-labeled {len(frames)} frames from {SOURCE_VIDEO} (every {FRAME_SKIP}th frame)")

    review_frames = select_frames_for_review(frames)
    review_images = render_review_images(review_frames)
    print(f"selected {len(review_frames)} frames for human review:")
    for frame, image_path in zip(review_frames, review_images):
        det_summary = ", ".join(f"{d.class_name}:{d.confidence:.2f}" for d in frame["detections"]) or "(no detections)"
        print(f"  frame_{frame['frame_id']:04d} (t={frame['timestamp']:.2f}s) -- {det_summary} -- {image_path}")


if __name__ == "__main__":
    main()
