"""
Proctored Code Execution Service - Stateless Edition
No database, no persistence, no user management.
Only code execution via Docker sandbox.
"""

import structlog
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import execution
from app.services.logger import setup_logging

setup_logging()
log = structlog.get_logger()


def _parse_env_list(raw: str) -> list[str]:
    if not raw:
        return []
    value = raw.strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
    return [item.strip() for item in value.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle - no database initialization."""
    log.info(
        "startup",
        service="proctored-code-env",
        version="2.0-stateless",
        environment=settings.ENVIRONMENT,
    )
    yield
    log.info("shutdown")


app = FastAPI(
    title="Proctored Code Execution Platform",
    description="Stateless code execution backend - execution only, no persistence",
    version="2.0-stateless",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_env_list(settings.ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-Session-Token", "X-Observe-Secret"],
)

if settings.ENVIRONMENT == "production":
    allowed_hosts = set(_parse_env_list(settings.ALLOWED_HOSTS))
    if not allowed_hosts:
        allowed_hosts = {"*"}
    allowed_hosts.update({"localhost", "127.0.0.1", "testserver"})
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(allowed_hosts))


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    import time
    import uuid
    req_id = str(uuid.uuid4())
    request.state.request_id = req_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
        request_id=req_id,
        client_ip=request.client.host if request.client else None,
    )
    response.headers["X-Request-ID"] = req_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(execution.router, prefix="/api/v1/execute", tags=["Execution"])


# ── Deprecated Endpoints (return 410 Gone) ──────────────────────────────────


@app.post("/api/v1/auth/login")
async def deprecated_auth():
    """Auth endpoint removed - this is a stateless executor."""
    raise HTTPException(
        status_code=410,
        detail="Auth endpoint removed. This service is stateless (execution only).",
    )


@app.post("/api/v1/submissions")
async def deprecated_submissions():
    """Submissions endpoint removed - all persistence handled by mock_server."""
    raise HTTPException(
        status_code=410,
        detail="Submissions endpoint removed. Persist results via mock_server.",
    )


@app.post("/api/v1/questions")
async def deprecated_questions():
    """Questions endpoint removed - questions served by mock_server."""
    raise HTTPException(
        status_code=410,
        detail="Questions endpoint removed. Use mock_server for question data.",
    )


# ── Health Endpoint ────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health check - no database check."""
    return {
        "status": "ok",
        "service": "proctored-code-env",
        "version": "2.0-stateless",
        "uptime": "stateless (no db)",
    }

