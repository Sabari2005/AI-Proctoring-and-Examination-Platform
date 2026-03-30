"""Secure HTTP client for the ObserveProctor backend.

Provides authentication, exam lifecycle, coding, telemetry, evidence, and log
endpoints with request signing and replay-protection metadata where required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class ProctorAPIError(Exception):
    """Raised when the server returns a non-2xx status or a known error field."""
    def __init__(self, message: str, status_code: int = 0, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class ProctorClient:
    """Thread-safe client for the ObserveProctor backend APIs.

    Args:
        base_url: Server base URL, for example http://localhost:8080.
        secret: Shared HMAC secret expected by the server.
        timeout: Request timeout in seconds.
    """

    def __init__(self, base_url: str, secret: str, timeout: float = 5.0):
        self._state_lock = threading.RLock()
        self._base_url = base_url.rstrip("/")
        self._secret   = secret.encode("utf-8")
        self._timeout  = timeout
        self._retry_count = 2  # Retry up to 2 times on timeout/connection error
        self._retry_backoff = 0.5  # Start with 500ms backoff, exponential: 0.5s, 1s, 2s

        # Authentication state.
        self._email:         str | None = None
        self._login_token:   str | None = None
        self._candidate_id:  int | None = None
        self._user_name:     str | None = None
        self._session_nonce: str | None = None
        self._hw_fp:         str | None = None       # hardware fingerprint (hex)

        # Exam state.
        self._attempt_id:    int | None = None
        self._exam_id:       int | None = None

        # Per-endpoint sequence counters used for replay protection.
        self._seq_lock = threading.Lock()
        self._sequences: dict[str, int] = {}         # endpoint → last seq sent

        # Seen payload hashes used as a local deduplication guard.
        self._seen_hashes: set[str] = set()

    def _snapshot_state(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "base_url": self._base_url,
                "timeout": self._timeout,
                "retry_count": self._retry_count,
                "retry_backoff": self._retry_backoff,
                "email": self._email,
                "login_token": self._login_token,
                "candidate_id": self._candidate_id,
                "user_name": self._user_name,
                "session_nonce": self._session_nonce,
                "hw_fp": self._hw_fp,
                "attempt_id": self._attempt_id,
                "exam_id": self._exam_id,
            }

    # Low-level helpers

    def _stable_json(self, data: dict) -> bytes:
        return json.dumps(data, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")

    def _compute_sig(self, body: bytes) -> str:
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def _next_seq(self, endpoint: str) -> int:
        with self._seq_lock:
            self._sequences[endpoint] = self._sequences.get(endpoint, 0) + 1
            return self._sequences[endpoint]

    def _payload_hash(self, payload: dict) -> str:
        """SHA-256 of the stable-JSON encoding of payload (without payload_hash key)."""
        clone = {k: v for k, v in payload.items() if k != "payload_hash"}
        return hashlib.sha256(self._stable_json(clone)).hexdigest()

    def _post(
        self,
        path: str,
        payload: dict,
        *,
        sign: bool = True,
        add_seq: bool = False,
        add_hash: bool = False,
    ) -> dict:
        """POST JSON payload to the server with retry handling."""
        payload = dict(payload)

        if add_seq:
            payload["sequence_id"] = self._next_seq(path)
            payload["timestamp"]   = datetime.now(timezone.utc).isoformat()

        if add_hash:
            payload["payload_hash"] = self._payload_hash(payload)

        body = self._stable_json(payload)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if sign:
            headers["X-Virtusa-Signature"] = self._compute_sig(body)
        state = self._snapshot_state()
        hw_fp = state.get("hw_fp")
        if hw_fp:
            headers["X-Virtusa-HW-FP"] = str(hw_fp)

        url = f"{state['base_url']}{path}"
        
        # Retry with exponential backoff on connection failures.
        retry_count = int(state["retry_count"])
        retry_backoff = float(state["retry_backoff"])
        timeout = float(state["timeout"])
        for attempt in range(retry_count + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                raw = ""
                try:
                    raw = exc.read().decode("utf-8", errors="ignore")
                    data = json.loads(raw)
                except Exception:
                    data = {"error": raw or str(exc)}
                raise ProctorAPIError(
                    data.get("error", str(exc)),
                    status_code=exc.code,
                    payload=data,
                ) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                # Retry on connection/timeout errors
                if attempt < retry_count:
                    wait = retry_backoff * (2 ** attempt)
                    time.sleep(wait)
                    continue
                raise ProctorAPIError(f"Connection failed after {retry_count + 1} attempts: {exc}") from exc

    def _get(self, path: str) -> dict:
        state = self._snapshot_state()
        url = f"{state['base_url']}{path}"
        retry_count = int(state["retry_count"])
        retry_backoff = float(state["retry_backoff"])
        timeout = float(state["timeout"])
        
        # Retry with exponential backoff on connection failures.
        for attempt in range(retry_count + 1):
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="ignore")
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"error": raw}
                raise ProctorAPIError(data.get("error", str(exc)), status_code=exc.code) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                # Retry on connection/timeout errors
                if attempt < retry_count:
                    wait = retry_backoff * (2 ** attempt)
                    time.sleep(wait)
                    continue
                raise ProctorAPIError(f"Connection failed after {retry_count + 1} attempts: {exc}") from exc

    # Public auth API

    def health_check(self) -> dict:
        """GET /health to verify service reachability."""
        return self._get("/health")

    def login(self, email: str, password: str) -> dict:
        """
        POST /v1/auth/login
        Returns { status, login_token, candidate_id, user_name, email }
        Stores login_token, email, candidate_id on success.
        """
        result = self._post(
            "/v1/auth/login",
            {"email": email, "password": password},
            sign=False,
        )
        if result.get("status") == "authenticated":
            with self._state_lock:
                self._email        = email.strip().lower()
                self._login_token  = result["login_token"]
                self._candidate_id = result.get("candidate_id")
                self._user_name    = result.get("user_name", "")
        return result

    def get_nonce(self, hardware_fingerprint: str) -> dict:
        """
        POST /v1/session/nonce
        Requires a prior successful login().
        Returns { status, session_nonce, server_time }
        Stores session_nonce and hardware_fingerprint for subsequent calls.
        """
        state = self._snapshot_state()
        login_token = state.get("login_token")
        email = state.get("email")
        if not login_token or not email:
            raise ProctorAPIError("Must call login() before get_nonce()")

        with self._state_lock:
            self._hw_fp = hardware_fingerprint
        payload = {
            "email":                email,
            "login_token":          login_token,
            "hardware_fingerprint": hardware_fingerprint,
        }
        result = self._post("/v1/session/nonce", payload, sign=True)
        if result.get("status") == "ok":
            with self._state_lock:
                self._session_nonce = result["session_nonce"]
        return result

    # Exam lifecycle

    def bootstrap_exam(self, exam_launch_code: str, exam_id: int | None = None) -> dict:
        """
        POST /v1/exam/bootstrap
        Returns status="waiting" (with seconds_to_start) or
                status="ready"   (with sections + questions + duration).
        Stores attempt_id and exam_id on "ready".
        """
        state = self._snapshot_state()
        if not state.get("login_token") or not state.get("email"):
            raise ProctorAPIError("Must be logged in to bootstrap exam")

        payload: dict[str, Any] = {
            "email":           self._email,
            "login_token":     state["login_token"],
            "exam_launch_code": exam_launch_code.strip().upper(),
        }
        payload["email"] = state["email"]
        if exam_id is not None:
            payload["exam_id"] = exam_id

        result = self._post("/v1/exam/bootstrap", payload, sign=False)

        if result.get("status") == "ready":
            with self._state_lock:
                self._attempt_id = result.get("attempt_id")
                self._exam_id    = result.get("exam_id")

        return result

    def save_answer(
        self,
        question_id: int | str,
        selected_option: str | list,
        *,
        question_number: int = 1,
        time_taken_seconds: int = 0,
        confidence: int | None = None,
    ) -> dict:
        """
        POST /v1/exam/answer
        Upserts a single answer during the exam.
        Works for both static and JIT exams.
        """
        state = self._snapshot_state()
        if not state.get("login_token") or not state.get("email"):
            raise ProctorAPIError("Must be logged in to save answer")
        if not state.get("attempt_id"):
            raise ProctorAPIError("No active attempt — call bootstrap_exam() first")

        # Serialize list answers (for MSQ) as JSON strings for transport.
        if isinstance(selected_option, list):
            answer_value = json.dumps(selected_option)
        else:
            answer_value = str(selected_option)

        payload: dict[str, Any] = {
            "email":           self._email,
            "login_token":     state["login_token"],
            "exam_id":         state.get("exam_id"),
            "attempt_id":      state["attempt_id"],
            "question_id":     question_id,
            "selected_option": answer_value,
            "answer":          answer_value,
            "question_number": question_number,
            "time_taken_seconds": time_taken_seconds,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
        }
        payload["email"] = state["email"]
        if confidence is not None:
            payload["confidence"] = confidence

        return self._post("/v1/exam/answer", payload, sign=False)

    def submit_exam(self, answers: dict, total_questions: int, session_duration_seconds: int) -> dict:
        """
        POST /v1/exam/submit
        Finalises the attempt.  Requires a valid session nonce.
        answers: { question_id_str: answer_value }
        """
        state = self._snapshot_state()
        if not state.get("session_nonce"):
            raise ProctorAPIError("No session nonce — call get_nonce() first")
        if not state.get("attempt_id"):
            raise ProctorAPIError("No active attempt — call bootstrap_exam() first")

        payload: dict[str, Any] = {
            "session_nonce":             state["session_nonce"],
            "hardware_fingerprint":      state.get("hw_fp") or "",
            "email":                     state.get("email"),
            "attempt_id":                state["attempt_id"],
            "answers":                   answers,
            "total_questions":           total_questions,
            "session_duration_seconds":  session_duration_seconds,
            "submitted_at":              datetime.now(timezone.utc).isoformat(),
        }
        return self._post("/v1/exam/submit", payload, sign=True)

    # Coding endpoints

    def run_code(
        self,
        question_id: int | str,
        language: str,
        source_code: str,
        stdin: str = "",
    ) -> dict:
        """
        POST /v1/exam/coding/run
        Execute code against public test cases.
        Returns { stdout, stderr, exit_code, execution_time_ms, public_test_results, … }
        """
        state = self._snapshot_state()
        if not state.get("login_token") or not state.get("email"):
            raise ProctorAPIError("Must be logged in to run code")

        payload: dict[str, Any] = {
            "email":       state["email"],
            "login_token": state["login_token"],
            "attempt_id":  state.get("attempt_id"),
            "question_id": question_id,
            "language":    language,
            "source_code": source_code,
            "stdin":       stdin,
        }
        return self._post("/v1/exam/coding/run", payload, sign=False)

    def submit_code(
        self,
        question_id: int | str,
        language: str,
        source_code: str,
        *,
        test_results: list | None = None,
        execution_time_ms: int | None = None,
        memory_used_kb: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> dict:
        """
        POST /v1/exam/coding/submit
        Persist the final code solution.
        """
        state = self._snapshot_state()
        if not state.get("login_token") or not state.get("email"):
            raise ProctorAPIError("Must be logged in to submit code")

        payload: dict[str, Any] = {
            "email":       state["email"],
            "login_token": state["login_token"],
            "attempt_id":  state.get("attempt_id"),
            "question_id": question_id,
            "language":    language,
            "source_code": source_code,
            "stdout":      stdout,
            "stderr":      stderr,
        }
        if test_results is not None:
            payload["test_results"] = test_results
        if execution_time_ms is not None:
            payload["execution_time_ms"] = execution_time_ms
        if memory_used_kb is not None:
            payload["memory_used_kb"] = memory_used_kb

        return self._post("/v1/exam/coding/submit", payload, sign=False)

    # Telemetry and evidence

    def send_telemetry(self, results: dict, binary_integrity_hash: str = "") -> dict:
        """
        POST /v1/telemetry
        Send proctoring telemetry (VM detection, process violations, etc.).
        Returns { status, server_decision: { is_safe, action, reasons } }
        """
        state = self._snapshot_state()
        if not state.get("session_nonce") or not state.get("email") or not state.get("hw_fp"):
            raise ProctorAPIError("Must have an active session nonce to send telemetry")

        payload: dict[str, Any] = {
            "session_nonce":        state["session_nonce"],
            "email":                state["email"],
            "hardware_fingerprint": state["hw_fp"],
            "results":              results,
            "binary_integrity_hash": binary_integrity_hash,
        }
        return self._post(
            "/v1/telemetry", payload,
            sign=True, add_seq=True, add_hash=True,
        )

    def send_evidence(self, evidence_type: str = "frame") -> dict:
        """
        POST /v1/evidence
        Acknowledge a proctoring evidence capture.
        """
        state = self._snapshot_state()
        if not state.get("session_nonce") or not state.get("hw_fp"):
            raise ProctorAPIError("Must have an active session nonce to send evidence")

        payload: dict[str, Any] = {
            "session_nonce":        state["session_nonce"],
            "email":                state.get("email"),
            "hardware_fingerprint": state["hw_fp"],
            "evidence_type":        evidence_type,
        }
        return self._post("/v1/evidence", payload, sign=True, add_seq=True)

    def save_evidence_frames(
        self,
        warning_text: str,
        frames: list[dict],
        display_frames: list[dict] | None = None,
        *,
        test_id: str = "",
        section_id: str = "",
        session_id: str = "",
    ) -> dict:
        """
        POST /v1/evidence/save-frames
        Store warning-triggered camera/display frames on the server.
        Each frame dict: { sequence, phase, timestamp, jpeg_b64 }
        """
        state = self._snapshot_state()
        if not state.get("session_nonce"):
            raise ProctorAPIError("Must have a session nonce to save evidence frames")

        payload: dict[str, Any] = {
            "session_nonce":        state["session_nonce"],
            "email":                state.get("email") or "",
            "username":             state.get("email") or "",
            "hardware_fingerprint": state.get("hw_fp") or "",
            "warning_text":         warning_text,
            "trigger_time":         time.time(),
            "frames":               frames,
            "display_frames":       display_frames or [],
            "frame_count":          len(frames),
            "display_frame_count":  len(display_frames or []),
            "test_id":              test_id or str(state.get("exam_id") or ""),
            "section_id":           section_id,
            "session_id":           session_id or state["session_nonce"],
        }
        return self._post("/v1/evidence/save-frames", payload, sign=True)

    # Logs

    def upload_logs(
        self,
        log_text: str,
        process_snapshot: dict | None = None,
        upload_reason: str = "finalize",
    ) -> dict:
        """
        POST /v1/exam/logs
        Upload client log file and optional process snapshot after exam ends.
        """
        state = self._snapshot_state()
        payload: dict[str, Any] = {
            "session_nonce":    state.get("session_nonce") or "",
            "email":            state.get("email") or "",
            "login_token":      state.get("login_token") or "",
            "hardware_fingerprint": state.get("hw_fp") or "",
            "attempt_id":       state.get("attempt_id"),
            "log_text":         log_text,
            "process_snapshot": process_snapshot or {},
            "upload_reason":    upload_reason,
        }
        return self._post("/v1/exam/logs", payload, sign=True)

    # Convenience properties

    @property
    def is_logged_in(self) -> bool:
        state = self._snapshot_state()
        return bool(state.get("login_token") and state.get("email"))

    @property
    def has_nonce(self) -> bool:
        state = self._snapshot_state()
        return bool(state.get("session_nonce"))

    @property
    def candidate_id(self) -> int | None:
        state = self._snapshot_state()
        return state.get("candidate_id")

    @property
    def attempt_id(self) -> int | None:
        state = self._snapshot_state()
        return state.get("attempt_id")

    @property
    def exam_id(self) -> int | None:
        state = self._snapshot_state()
        return state.get("exam_id")

    @property
    def user_name(self) -> str:
        return self._user_name or ""

    @property
    def email(self) -> str | None:
        return self._email