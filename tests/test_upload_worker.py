"""Tests for scripts/upload_worker.py's poll-and-process loop.

scripts/ isn't part of the installed `trace` package (src/ is, via
pyproject.toml's package-dir), so it's imported here the same way the
script imports its own src/ dependencies: sys.path.insert, not a real
package import.

pipeline.process_video is monkeypatched to a fake in every test here --
this suite is about upload_worker's own claim/dispatch/status-transition
logic (Step 1's design), not about re-testing the real detector/tracker/
event-engine pipeline, which already has its own dedicated test files
(test_event_engine.py, test_tracker.py, etc.).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import upload_worker  # noqa: E402

import pipeline  # noqa: E402
from database import repository  # noqa: E402


def test_process_one_uses_suppressed_thresholds_regardless_of_env(db_session, monkeypatch):
    """Step 3's requirement: an upload-created camera has no homography
    config at all, so OVERSPEED/SUDDEN_STOP must be suppressed no matter
    what TRACE_SPEED_LIMIT/TRACE_MIN_DECELERATION_MAGNITUDE happen to be set
    to for the *other*, bootstrap worker."""
    monkeypatch.setenv("TRACE_SPEED_LIMIT", "5.0")
    monkeypatch.setenv("TRACE_MIN_DECELERATION_MAGNITUDE", "500.0")

    camera = repository.get_or_create_camera(db_session, "cam_upload_worker_thresholds")
    repository.create_pending_video(db_session, camera, "/data/uploads/does-not-matter.mp4", total_frames=10)
    db_session.flush()
    video = repository.claim_next_pending_video(db_session)

    captured = {}

    def fake_process_video(session, cam, source, **kwargs):
        captured.update(kwargs)
        return (10, 3, 1)

    monkeypatch.setattr(upload_worker, "process_video", fake_process_video)

    upload_worker._process_one(db_session, video)

    assert captured["speed_limit"] == pipeline.UPLOAD_SPEED_LIMIT
    assert captured["min_deceleration_magnitude"] == pipeline.UPLOAD_MIN_DECELERATION_MAGNITUDE
    assert captured["speed_limit"] != 5.0
    assert captured["min_deceleration_magnitude"] != 500.0


def test_process_one_marks_video_done_and_records_progress(db_session, monkeypatch):
    camera = repository.get_or_create_camera(db_session, "cam_upload_worker_done")
    repository.create_pending_video(db_session, camera, "/data/uploads/ok.mp4", total_frames=10)
    db_session.flush()
    video = repository.claim_next_pending_video(db_session)

    def fake_process_video(session, cam, source, *, progress_callback=None, **kwargs):
        progress_callback(10, 12.5)
        return (10, 3, 1)

    monkeypatch.setattr(upload_worker, "process_video", fake_process_video)

    upload_worker._process_one(db_session, video)

    assert video.status == "done"
    assert video.frames_processed == 10
    assert video.current_fps == 12.5


def test_process_one_marks_video_failed_on_pipeline_exception(db_session, monkeypatch):
    camera = repository.get_or_create_camera(db_session, "cam_upload_worker_failed")
    repository.create_pending_video(db_session, camera, "/data/uploads/bad.mp4", total_frames=10)
    db_session.flush()
    video = repository.claim_next_pending_video(db_session)

    def fake_process_video(session, cam, source, **kwargs):
        raise IOError("could not open frame source: '/data/uploads/bad.mp4'")

    monkeypatch.setattr(upload_worker, "process_video", fake_process_video)

    upload_worker._process_one(db_session, video)

    assert video.status == "failed"
    assert "could not open frame source" in video.error_message
