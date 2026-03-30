"""
logger.py — Structured, server-side audit logging for all events.

Every significant event (login, submission, run, proctor event) is:
  1. Logged to stdout as structured JSON (picked up by container log driver)
  2. Written to audit_logs PostgreSQL table
  3. (Optional) Uploaded to S3 for long-term retention
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import structlog


def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if _is_dev() else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def _is_dev() -> bool:
    import os
    return os.getenv("ENVIRONMENT", "development") == "development"


class AuditLogger:
    """High-level audit logger — writes to DB + structured logs."""

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        log = structlog.get_logger()
        log.info(
            "audit_event",
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            payload=payload,
            client_ip=client_ip,
            request_id=request_id,
        )

        # Async DB write (best-effort — don't fail the request if this fails)
        try:
            await self._write_to_db(event_type, user_id, session_id, payload, client_ip, request_id)
        except Exception as e:
            log.error("audit_db_write_failed", error=str(e))

    async def _write_to_db(self, event_type, user_id, session_id, payload, client_ip, request_id):
        from app.services.db import get_async_session
        from app.models.models import AuditLog

        async with get_async_session() as session:
            record = AuditLog(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                payload=payload,
                client_ip=client_ip,
                request_id=request_id,
            )
            session.add(record)
            await session.commit()


audit_logger = AuditLogger()
