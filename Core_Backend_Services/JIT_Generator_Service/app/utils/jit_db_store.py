"""Persist JIT completion artifacts directly to the main Neon database."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _load_env_candidates() -> None:
    """Load .env from common run locations for standalone JIT service."""
    module_path = Path(__file__).resolve()
    repo_root = module_path.parents[4]

    candidates = [
        Path.cwd() / ".env",
        module_path.parents[2] / ".env",  # Backend/new_jit/.env
        repo_root / ".env",               # workspace root .env
        repo_root / "APPLICATION" / "server" / ".env",
    ]

    for env_path in candidates:
        if env_path.exists():
            load_dotenv(env_path, override=False)


_load_env_candidates()

_ENGINE = None
_ENGINE_LOCK = threading.Lock()


def _normalize_database_url(raw_url: str) -> str:
    url = str(raw_url or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def _get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE

        db_url = _normalize_database_url(os.getenv("DATABASE_URL", ""))
        if not db_url:
            raise RuntimeError("DATABASE_URL is not configured for JIT DB persistence")

        _ENGINE = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
            connect_args={"connect_timeout": 10},
        )
        return _ENGINE


def persist_final_report(session_id: str, final_report: dict | None) -> bool:
    """Write final_report to jit_section_sessions by jit_session_id.

    Returns True when at least one row was updated.
    """
    if not session_id or not isinstance(final_report, dict):
        return False

    try:
        engine = _get_engine()
    except Exception as exc:
        print(f"[JIT_DB] WARNING: Skipping DB persistence (engine init failed): {exc}")
        return False

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE jit_section_sessions
                    SET
                        final_report = CAST(:final_report AS JSON),
                        status = 'completed',
                        updated_at = now()
                    WHERE jit_session_id = :session_id
                    """
                ),
                {
                    "session_id": str(session_id),
                    "final_report": json.dumps(final_report, ensure_ascii=False),
                },
            )
            updated_rows = int(result.rowcount or 0)
            if updated_rows <= 0:
                print(
                    f"[JIT_DB] WARNING: No jit_section_sessions row found for jit_session_id={session_id}"
                )
                return False

        print(
            f"[JIT_DB] Persisted final_report for jit_session_id={session_id} rows={updated_rows}"
        )
        return True
    except Exception as exc:
        print(f"[JIT_DB] ERROR: Failed persisting final_report for {session_id}: {exc}")
        return False


def persist_session_start(
    session_id: str,
    candidate_id: str | None,
    section_topic: str | None,
) -> bool:
    """Bind jit_session_id to a pending/active jit_section_sessions row at start.

    This is best-effort. It only runs when candidate_id can be parsed as an int,
    because exam_attempts.candidate_id is an integer FK in the main schema.
    """
    if not session_id:
        return False

    candidate_text = str(candidate_id or "").strip()
    section_title = str(section_topic or "").strip()
    if not candidate_text.isdigit() or not section_title:
        return False

    try:
        engine = _get_engine()
    except Exception as exc:
        print(f"[JIT_DB] WARNING: Skipping session-start DB bind (engine init failed): {exc}")
        return False

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE jit_section_sessions jss
                    SET
                        jit_session_id = :session_id,
                        status = 'active',
                        updated_at = now()
                    WHERE jss.jit_section_session_id = (
                        SELECT x.jit_section_session_id
                        FROM jit_section_sessions x
                        JOIN exam_attempts ea ON ea.attempt_id = x.attempt_id
                        WHERE ea.candidate_id = :candidate_id
                          AND LOWER(TRIM(x.section_title)) = LOWER(TRIM(:section_title))
                          AND (x.jit_session_id IS NULL OR TRIM(x.jit_session_id) = '')
                          AND x.status IN ('pending', 'active')
                        ORDER BY x.updated_at DESC NULLS LAST, x.created_at DESC NULLS LAST
                        LIMIT 1
                    )
                    """
                ),
                {
                    "session_id": str(session_id),
                    "candidate_id": int(candidate_text),
                    "section_title": section_title,
                },
            )
            updated_rows = int(result.rowcount or 0)
            if updated_rows <= 0:
                print(
                    "[JIT_DB] WARNING: Session-start bind found no jit_section_sessions row "
                    f"for candidate_id={candidate_text} section_title={section_title!r}"
                )
                return False

        print(
            f"[JIT_DB] Bound session start jit_session_id={session_id} rows={updated_rows}"
        )
        return True
    except Exception as exc:
        print(f"[JIT_DB] ERROR: Failed persisting start state for {session_id}: {exc}")
        return False
