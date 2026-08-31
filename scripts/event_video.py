"""Run the full TRACE pipeline end-to-end on a video file or camera and print
every event as it's produced:

    FrameSource -> Detector -> Tracker -> Trajectory -> Geometry -> Event Engine

Database wiring (Phase 8) is not part of this script -- events are printed,
not persisted.

Usage:
    python scripts/event_video.py path/to/video.mp4 --camera-id demo
    python scripts/event_video.py 0 --camera-id demo --speed-limit 2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
from events.engine import EventEngine
from geometry.homography import load_camera_homography
from geometry.line_crossing import load_camera_lines
from geometry.zone import load_camera_zones
from tracking.byte_tracker import ByteTracker


def _parse_source(raw: str) -> "str | int":
    """A source that looks like a bare integer is a camera index; anything else is a file path."""
    try:
        return int(raw)
    except ValueError:
        return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="video file path or camera index (e.g. 0)")
    parser.add_argument("--camera-id", default="demo", help="which configs/cameras/<id>.json to load (default: %(default)s)")
    parser.add_argument("--configs-dir", default="configs/cameras", help="directory holding per-camera configs (default: %(default)s)")
    parser.add_argument("--num-frames", type=int, default=200, help="frames to process (default: 200)")
    parser.add_argument("--frame-skip", type=int, default=1, help="process every Nth frame (default: 1)")
    parser.add_argument("--confidence", type=float, default=0.25, help="detection confidence threshold (default: 0.25)")
    parser.add_argument("--classes", default=None, help="comma-separated class allowlist (default: %(default)s)")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics weights path/name (default: %(default)s)")
    parser.add_argument("--track-buffer", type=int, default=30, help="frames a lost track survives before termination (default: 30)")
    parser.add_argument("--speed-limit", type=float, default=5.0, help="OVERSPEED threshold, world units/s (default: 5.0)")
    parser.add_argument("--min-stationary-seconds", type=float, default=2.0, help="STOPPED duration threshold (default: 2.0)")
    parser.add_argument("--min-dwell-seconds", type=float, default=5.0, help="LOITERING cumulative dwell threshold (default: 5.0)")
    parser.add_argument("--missing-timeout-seconds", type=float, default=2.0, help="OBJECT_DISAPPEARED absence threshold (default: 2.0)")
    args = parser.parse_args()

    class_allowlist = (
        tuple(c.strip() for c in args.classes.split(",")) if args.classes else DEFAULT_CLASS_ALLOWLIST
    )

    homography = load_camera_homography(args.camera_id, configs_dir=args.configs_dir)
    lines = load_camera_lines(args.camera_id, configs_dir=args.configs_dir)
    zones = load_camera_zones(args.camera_id, configs_dir=args.configs_dir)
    print(f"loaded camera_id={args.camera_id!r}: {len(lines)} line(s), {len(zones)} zone(s)")

    source = _parse_source(args.source)
    detector = YoloDetector(
        model_path=args.model,
        confidence_threshold=args.confidence,
        class_allowlist=class_allowlist,
    )
    tracker = ByteTracker(track_buffer=args.track_buffer)
    engine = EventEngine(
        camera_id=args.camera_id,
        homography=homography,
        lines=lines,
        zones=zones,
        speed_limit=args.speed_limit,
        min_stationary_seconds=args.min_stationary_seconds,
        min_dwell_seconds=args.min_dwell_seconds,
        missing_timeout_seconds=args.missing_timeout_seconds,
    )

    with FrameSource(source, frame_skip=args.frame_skip) as frame_source:
        frame_count = 0
        for _ in range(args.num_frames):
            frame: Frame | None = frame_source.read()
            if frame is None:
                print(f"source exhausted after {frame_count} frame(s)")
                break

            # Detector -> Tracker -> (Trajectory + Geometry, internally) -> Event Engine,
            # once per frame, in order, even when nothing is detected.
            detections = detector.detect(frame)
            tracks = tracker.update(detections)
            events = engine.update(tracks, timestamp=frame.timestamp)

            for event in events:
                print(
                    f"[{event.timestamp:8.3f}s] {event.event_type:<18} "
                    f"object_id={event.object_id:<4} class={event.class_name:<10} "
                    f"confidence={event.confidence:.2f} metadata={event.metadata}"
                )

            frame_count += 1


if __name__ == "__main__":
    main()
