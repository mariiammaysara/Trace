"""Run the full TRACE pipeline end-to-end on a video file or camera and
persist everything to Postgres, instead of just printing events:

    FrameSource -> Detector -> Tracker -> Trajectory -> Geometry -> Event Engine -> database

Requires Postgres reachable (see docker-compose.yml; `docker compose up -d db`,
reachable at localhost:5433 from the host by default). This is also the
`worker` service in docker-compose.yml -- there, every argument below comes
from an environment variable instead of a flag (Section 14: configuration is
externalized, not hardcoded), so `python scripts/persist_video.py` with zero
arguments is a real, valid way to run it -- every default below is exactly
what the worker container runs with.

Usage:
    python scripts/persist_video.py path/to/video.mp4 --camera-id demo
    python scripts/persist_video.py 0 --camera-id demo --database-url postgresql://trace:trace@localhost:5433/trace
    TRACE_CAMERA_SOURCE=data/sample.mp4 TRACE_CAMERA_ID=demo python scripts/persist_video.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database import repository
from database.db import create_all, get_engine, get_session_factory
from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_MODEL_PATH, YoloDetector
from events.engine import EventEngine
from geometry.homography import load_camera_homography
from geometry.line_crossing import load_camera_lines
from geometry.zone import load_camera_zones
from logging_config import configure_logging
from trajectories.trajectory import centroid
from tracking.byte_tracker import ByteTracker

logger = logging.getLogger("trace.worker")

# The same demo asset every phase's manual testing has used (Sections 2/3/8/9/10/13/15) --
# a real, working, zero-setup default so the worker container runs out of the box.
DEFAULT_SOURCE = "data/sample.mp4"


def _parse_source(raw: str) -> "str | int":
    """A source that looks like a bare integer is a camera index; anything else is a file path."""
    try:
        return int(raw)
    except ValueError:
        return raw


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "source",
        nargs="?",
        default=os.environ.get("TRACE_CAMERA_SOURCE", DEFAULT_SOURCE),
        help="video file path or camera index (e.g. 0); env: TRACE_CAMERA_SOURCE (default: %(default)s)",
    )
    parser.add_argument(
        "--camera-id",
        default=os.environ.get("TRACE_CAMERA_ID", "demo"),
        help="which configs/cameras/<id>.json to load; env: TRACE_CAMERA_ID (default: %(default)s)",
    )
    parser.add_argument("--configs-dir", default="configs/cameras", help="directory holding per-camera configs (default: %(default)s)")
    parser.add_argument("--database-url", default=None, help="defaults to DATABASE_URL env var, then database.db.DEFAULT_DATABASE_URL")
    _num_frames_env = os.environ.get("TRACE_NUM_FRAMES", "").strip()
    parser.add_argument(
        "--num-frames",
        type=int,
        default=int(_num_frames_env) if _num_frames_env else None,
        help="frames to process; env: TRACE_NUM_FRAMES (default: process until the source is exhausted)",
    )
    parser.add_argument("--frame-skip", type=int, default=1, help="process every Nth frame (default: 1)")
    parser.add_argument(
        "--confidence",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help="detection confidence threshold; env: TRACE_DETECTOR_CONFIDENCE (default: %(default)s)",
    )
    parser.add_argument("--classes", default=None, help="comma-separated class allowlist (default: %(default)s)")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_PATH,
        help="Ultralytics weights path/name; env: TRACE_DETECTOR_WEIGHTS (default: %(default)s)",
    )
    parser.add_argument("--commit-every", type=int, default=20, help="commit to the database every N frames (default: 20)")
    parser.add_argument(
        "--speed-limit",
        type=float,
        default=float(os.environ.get("TRACE_SPEED_LIMIT", "5.0")),
        help="OVERSPEED threshold, world units/s; env: TRACE_SPEED_LIMIT (default: %(default)s, matches "
        "EventEngine's own default). Set unreachably high (e.g. 1e9) for a camera with only a "
        "placeholder/illustrative homography, so OVERSPEED never fires against an uncalibrated world scale "
        "-- every camera currently shipped here (demo, demo-trafficlight) is exactly that case; see "
        "TRACE_STUDY_GUIDE.md's SUDDEN_STOP/OVERSPEED suppression note.",
    )
    parser.add_argument(
        "--min-deceleration-magnitude",
        type=float,
        default=float(os.environ.get("TRACE_MIN_DECELERATION_MAGNITUDE", "500.0")),
        help="SUDDEN_STOP threshold, world units/s^2; env: TRACE_MIN_DECELERATION_MAGNITUDE (default: "
        "%(default)s, matches EventEngine's own default). Same reasoning as --speed-limit: "
        "SUDDEN_STOP's deceleration_magnitude is computed via the homography's world scale, so set this "
        "unreachably high for a camera with only a placeholder homography, or SUDDEN_STOP fires on the "
        "fake world-space speed swings, not real events.",
    )
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

        source = _parse_source(args.source)
        video = None
        if isinstance(source, str):
            # a live camera index has no file to register/replay -- only file
            # sources get a Video row (Section 9: "one row per ingested video
            # file"), which is also what GET /videos/{id}/stream serves.
            video = repository.create_video(session, camera, source)
        session.commit()
        logger.info("loaded camera_id=%r: %d line(s), %d zone(s) -> persisted to database", args.camera_id, len(lines), len(zones))
        if video is not None:
            logger.info("registered video id=%s path=%r -- GET /videos/%s/stream serves it", video.id, source, video.id)
        logger.info(
            "starting pipeline: source=%r model=%r confidence=%.2f num_frames=%s",
            source, args.model, args.confidence, args.num_frames if args.num_frames is not None else "unbounded (until source exhausted)",
        )
        detector = YoloDetector(
            model_path=args.model,
            confidence_threshold=args.confidence,
            class_allowlist=class_allowlist,
        )
        tracker = ByteTracker()
        event_engine = EventEngine(
            camera_id=args.camera_id,
            homography=homography,
            lines=lines,
            zones=zones,
            speed_limit=args.speed_limit,
            min_deceleration_magnitude=args.min_deceleration_magnitude,
        )

        total_events = 0
        total_track_points = 0
        with FrameSource(source, frame_skip=args.frame_skip) as frame_source:
            frame_count = 0
            while args.num_frames is None or frame_count < args.num_frames:
                frame: Frame | None = frame_source.read()
                if frame is None:
                    logger.info("source exhausted after %d frame(s)", frame_count)
                    break

                detections = detector.detect(frame)
                tracks = tracker.update(detections)
                events = event_engine.update(tracks, timestamp=frame.timestamp)

                for track in tracks:
                    tracked_object = repository.get_or_create_object(
                        session, camera, track.object_id, track.class_name, track.timestamp
                    )
                    x, y = centroid(track.bbox)
                    repository.add_track_point(
                        session, tracked_object, track.frame_id, track.timestamp, x, y, bbox=track.bbox
                    )
                    total_track_points += 1

                for event in events:
                    repository.add_event_from_pipeline(session, camera, event)
                    total_events += 1

                if frame_count % args.commit_every == 0:
                    session.commit()

                frame_count += 1

        session.commit()
        logger.info("persisted %d track_point(s) and %d event(s) across %d frame(s)", total_track_points, total_events, frame_count)


if __name__ == "__main__":
    main()
