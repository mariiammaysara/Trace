"""The one real implementation of "run the pipeline over a video and persist
the results" -- FrameSource -> YoloDetector -> ByteTracker -> EventEngine ->
database. scripts/persist_video.py (the CLI/demo-bootstrap path) and
scripts/upload_worker.py (the upload poll loop) both call process_video()
here instead of each having their own copy of this loop.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from database import repository
from database.models import Camera
from detection.frame_source import Frame, FrameSource
from detection.yolo_detector import DEFAULT_CLASS_ALLOWLIST, DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_MODEL_PATH, YoloDetector
from events.engine import EventEngine
from geometry.homography import GroundPlaneHomography, load_camera_homography
from geometry.line_crossing import Line, load_camera_lines
from geometry.zone import Zone, load_camera_zones
from trajectories.trajectory import centroid
from tracking.byte_tracker import ByteTracker

logger = logging.getLogger("trace.pipeline")

# Unreachably high on purpose -- same convention docker-compose.yml's
# TRACE_SPEED_LIMIT/TRACE_MIN_DECELERATION_MAGNITUDE defaults already use for
# every camera here (Section 17: every homography is placeholder/
# illustrative, so OVERSPEED/SUDDEN_STOP numbers computed from it are
# physically meaningless). scripts/upload_worker.py hardcodes these for
# EVERY upload-processed video regardless of that env var, since an
# upload-created camera has no homography config at all -- worse than
# "placeholder", not just as-bad -- and letting a future .env change to the
# bootstrap camera's threshold accidentally also un-suppress uploads would
# be a real, silent correctness regression.
UPLOAD_SPEED_LIMIT = 1e9
UPLOAD_MIN_DECELERATION_MAGNITUDE = 1e9

# Same flat, illustrative 20px = 1m correspondences configs/cameras/demo.json
# itself uses for "no real survey exists" cameras -- reused here as the
# fallback for a camera with NO config file at all (every upload-created
# camera), not a new placeholder convention. speed_limit/min_deceleration_
# magnitude being suppressed (Step 3) is what actually keeps OVERSPEED/
# SUDDEN_STOP from firing on this fake scale; this homography exists only so
# EventEngine has *a* pixel->world mapping to construct with (its speed
# estimator needs one to run at all), not because the resulting numbers mean
# anything.
_IDENTITY_CORRESPONDENCES = [
    {"pixel": [0, 0], "world": [0, 0]},
    {"pixel": [100, 0], "world": [5, 0]},
    {"pixel": [100, 100], "world": [5, 5]},
    {"pixel": [0, 100], "world": [0, 5]},
]


def load_geometry_for_camera(
    camera_id: str, configs_dir: "str | Path" = "configs/cameras"
) -> Tuple[GroundPlaneHomography, List[Line], List[Zone]]:
    """Real config if configs/cameras/<camera_id>.json exists (unchanged
    behavior for every camera that has one); a synthetic identity-like
    homography and empty lines/zones for one that doesn't -- exactly the
    upload flow's situation, since an uploaded camera never has a config
    file. No LINE_CROSSED/ZONE_ENTERED/ZONE_EXITED can fire with zero lines/
    zones configured, which is correct: there's nothing real to say a line
    or zone was crossed against."""
    path = Path(configs_dir) / f"{camera_id}.json"
    if path.exists():
        return (
            load_camera_homography(camera_id, configs_dir),
            load_camera_lines(camera_id, configs_dir),
            load_camera_zones(camera_id, configs_dir),
        )
    return GroundPlaneHomography.from_correspondences(_IDENTITY_CORRESPONDENCES), [], []


def process_video(
    session: Session,
    camera: Camera,
    source: Union[str, int],
    *,
    configs_dir: "str | Path" = "configs/cameras",
    num_frames: Optional[int] = None,
    frame_skip: int = 1,
    confidence: float = DEFAULT_CONFIDENCE_THRESHOLD,
    class_allowlist: Optional[Tuple[str, ...]] = None,
    model: str = DEFAULT_MODEL_PATH,
    commit_every: int = 20,
    speed_limit: float = 5.0,
    min_deceleration_magnitude: float = 500.0,
    progress_callback: Optional[Callable[[int, Optional[float]], None]] = None,
    progress_every: int = 20,
) -> Tuple[int, int, int]:
    """Runs the real pipeline over `source` for `camera`, persisting every
    track point/event as it goes. Returns (frame_count, total_track_points,
    total_events). progress_callback(frames_processed, current_fps), if
    given, fires every `progress_every` frames -- current_fps is None until
    at least one call's worth of frames has actually elapsed (see
    scripts/upload_worker.py's caller for the "don't show an ETA yet"
    threshold), never a guess.
    """
    homography, lines, zones = load_geometry_for_camera(camera.camera_id, configs_dir)
    logger.info("loaded camera_id=%r: %d line(s), %d zone(s) -> persisted to database", camera.camera_id, len(lines), len(zones))
    for zone in zones:
        repository.get_or_create_zone(session, camera, zone.id, zone.polygon)
    for line in lines:
        repository.get_or_create_line(session, camera, line.id, line.start, line.end)
    session.commit()

    detector = YoloDetector(
        model_path=model,
        confidence_threshold=confidence,
        class_allowlist=class_allowlist or DEFAULT_CLASS_ALLOWLIST,
    )
    tracker = ByteTracker()
    event_engine = EventEngine(
        camera_id=camera.camera_id,
        homography=homography,
        lines=lines,
        zones=zones,
        speed_limit=speed_limit,
        min_deceleration_magnitude=min_deceleration_magnitude,
    )

    total_events = 0
    total_track_points = 0
    frame_count = 0
    started_at = time.monotonic()

    with FrameSource(source, frame_skip=frame_skip) as frame_source:
        while num_frames is None or frame_count < num_frames:
            frame: Optional[Frame] = frame_source.read()
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
                repository.add_track_point(session, tracked_object, track.frame_id, track.timestamp, x, y, bbox=track.bbox)
                total_track_points += 1

            for event in events:
                repository.add_event_from_pipeline(session, camera, event)
                total_events += 1

            frame_count += 1

            if frame_count % commit_every == 0:
                session.commit()

            if progress_callback is not None and frame_count % progress_every == 0:
                elapsed = time.monotonic() - started_at
                current_fps = frame_count / elapsed if elapsed > 0 else None
                progress_callback(frame_count, current_fps)

    session.commit()

    if progress_callback is not None:
        elapsed = time.monotonic() - started_at
        current_fps = frame_count / elapsed if elapsed > 0 else None
        progress_callback(frame_count, current_fps)

    logger.info("persisted %d track_point(s) and %d event(s) across %d frame(s)", total_track_points, total_events, frame_count)
    return frame_count, total_track_points, total_events
