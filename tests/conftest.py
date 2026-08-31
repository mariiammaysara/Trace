"""Shared pytest fixtures for TRACE tests."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://trace:trace@localhost:5433/trace_test")

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_VIDEO_PATH = FIXTURES_DIR / "sample_video.mp4"
SAMPLE_VIDEO_FRAME_COUNT = 15
SAMPLE_VIDEO_FPS = 10
SAMPLE_VIDEO_WIDTH = 64
SAMPLE_VIDEO_HEIGHT = 64


def _generate_sample_video(path: Path) -> None:
    """Write a small synthetic test video: solid-color frames, first frame pure blue (BGR order)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        SAMPLE_VIDEO_FPS,
        (SAMPLE_VIDEO_WIDTH, SAMPLE_VIDEO_HEIGHT),
    )
    try:
        for i in range(SAMPLE_VIDEO_FRAME_COUNT):
            frame_bgr = np.zeros((SAMPLE_VIDEO_HEIGHT, SAMPLE_VIDEO_WIDTH, 3), dtype=np.uint8)
            if i == 0:
                frame_bgr[:, :] = (255, 0, 0)  # pure blue, written in BGR channel order
            else:
                frame_bgr[:, :] = (0, 0, min(255, 20 + i * 15))  # increasingly red, BGR order
            writer.write(frame_bgr)
    finally:
        writer.release()


@pytest.fixture(scope="session")
def sample_video_path() -> Path:
    """Path to a small synthetic test video, generated once under tests/fixtures/ if missing."""
    if not SAMPLE_VIDEO_PATH.exists():
        _generate_sample_video(SAMPLE_VIDEO_PATH)
    return SAMPLE_VIDEO_PATH


@pytest.fixture
def sample_video_frame_count() -> int:
    return SAMPLE_VIDEO_FRAME_COUNT


@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped engine against a dedicated trace_test Postgres database
    (docker-compose's db service, mapped to host port 5433 -- see
    docker-compose.yml). Skips every test using it if that database isn't
    reachable, rather than failing hard, since it depends on Docker being up."""
    from database.db import create_all, get_engine

    engine = get_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(f"trace_test database not reachable at {TEST_DATABASE_URL!r} (is `docker compose up -d db` running?): {exc}")
    create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """One isolated session per test: everything happens inside an outer
    transaction that's rolled back at teardown, even if application code
    calls session.commit() -- the standard SQLAlchemy 2.0 "join a session to
    an external transaction" pattern (a SAVEPOINT is restarted after every
    inner commit) so no test's data leaks into the next."""
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False, future=True)()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()
