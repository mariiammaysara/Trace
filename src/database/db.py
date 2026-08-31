"""Database engine/session setup.

DATABASE_URL defaults to the docker-compose `db` service's connection string
as reachable from the host (docker-compose.yml maps the container's 5432 to
host port 5433) -- override via the DATABASE_URL environment variable for
anything else (a different port, a test database, running inside the `app`
container where the service is reachable as `db:5432` directly).
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

DEFAULT_DATABASE_URL = "postgresql://trace:trace@localhost:5433/trace"


def get_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_engine(url, future=True)


def create_all(engine: Engine) -> None:
    """Create every table in models.py if it doesn't already exist. This is
    schema setup for development/tests, not a migration tool -- a real
    migration tool (e.g. Alembic) would be the next step for evolving an
    already-deployed schema, and is out of scope here."""
    Base.metadata.create_all(engine)


def get_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
