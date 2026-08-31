"""TRACE's FastAPI app: POST /videos, POST /cameras, GET /cameras/{camera_id}/events,
GET /objects/{id}/trajectory, GET /analytics, POST /zones, POST /lines.

POST /agent/query and POST /alerts are `[PLANNED]` -- Phases 11-12, not this
phase (Section 10's table lists them, but they depend on the not-yet-built
Vision Agent and alert-rule system).

Error handling:
- 422 for a malformed request body -- Pydantic validation, automatic, before
  any route handler runs.
- 404 for a missing camera/object -- raised explicitly in the route/common
  helpers (api.common.get_camera_or_404, and inline in objects.py) once a
  repository lookup returns None.
- 500 for anything unexpected -- caught here, logged server-side, and turned
  into a clean {"detail": "internal server error"} body. Never the raw
  exception/stack trace: this handler is what guarantees that, rather than
  relying on Starlette's default behavior.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routers import analytics, cameras, lines, objects, videos, zones

logger = logging.getLogger("trace.api")

app = FastAPI(title="TRACE API")

app.include_router(cameras.router)
app.include_router(videos.router)
app.include_router(zones.router)
app.include_router(lines.router)
app.include_router(objects.router)
app.include_router(analytics.router)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
