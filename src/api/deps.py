"""FastAPI dependency injection: one DB session per request, closed after.

A real request gets a fresh session from database.db's engine/session
factory; tests override get_db (via app.dependency_overrides) to hand back a
session bound to a rolled-back transaction instead, so API tests never leave
data behind -- same isolation pattern Phase 8's db_session fixture already
uses.
"""

from __future__ import annotations

from typing import Iterator

from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory

_engine = get_engine()
_session_factory = get_session_factory(_engine)


def get_db() -> Iterator[Session]:
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
