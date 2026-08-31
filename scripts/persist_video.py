"""Run the full TRACE pipeline end-to-end on a video file or camera and
persist everything to Postgres, instead of just printing events:

    FrameSource -> Detector -> Tracker -> Trajectory -> Geometry -> Event Engine -> database

Requires the docker-compose `db` service running (see docker-compose.yml;
`docker compose up -d db`, reachable at localhost:5433 by default).

Usage:
    python scripts/persist_video.py path/to/video.mp4 --camera-id demo
    python scripts/persist_video.py 0 --camera-id demo --database-url postgresql://trace:trace@localhost:5433/trace
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database import repository
from database.db import create_all, get_engine, get_session_factory
from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, YoloDetector
from events.engine import EventEngine
from geometry.homography import load_camera_homography
from geometry.line_crossing import load_camera_lines
from geometry.zone import load_camera_zones
from trajectories.trajectory import centroid
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
    parser.add_argument("--database-url", default=None, help="defaults to database.db.DEFAULT_DATABASE_URL (localhost:5433)")
    parser.add_argument("--num-frames", type=int, default=200, help="frames to process (default: 200)")
    parser.add_argument("--frame-skip", type=int, default=1, help="process every Nth frame (default: 1)")
    parser.add_argument("--confidence", type=float, default=0.25, help="detection confidence threshold (default: 0.25)")
    parser.add_argument("--classes", default=None, help="comma-separated class allowlist (default: %(default)s)")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics weights path/name (default: %(default)s)")
    parser.add_argument("--commit-every", type=int, default=20, help="commit to the database every N frames (default: 20)")
    args = parser.parse_args()

    class_allowlist = (
        tuple(c.strip() for c in args.classes.split(",")) if args.classes else DEFAULT_CLASS_ALLOWLIST
    )

    engine = get_engine(args.database_url)
    create_all(engine)
    Session = get_session_factory(engine)

    homography = load_camera_homography(args.camera_id, configs_dir=args.configs_dir)
    lines = load_camera_lines(args.camera_id, configs_dir=args.configs_dir)
    zones = load_camera_zones(args.camera_id, configs_dir=args.configs_dir)

    with Session() as session:
        camera = repository.get_or_create_camera(session, args.camera_id)
        for zone in zones:
            repository.get_or_create_zone(session, camera, zone.id, zone.polygon)
        for line in lines:
            repository.get_or_create_line(session, camera, line.id, line.start, line.end)
        session.commit()
        print(f"loaded camera_id={args.camera_id!r}: {len(lines)} line(s), {len(zones)} zone(s) -> persisted to database")

        source = _parse_source(args.source)
        detector = YoloDetector(
            model_path=args.model,
            confidence_threshold=args.confidence,
            class_allowlist=class_allowlist,
        )
        tracker = ByteTracker()
        event_engine = EventEngine(camera_id=args.camera_id, homography=homography, lines=lines, zones=zones)

        total_events = 0
        total_track_points = 0
        with FrameSource(source, frame_skip=args.frame_skip) as frame_source:
            frame_count = 0
            for _ in range(args.num_frames):
                frame: Frame | None = frame_source.read()
                if frame is None:
                    print(f"source exhausted after {frame_count} frame(s)")
                    break

                detections = detector.detect(frame)
                tracks = tracker.update(detections)
                events = event_engine.update(tracks, timestamp=frame.timestamp)

                for track in tracks:
                    tracked_object = repository.get_or_create_object(
                        session, camera, track.object_id, track.class_name, track.timestamp
                    )
                    x, y = centroid(track.bbox)
                    repository.add_track_point(session, tracked_object, track.frame_id, track.timestamp, x, y)
                    total_track_points += 1

                for event in events:
                    repository.add_event_from_pipeline(session, camera, event)
                    total_events += 1

                if frame_count % args.commit_every == 0:
                    session.commit()

                frame_count += 1

        session.commit()
        print(f"persisted {total_track_points} track_point(s) and {total_events} event(s) across {frame_count} frame(s)")


if __name__ == "__main__":
    main()
