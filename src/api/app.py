"""TRACE's FastAPI app: POST /videos, POST /videos/upload, GET /videos/{id}/status,
POST /cameras, GET /cameras/{camera_id}/events,
GET /objects/{id}/trajectory, GET /objects/{id}, GET /objects/{id}/events, GET /analytics,
POST /zones, POST /lines, POST /agent/query, POST /alerts, GET /cameras/{camera_id}/alerts,
POST /agent/actions/{id}/approve, GET /agent/actions/{id}, GET /evaluation.

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
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import agent, alerts, analytics, cameras, evaluation, lines, objects, videos, zones
from logging_config import configure_logging

configure_logging()

logger = logging.getLogger("trace.api")

app = FastAPI(title="TRACE API")

# Needed for real use, not speculative: the dashboard (Phase 10) is a
# separate origin (the Vite dev server at localhost:5173, or the built
# dashboard's own container/port in docker-compose) calling this API's
# fetch()/<video> requests from the browser -- without CORS, the browser
# blocks every cross-origin request outright. Explicit origins, not "*",
# since a wildcard would also have to disable credentials; there are none to
# disable yet, but naming real origins now is one line and avoids a silent
# security regression if credentials are ever added later.
# Externalized (TRACE_ALLOWED_ORIGINS, comma-separated) per Section 14 --
# the deployed dashboard's real origin belongs in the environment, not a
# code change, once this runs anywhere beyond local dev.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("TRACE_ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(cameras.router)
app.include_router(videos.router)
app.include_router(zones.router)
app.include_router(lines.router)
app.include_router(objects.router)
app.include_router(analytics.router)
app.include_router(agent.router)
app.include_router(alerts.router)
app.include_router(evaluation.router)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
