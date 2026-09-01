"""FastAPI dependency injection: one DB session per request, closed after.

A real request gets a fresh session from database.db's engine/session
factory; tests override get_db (via app.dependency_overrides) to hand back a
session bound to a rolled-back transaction instead, so API tests never leave
data behind -- same isolation pattern Phase 8's db_session fixture already
uses.
"""

from __future__ import annotations

from typing import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from agent import LLMNotConfiguredError, VisionAgent, build_default_llm_client
from database.db import get_engine, get_session_factory

_engine = get_engine()
_session_factory = get_session_factory(_engine)


def get_db() -> Iterator[Session]:
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def get_agent() -> VisionAgent:
    """A fresh VisionAgent per request -- cheap (build_default_llm_client()
    only reads an env var, no network call happens until a question is
    actually asked). Turns the "no API key configured" case into a clear 503
    here rather than letting it fall through to the generic 500 handler,
    which would hide *why* it failed behind a deliberately opaque message."""
    try:
        return VisionAgent(build_default_llm_client())
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
