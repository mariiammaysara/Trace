"""One place to turn on real, leveled, timestamped logging -- used by both
the API (src/api/app.py) and the pipeline worker (scripts/persist_video.py).

Without this, `logging.getLogger(...)` calls scattered across the codebase
(e.g. api.app's `logger.exception(...)` in the global error handler) never
actually configure a handler on their own -- Python's logging module falls
back to its bare "last resort" handler (WARNING+ only, no timestamp, no
logger name), which is enough to not lose an error silently but not enough
to actually debug anything in a running container. `configure_logging()`
installs a real handler with a real format, once, at process startup.

Level is externalized via TRACE_LOG_LEVEL (default INFO) -- per Section 14,
observability configuration belongs in the environment, not hardcoded.
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent: safe to call from multiple entrypoints (app import,
    __main__ guards, tests) without installing duplicate handlers."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.environ.get("TRACE_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    _CONFIGURED = True
