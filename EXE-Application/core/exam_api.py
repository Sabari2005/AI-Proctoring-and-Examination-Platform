"""HTTP client for exam lifecycle operations.

This module provides a thin, signed API client used by the desktop app for
bootstrap, answer persistence, coding execution/submission, log upload, and
final exam submission.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import socket
import threading
import time
import uuid
from typing import Any, Optional

import requests


def _machine_fingerprint() -> str:
    """Return a stable host fingerprint hash derived from local machine traits."""
    parts = [
        platform.system(),
        platform.release(),
        platform.machine(),
        str(uuid.getnode()),
        socket.gethostname(),
    ]
    payload = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


def _shared_secret() -> bytes:
    """Load and validate the HMAC secret used for request signing."""
    secret = (os.environ.get("VIRTUSA_PROCTOR_SECRET") or "").strip()
    if not secret or secret == "dev-shared-secret-change-me" or len(secret) < 24:
        raise RuntimeError(
            "Invalid VIRTUSA_PROCTOR_SECRET. Configure a strong production secret (min 24 chars)."
        )
    return secret.encode("utf-8")


def _stable_json(data: dict) -> bytes:
    """Serialize payload to deterministic JSON bytes for signing/transmission."""
    return json.dumps(data, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")


def _signature(payload: dict) -> str:
    """Compute request signature for a payload using HMAC-SHA256."""
    return hmac.new(_shared_secret(), _stable_json(payload), hashlib.sha256).hexdigest()


def _coerce_question_id(raw: Any) -> Any:
    """Normalize a question identifier to int when possible, else trimmed string."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        text = str(raw).strip()
        return text if text else None


class ExamApiClient:
    """Thread-safe API client for exam and coding endpoints."""

    def __init__(self, server_url: str, email: str, login_token: str):
        self._state_lock = threading.RLock()
        self.server_url = (server_url or "").rstrip("/")
        self.email = (email or "").strip().lower()
        self.login_token = (login_token or "").strip()
        self.hardware_fingerprint = _machine_fingerprint()

    def _snapshot_auth(self) -> tuple[str, str, str, str]:
        """Return an atomic snapshot of auth/session fields for request building."""
        with self._state_lock:
            return (
                self.server_url,
                self.email,
                self.login_token,
                self.hardware_fingerprint,
            )

    def update_auth(self, *, email: Optional[str] = None, login_token: Optional[str] = None) -> None:
        """Best-effort runtime auth refresh used by long-lived clients."""
        with self._state_lock:
            if email is not None:
                self.email = str(email or "").strip().lower()
            if login_token is not None:
                self.login_token = str(login_token or "").strip()

    def bootstrap(
        self,
        exam_id: Optional[int] = None,
        exam_launch_code: Optional[str] = None,
        timeout: float = 12.0,
    ) -> dict[str, Any]:
        """Bootstrap an exam session.

        Sends login identity plus optional exam selectors and returns bootstrap
        payload from the backend.
        """
        server_url, email, login_token, _ = self._snapshot_auth()
        payload: dict[str, Any] = {
            "email": email,
            "login_token": login_token,
        }
        if exam_id is not None:
            payload["exam_id"] = exam_id
        if exam_launch_code:
            payload["exam_launch_code"] = str(exam_launch_code).strip().upper()
        headers = {
            "Content-Type": "application/json",
            "X-Virtusa-Signature": _signature(payload),
        }
        response = requests.post(
            f"{server_url}/v1/exam/bootstrap",
            data=_stable_json(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def save_answer(
        self,
        attempt_id: int,
        exam_id: int,
        question_id: Any,
        answer: Any,
        confidence: Optional[int] = None,
        time_taken_seconds: Optional[int] = None,
        question_number: Optional[int] = None,
        timeout: float = 8.0,
    ) -> dict[str, Any]:
        """Persist a single question answer for an active attempt."""
        server_url, email, login_token, _ = self._snapshot_auth()
        if isinstance(answer, list):
            selected = json.dumps(answer, ensure_ascii=True)
        else:
            selected = str(answer) if answer is not None else ""

        payload = {
            "email": email,
            "login_token": login_token,
            "exam_id": int(exam_id),
            "attempt_id": int(attempt_id),
            "question_id": _coerce_question_id(question_id),
            "selected_option": selected,
            "timestamp": time.time(),
        }
        if confidence is not None:
            payload["confidence"] = int(confidence)
        if time_taken_seconds is not None:
            payload["time_taken_seconds"] = max(0, int(time_taken_seconds))
        if question_number is not None:
            payload["question_number"] = int(question_number)
        headers = {
            "Content-Type": "application/json",
            "X-Virtusa-Signature": _signature(payload),
        }
        response = requests.post(
            f"{server_url}/v1/exam/answer",
            data=_stable_json(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def submit_exam(
        self,
        session_nonce: str,
        attempt_id: int,
        answers: dict,
        total_questions: int,
        duration_seconds: int,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """Submit finalized exam answers and session metadata."""
        server_url, _, _, hardware_fingerprint = self._snapshot_auth()
        payload = {
            "session_nonce": (session_nonce or "").strip(),
            "hardware_fingerprint": hardware_fingerprint,
            "attempt_id": int(attempt_id),
            "answers": answers,
            "total_questions": int(total_questions),
            "session_duration_seconds": int(duration_seconds),
            "submitted_at": time.time(),
        }
        headers = {
            "Content-Type": "application/json",
            "X-Virtusa-Signature": _signature(payload),
        }
        response = requests.post(
            f"{server_url}/v1/exam/submit",
            data=_stable_json(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def upload_exam_logs(
        self,
        session_nonce: str,
        attempt_id: int,
        log_text: str,
        process_snapshot: Optional[dict] = None,
        upload_reason: Optional[str] = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """Upload exam runtime logs and optional process snapshot evidence."""
        server_url, email, login_token, hardware_fingerprint = self._snapshot_auth()
        payload = {
            "session_nonce": (session_nonce or "").strip(),
            "email": email,
            "login_token": login_token,
            "hardware_fingerprint": hardware_fingerprint,
            "attempt_id": int(attempt_id),
            "log_text": str(log_text or ""),
            "process_snapshot": process_snapshot or {},
            "upload_reason": str(upload_reason or "finalize"),
            "uploaded_at": time.time(),
        }
        headers = {
            "Content-Type": "application/json",
            "X-Virtusa-Signature": _signature(payload),
        }
        response = requests.post(
            f"{server_url}/v1/exam/logs",
            data=_stable_json(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def run_code(
        self,
        language: str,
        source_code: str,
        stdin: str = "",
        question_id: Optional[Any] = None,
        attempt_id: Optional[int] = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """Execute coding-question source code through remote judge endpoints.

        Endpoint strategy:
        - Try optional VIRTUSA_CODE_RUN_PATH first when configured.
        - Fall back to known default paths.
        - Retry transient transport/service failures with short backoff.
        """
        server_url, email, login_token, _ = self._snapshot_auth()
        payload = {
            "email": email,
            "login_token": login_token,
            "language": str(language or "python").lower(),
            "source_code": str(source_code or ""),
            "stdin": str(stdin or ""),
            "question_id": _coerce_question_id(question_id),
            "attempt_id": int(attempt_id) if attempt_id is not None else None,
            "timestamp": time.time(),
        }
        configured_path = (os.getenv("VIRTUSA_CODE_RUN_PATH") or "").strip()
        candidate_paths = []
        if configured_path:
            candidate_paths.append(configured_path)
        candidate_paths.extend(["/v1/exam/coding/run", "/v1/exam/code/run"])

        last_error: Exception | None = None
        for path in candidate_paths:
            normalized = path if str(path).startswith("/") else f"/{path}"
            for attempt in range(3):
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "X-Virtusa-Signature": _signature(payload),
                    }
                    response = requests.post(
                        f"{server_url}{normalized}",
                        data=_stable_json(payload),
                        headers=headers,
                        timeout=timeout,
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.HTTPError as exc:
                    last_error = exc
                    status_code = getattr(exc.response, "status_code", None)
                    if status_code == 404:
                        # Endpoint not present; move to the next candidate path.
                        break
                    if status_code in {502, 503, 504} and attempt < 2:
                        # Retry transient upstream availability errors.
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise
                except requests.RequestException as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("Code execution endpoint not configured")

    def submit_coding(
        self,
        question_id: Any,
        language: str,
        source_code: str,
        attempt_id: Optional[int] = None,
        test_results: Optional[list[dict[str, Any]]] = None,
        execution_time_ms: Optional[int] = None,
        memory_used_kb: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """Submit final coding answer and optional execution diagnostics."""
        server_url, email, login_token, _ = self._snapshot_auth()
        payload: dict[str, Any] = {
            "email": email,
            "login_token": login_token,
            "question_id": _coerce_question_id(question_id),
            "language": str(language or "python").lower(),
            "source_code": str(source_code or ""),
        }
        if attempt_id is not None:
            payload["attempt_id"] = int(attempt_id)
        if test_results is not None:
            payload["test_results"] = test_results
        if execution_time_ms is not None:
            payload["execution_time_ms"] = int(execution_time_ms)
        if memory_used_kb is not None:
            payload["memory_used_kb"] = int(memory_used_kb)
        if stdout is not None:
            payload["stdout"] = str(stdout)
        if stderr is not None:
            payload["stderr"] = str(stderr)

        headers = {
            "Content-Type": "application/json",
            "X-Virtusa-Signature": _signature(payload),
        }

        response = requests.post(
            f"{server_url}/v1/exam/coding/submit",
            data=_stable_json(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
