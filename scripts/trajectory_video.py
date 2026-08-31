"""Run a video file or camera through FrameSource + YoloDetector + ByteTracker +
TrajectoryManager and draw each object's accumulated path (plus its current
box, id, speed, and stationary/moving state) for visual sanity-checking.

Usage:
    python scripts/trajectory_video.py path/to/video.mp4 --output out.mp4
    python scripts/trajectory_video.py 0 --display --stationary-threshold 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np

from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
from tracking.byte_tracker import ByteTracker
from tracking.tracker import Track
from trajectories.trajectory import TrajectoryManager

BOX_COLOR = (0, 255, 0)  # BGR
PATH_COLOR = (0, 200, 255)  # BGR
STATIONARY_COLOR = (0, 0, 255)  # BGR


def _parse_source(raw: str) -> "str | int":
    """A source that looks like a bare integer is a camera index; anything else is a file path."""
    try:
        return int(raw)
    except ValueError:
        return raw


def _draw(image_bgr, tracks: list[Track], trajectory_manager: TrajectoryManager, latest_step_by_id: dict):
    for track in tracks:
        path = trajectory_manager.get_path(track.object_id)
        if len(path) >= 2:
            points = np.array([(int(round(x)), int(round(y))) for x, y in path], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(image_bgr, [points], isClosed=False, color=PATH_COLOR, thickness=2)

        x_min, y_min, x_max, y_max = (int(round(v)) for v in track.bbox)
        step = latest_step_by_id.get(track.object_id)
        color = STATIONARY_COLOR if (step is not None and step.is_stationary) else BOX_COLOR
        cv2.rectangle(image_bgr, (x_min, y_min), (x_max, y_max), color, 2)

        label = f"id={track.object_id} {track.class_name}"
        if step is not None:
            state = "stationary" if step.is_stationary else "moving"
            label += f" {step.speed:.0f}px/s {state}"
        cv2.putText(
            image_bgr, label, (x_min, max(0, y_min - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )
    return image_bgr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="video file path or camera index (e.g. 0)")
    parser.add_argument("--output", default=None, help="path to save the annotated video")
    parser.add_argument("--display", action="store_true", help="show the annotated video live (press q to quit)")
    parser.add_argument("--num-frames", type=int, default=200, help="frames to process (default: 200)")
    parser.add_argument("--frame-skip", type=int, default=1, help="process every Nth frame (default: 1)")
    parser.add_argument("--confidence", type=float, default=0.25, help="detection confidence threshold (default: 0.25)")
    parser.add_argument("--classes", default=None, help="comma-separated class allowlist (default: %(default)s)")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics weights path/name (default: %(default)s)")
    parser.add_argument("--track-buffer", type=int, default=30, help="frames a lost track survives before termination (default: 30)")
    parser.add_argument("--stationary-threshold", type=float, default=30.0, help="px/s below which a track reads stationary (default: 30.0)")
    args = parser.parse_args()

    if not args.output and not args.display:
        parser.error("pass --output PATH and/or --display so there's somewhere to see the result")

    class_allowlist = (
        tuple(c.strip() for c in args.classes.split(",")) if args.classes else DEFAULT_CLASS_ALLOWLIST
    )

    source = _parse_source(args.source)
    detector = YoloDetector(
        model_path=args.model,
        confidence_threshold=args.confidence,
        class_allowlist=class_allowlist,
    )
    tracker = ByteTracker(track_buffer=args.track_buffer)
    trajectory_manager = TrajectoryManager(stationary_speed_threshold=args.stationary_threshold)

    writer = None
    try:
        with FrameSource(source, frame_skip=args.frame_skip) as frame_source:
            frame_count = 0
            for _ in range(args.num_frames):
                frame: Frame | None = frame_source.read()
                if frame is None:
                    print(f"source exhausted after {frame_count} frame(s)")
                    break

                # tracker.update() and trajectory_manager.update() both run once
                # per frame, in order, even when detections/tracks are empty.
                detections = detector.detect(frame)
                tracks = tracker.update(detections)
                steps = trajectory_manager.update(tracks)
                latest_step_by_id = {step.object_id: step for step in steps}

                image_bgr = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
                _draw(image_bgr, tracks, trajectory_manager, latest_step_by_id)

                if args.output:
                    if writer is None:
                        height, width = image_bgr.shape[:2]
                        writer = cv2.VideoWriter(
                            args.output, cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (width, height)
                        )
                    writer.write(image_bgr)

                if args.display:
                    cv2.imshow("TRACE trajectories", image_bgr)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("stopped by user")
                        break

                print(
                    f"frame_id={frame.frame_id:>5}  timestamp={frame.timestamp:.3f}s  "
                    f"tracks={len(tracks)}  motion_steps={len(steps)}"
                )
                frame_count += 1
    finally:
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
