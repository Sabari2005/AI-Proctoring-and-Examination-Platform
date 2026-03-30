"""
Database engine and session helpers for the mock proctoring server.

Reads DATABASE_URL from environment configuration.
If the URL does not specify sslmode, sslmode=require is appended so managed
PostgreSQL providers that require TLS connect reliably by default.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def _build_url() -> str:
    """Build a normalized SQLAlchemy connection URL from DATABASE_URL."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set.  "
            "Add it to the server environment before starting the mock server."
        )
    # Normalize postgres:// alias for SQLAlchemy 2.x.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # Ensure TLS mode is enabled when not explicitly configured.
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


_engine = None
_SessionLocal = None


def get_engine():
    """Return singleton SQLAlchemy engine configured for application usage."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            _build_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10},
        )
    return _engine


def get_session_factory():
    """Return singleton SQLAlchemy sessionmaker bound to the shared engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db():
    """Yield a scoped DB session; always closed on exit."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Return True if the DB connection is healthy."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"[DB] Connection check failed: {exc}")
        return False
