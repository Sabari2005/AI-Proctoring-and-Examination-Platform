"""
Code Execution Router - Stateless Edition
No authentication, no persistence, pure execution.
"""

import structlog
import os
import hmac
import asyncio
from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.schemas.schemas import RunRequest, RunResult
from app.services.sandbox import sandbox_executor

router = APIRouter()
log = structlog.get_logger()


def _verify_internal_secret(header_secret: str) -> bool:
    """Verify internal secret from mock_server (optional)."""
    expected = os.getenv("OBSERVE_INTERNAL_SECRET", "").strip()
    if not expected or len(expected) < 24:
        return False
    return hmac.compare_digest(header_secret, expected)


@router.post("/run", response_model=RunResult)
async def execute_code(
    request: Request,
    body: RunRequest,
):
    """
    Execute user code in sandboxed Docker container.
    
    No authentication required - this is a stateless backend-only service.
    Rate-limiting is handled by upstream (mock_server).
    
    Args:
        body: RunRequest with language, source_code, stdin
    
    Returns:
        RunResult: stdout, stderr, exit_code, execution_time_ms, memory_used_kb, etc.
    """
    
    # Validate language
    if body.language not in settings.SUPPORTED_LANGUAGES:
        log.warning(
            "unsupported_language",
            language=body.language,
            supported=settings.SUPPORTED_LANGUAGES,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {body.language}. "
                   f"Supported: {', '.join(settings.SUPPORTED_LANGUAGES)}"
        )

    # Validate code size (64 KB max)
    if len(body.source_code) > 65536:
        log.warning(
            "code_too_large",
            size_bytes=len(body.source_code),
            max_bytes=65536,
        )
        raise HTTPException(status_code=413, detail="Code too large (>64KB)")

    # Validate stdin size (1 MB max)
    if len(body.stdin) > 1048576:
        log.warning(
            "stdin_too_large",
            size_bytes=len(body.stdin),
            max_bytes=1048576,
        )
        raise HTTPException(status_code=413, detail="Input too large (>1MB)")

    client_ip = request.client.host if request.client else "unknown"
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        log.info(
            "code_execution_start",
            language=body.language,
            code_size=len(body.source_code),
            stdin_size=len(body.stdin),
            client_ip=client_ip,
            question_id=body.question_id,
            request_id=request_id,
        )

        # Execute code in Docker sandbox
        result = await sandbox_executor.run(
            language=body.language,
            source_code=body.source_code,
            stdin=body.stdin,
        )

        log.info(
            "code_execution_complete",
            language=body.language,
            exit_code=result.exit_code,
            execution_time_ms=result.execution_time_ms,
            memory_used_kb=result.memory_used_kb,
            timed_out=result.timed_out,
            request_id=request_id,
        )

        return result

    except asyncio.TimeoutError:
        log.error(
            "code_execution_timeout",
            language=body.language,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=504,
            detail="Execution timed out"
        )
    except Exception as exc:
        log.error(
            "code_execution_error",
            language=body.language,
            error=str(exc),
            request_id=request_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code execution failed: {str(exc)}"
        )


@router.post("/internal/run", response_model=RunResult)
async def execute_code_internal(
    request: Request,
    body: RunRequest,
):
    """
    Internal endpoint for mock_server with optional secret verification.
    Same execution logic, adds verification header.
    """
    # Optional: Verify internal secret if configured
    secret_header = request.headers.get("X-Observe-Secret", "").strip()
    if secret_header:
        if not _verify_internal_secret(secret_header):
            log.warning("invalid_internal_secret", client_ip=request.client.host if request.client else "unknown")
            raise HTTPException(status_code=403, detail="Invalid internal secret")

    # Same execution as public endpoint
    return await execute_code(request, body)

