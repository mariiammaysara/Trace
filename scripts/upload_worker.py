"""Persistent poll loop for videos uploaded via POST /videos/upload.

Step 1's chosen design (see the upload feature's PR description for the
full tradeoff writeup): the API only ever validates an upload, saves it to
disk, and inserts a "pending" Video row -- it never runs the CPU-bound
pipeline itself, since that would block the request-serving process for
minutes. This script is the other half: a long-running consumer, one
process, claiming and running one pending video at a time via
database.repository.claim_next_pending_video()'s SELECT ... FOR UPDATE SKIP
LOCKED (real mutual exclusion, not just "there's only one worker by
convention").

This is a SEPARATE docker-compose service from `worker` (scripts/
persist_video.py) on purpose: `worker` is a one-shot demo-seeding job that
processes exactly one fixed, env-configured camera/source and exits;
this script never exits and knows nothing about any specific camera --
it just drains whatever POST /videos/upload put in the queue.

Every video this claims is processed with OVERSPEED/SUDDEN_STOP thresholds
hardcoded to pipeline.UPLOAD_SPEED_LIMIT/UPLOAD_MIN_DECELERATION_MAGNITUDE
(unreachably high) regardless of TRACE_SPEED_LIMIT/TRACE_MIN_DECELERATION_
MAGNITUDE -- every upload-created camera has no homography config at all
(worse than the shipped cameras' placeholder ones), so those numbers would
be physically meaningless if they were ever allowed to fire. See Section 17
and pipeline.py's module comment for the full reasoning; letting a real
camera later provide real calibration is explicitly out of scope here.

Usage:
    python scripts/upload_worker.py
    TRACE_UPLOAD_POLL_INTERVAL_SECONDS=1 python scripts/upload_worker.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database import repository
from database.db import create_all, get_engine, get_session_factory
from logging_config import configure_logging
from pipeline import UPLOAD_MIN_DECELERATION_MAGNITUDE, UPLOAD_SPEED_LIMIT, process_video

logger = logging.getLogger("trace.upload_worker")

DEFAULT_POLL_INTERVAL_SECONDS = 2.0


def _process_one(session, video) -> None:
    camera = video.camera
    logger.info(
        "claimed video id=%s camera_id=%r path=%r total_frames=%s -- starting pipeline",
        video.id, camera.camera_id, video.path, video.total_frames,
    )

    def on_progress(frames_processed: int, current_fps: "float | None") -> None:
        repository.update_video_progress(session, video, frames_processed, current_fps)

    try:
        frame_count, total_track_points, total_events = process_video(
            session,
            camera,
            video.path,
            speed_limit=UPLOAD_SPEED_LIMIT,
            min_deceleration_magnitude=UPLOAD_MIN_DECELERATION_MAGNITUDE,
            progress_callback=on_progress,
        )
    except Exception as exc:  # noqa: BLE001 -- any pipeline failure marks this video failed, never silently drops it
        logger.exception("video id=%s failed during processing", video.id)
        session.rollback()
        repository.mark_video_failed(session, video, str(exc))
        return

    repository.mark_video_done(session, video)
    logger.info(
        "video id=%s done: %d frame(s), %d track_point(s), %d event(s)",
        video.id, frame_count, total_track_points, total_events,
    )


def main() -> None:
    configure_logging()

    poll_interval = float(os.environ.get("TRACE_UPLOAD_POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS)))

    engine = get_engine()
    create_all(engine)
    Session = get_session_factory(engine)

    logger.info("upload worker started -- polling for pending videos every %.1fs", poll_interval)

    while True:
        with Session() as session:
            video = repository.claim_next_pending_video(session)
            if video is None:
                time.sleep(poll_interval)
                continue
            _process_one(session, video)


if __name__ == "__main__":
    main()
