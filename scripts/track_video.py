"""Run a video file or camera through FrameSource + YoloDetector + ByteTracker and
draw stable track IDs for visual sanity-checking: save an annotated video,
display it live, or both.

Usage:
    python scripts/track_video.py path/to/video.mp4 --output out.mp4
    python scripts/track_video.py 0 --display --confidence 0.4 --track-buffer 60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
from tracking.byte_tracker import ByteTracker
from tracking.tracker import Track

BOX_COLOR = (0, 255, 0)  # BGR -- drawing happens in BGR, the space cv2's own primitives expect


def _parse_source(raw: str) -> "str | int":
    """A source that looks like a bare integer is a camera index; anything else is a file path."""
    try:
        return int(raw)
    except ValueError:
        return raw


def _draw_tracks(image_bgr, tracks: list[Track]):
    for track in tracks:
        x_min, y_min, x_max, y_max = (int(round(v)) for v in track.bbox)
        cv2.rectangle(image_bgr, (x_min, y_min), (x_max, y_max), BOX_COLOR, 2)
        label = f"id={track.object_id} {track.class_name} {track.confidence:.2f}"
        cv2.putText(
            image_bgr, label, (x_min, max(0, y_min - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, BOX_COLOR, 1, cv2.LINE_AA,
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

    writer = None
    try:
        with FrameSource(source, frame_skip=args.frame_skip) as frame_source:
            frame_count = 0
            for _ in range(args.num_frames):
                frame: Frame | None = frame_source.read()
                if frame is None:
                    print(f"source exhausted after {frame_count} frame(s)")
                    break

                # tracker.update() must run once per frame, in order, even when
                # detections is empty -- see Tracker's docstring for why.
                detections = detector.detect(frame)
                tracks = tracker.update(detections)

                image_bgr = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
                _draw_tracks(image_bgr, tracks)

                if args.output:
                    if writer is None:
                        height, width = image_bgr.shape[:2]
                        writer = cv2.VideoWriter(
                            args.output, cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (width, height)
                        )
                    writer.write(image_bgr)

                if args.display:
                    cv2.imshow("TRACE tracks", image_bgr)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("stopped by user")
                        break

                ids = [t.object_id for t in tracks]
                print(
                    f"frame_id={frame.frame_id:>5}  timestamp={frame.timestamp:.3f}s  "
                    f"detections={len(detections)}  tracks={len(tracks)}  ids={ids}"
                )
                frame_count += 1
    finally:
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
