"""YOLO detector: concrete Detector backed by a pretrained Ultralytics YOLO model."""

from __future__ import annotations

import os

import cv2

from detection.detector import Detection, Detector
from detection.frame_source import Frame

DEFAULT_CLASS_ALLOWLIST = ("person", "car", "motorcycle", "bus", "truck", "bicycle")

# Which weights the live pipeline loads when model_path isn't given
# explicitly. Phase 13 built a real two-stage fine-tune (training/) -- Stage 1
# narrows yolov8n to TRACE's 6 classes on a COCO128 subset, Stage 2 further
# adapts Stage 1 on real footage -- and measured both against this exact
# pretrained baseline on two separate held-out sets before choosing. Result:
# Stage 1 collapsed (precision cratered to ~0.003-0.005, 5/6 classes hit
# exactly zero mAP on held-out COCO images); Stage 2 partially recovered
# localization quality on the ONE real scene it adapted to but never fixed
# the inherited precision collapse. The plain pretrained baseline stayed
# reliable across the board on every held-out set tested. Neither fine-tuned
# stage is the default as a result -- see TRACE_STUDY_GUIDE.md Section 2 for
# the full real numbers and reasoning, not just the choice. Overridable
# per-process via TRACE_DETECTOR_WEIGHTS without a code change (e.g. to try
# models/yolov8n_trace_stage1.pt or _stage2.pt anyway, or point at a future,
# better fine-tune) -- explicit and configurable, per Phase 13's requirement.
DEFAULT_MODEL_PATH = os.environ.get("TRACE_DETECTOR_WEIGHTS", "yolov8n.pt")

# Same override pattern as DEFAULT_MODEL_PATH above -- Phase 16 externalized this
# for deployment (docker-compose/production), where confidence thresholds are a
# per-environment tuning knob, not something that should need a code change.
DEFAULT_CONFIDENCE_THRESHOLD = float(os.environ.get("TRACE_DETECTOR_CONFIDENCE", "0.25"))


class YoloDetector(Detector):
    """Pretrained YOLO (Ultralytics) behind the Detector interface. Inference only — no training
    (training/ is a separate, offline fine-tuning pipeline -- Section 2's fine-tuning subsection --
    that produces the weights this class can be pointed at; it never trains at runtime).

    `model_path` names any Ultralytics-compatible weights file, defaulting to
    `DEFAULT_MODEL_PATH` above; Ultralytics downloads a named pretrained
    model automatically on first use if not already cached locally (a
    fine-tuned path, e.g. `models/yolov8n_trace_stage1.pt` or `_stage2.pt`,
    must already exist on disk -- see training/export_weights.py).

    `class_allowlist=None` disables filtering (every COCO class is kept);
    pass an explicit iterable to restrict to those class names.
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        class_allowlist: "tuple[str, ...] | None" = DEFAULT_CLASS_ALLOWLIST,
        device: str | None = None,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0, 1], got {confidence_threshold}")

        from ultralytics import YOLO  # imported lazily so mocking Detector doesn't require ultralytics/torch

        self._model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.class_allowlist = set(class_allowlist) if class_allowlist is not None else None
        self.device = device

    def detect(self, frame: Frame) -> list[Detection]:
        # Frame.image is RGB (FrameSource's boundary conversion). Ultralytics'
        # numpy-array input path assumes BGR and flips it to RGB internally
        # (see BasePredictor.preprocess) -- feeding it RGB directly would get
        # silently double-flipped back to BGR before the model ever sees it.
        # Convert back to BGR here so the model actually receives RGB.
        image_bgr = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)

        results = self._model.predict(
            image_bgr,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )[0]

        class_names = results.names
        detections = []
        for box in results.boxes:
            class_name = class_names[int(box.cls[0])]
            if self.class_allowlist is not None and class_name not in self.class_allowlist:
                continue

            x_min, y_min, x_max, y_max = (float(v) for v in box.xyxy[0])
            detections.append(
                Detection(
                    bbox=(x_min, y_min, x_max, y_max),
                    class_name=class_name,
                    confidence=float(box.conf[0]),
                    frame_id=frame.frame_id,
                    timestamp=frame.timestamp,
                )
            )
        return detections
