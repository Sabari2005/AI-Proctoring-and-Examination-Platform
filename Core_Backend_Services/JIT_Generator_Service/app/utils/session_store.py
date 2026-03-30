"""
JIT/app/utils/session_store.py
───────────────────────────────
In-memory session store for JIT sessions.
In production, replace with Redis or DB-backed store.
"""
import uuid
from typing import Optional
from app.core.schemas import JITSessionState


_store: dict[str, JITSessionState] = {}


def create_session(state: JITSessionState) -> str:
    _store[state.session_id] = state
    return state.session_id


def get_session(session_id: str) -> Optional[JITSessionState]:
    return _store.get(session_id)


def update_session(state: JITSessionState) -> None:
    _store[state.session_id] = state


def delete_session(session_id: str) -> None:
    _store.pop(session_id, None)


def new_session_id() -> str:
    return f"jit-{uuid.uuid4().hex[:10]}"


def new_question_id(session_id: str, q_num: int) -> str:
    return f"{session_id}-q{q_num:02d}"