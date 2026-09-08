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

CORS-on-500 note (real bug, fixed here -- see UnhandledExceptionMiddleware
below): a handler registered the "normal" FastAPI way, via
`@app.exception_handler(Exception)`, gets special-cased by Starlette into
`ServerErrorMiddleware` -- which Starlette always places as the OUTERMOST
layer of the whole middleware stack, outside every middleware added via
`app.add_middleware(...)` (CORSMiddleware included), regardless of what
order those are added in. That means a response coming from an
`@app.exception_handler(Exception)` handler never passes back through
CORSMiddleware, so it never gets `Access-Control-Allow-Origin` -- and a
browser calling this API cross-origin then reports a generic
`TypeError: Failed to fetch` for the 500, hiding the real status/detail
entirely (confirmed with curl: a 200 and a normal 404 both carry
`access-control-allow-origin`, this bare-`Exception` handler's 500 didn't).
The fix is to stop using `@app.exception_handler(Exception)` for this and
use real ASGI middleware instead, added via `add_middleware` BEFORE
CORSMiddleware -- since `add_middleware` prepends, that makes CORSMiddleware
the outer of the two, so it wraps this middleware and sees (and adds headers
to) whatever response it returns, unhandled-exception 500s included.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.routers import agent, alerts, analytics, cameras, evaluation, lines, objects, videos, zones
from logging_config import configure_logging

configure_logging()

logger = logging.getLogger("trace.api")

app = FastAPI(title="TRACE API")


class UnhandledExceptionMiddleware(BaseHTTPMiddleware):
    """Replaces `@app.exception_handler(Exception)` -- see the module
    docstring's CORS-on-500 note for exactly why that approach silently
    drops CORS headers and this one doesn't. Only ever sees exceptions that
    escape normal FastAPI/Starlette handling (HTTPException, validation
    errors, etc. are already turned into responses by ExceptionMiddleware,
    further inside this stack, before they'd ever reach here) -- so this
    catches exactly the same "anything unexpected" cases the old handler did,
    nothing more.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("unhandled error on %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "internal server error"})


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

# Order matters (see UnhandledExceptionMiddleware's docstring and the
# CORS-on-500 module note): add_middleware prepends, so whichever is added
# LAST ends up OUTERMOST. UnhandledExceptionMiddleware must be added first
# so CORSMiddleware (added second, now outermost) wraps it and can add
# Access-Control-Allow-Origin to every response it returns, 500s included.
app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # DELETE added for DELETE /cameras/{camera_id} (camera delete feature) --
    # missing methods here fail the browser's own CORS preflight before the
    # actual request is ever sent, a different-looking but same-root-cause
    # failure as the CORS-on-500 bug above (confirmed via a manual OPTIONS
    # preflight: this previously came back "Disallowed CORS method").
    allow_methods=["GET", "POST", "DELETE"],
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
