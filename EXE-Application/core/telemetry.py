"""
Secure telemetry transport for proctoring decisions.

Provides:
- Session authentication using login token, machine fingerprint, and server nonce.
- Replay/tamper protection via monotonic sequence ID and payload hash.
- HMAC-SHA256 signing for JSON request bodies.
- TLS hardening (minimum TLS 1.2) with optional certificate pin validation.
- Server-time offset correction for timestamp consistency.
- Fail-closed decisions on authentication, transport, or verification errors.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import socket
import ssl
import threading
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

try:
    from .backend_config import get_backend_url
except Exception:
    def get_backend_url() -> str:
        raise RuntimeError("Backend configuration unavailable. Cannot initialize telemetry client.")


def _stable_json(data: dict) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_secret() -> bytes:
    """Load and validate shared HMAC secret from environment."""
    raw = (os.environ.get("OBSERVE_PROCTOR_SECRET") or "").strip()
    if not raw or raw == "dev-shared-secret-change-me" or len(raw) < 24:
        raise RuntimeError(
            "Invalid OBSERVE_PROCTOR_SECRET. Configure a strong production secret (min 24 chars)."
        )
    return raw.encode("utf-8")


def _machine_fingerprint() -> str:
    """Best-effort machine fingerprint used for binding auth/session state."""
    parts = [
        platform.system(),
        platform.release(),
        platform.machine(),
        str(uuid.getnode()),
        socket.gethostname(),
    ]
    payload = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


def _tls_context() -> ssl.SSLContext:
    """Create TLS context with hardened minimum protocol version."""
    ctx = ssl.create_default_context()
    # Enforce TLS 1.2 minimum.
    if hasattr(ssl, "TLSVersion"):
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


@dataclass
class _HttpResult:
    status: int
    data: dict[str, Any]


class TelemetryClient:
    """Secure telemetry session client with fail-closed semantics."""

    def __init__(
        self,
        email: str,
        login_token: str,
        backend_url: Optional[str] = None,
    ):
        self.email = (email or "").strip().lower()
        self.login_token = (login_token or "").strip()
        self.backend_url = (backend_url or get_backend_url()).rstrip("/")

        self.hardware_fingerprint = _machine_fingerprint()
        self._shared_secret = _default_secret()

        self._authenticated = False
        self._session_nonce: Optional[str] = None
        self._time_offset_sec: float = 0.0
        self._sequence_id: int = 0
        self._auth_response: dict[str, Any] = {}
        self._state_lock = threading.RLock()

        # Optional certificate pin: SHA-256 of leaf certificate DER bytes.
        self._pinned_cert_sha256 = os.environ.get("OBSERVE_TLS_PIN_SHA256", "").strip().lower()

    @property
    def session_nonce(self) -> Optional[str]:
        with self._state_lock:
            return self._session_nonce

    @property
    def blacklisted_hashes(self) -> list[str]:
        with self._state_lock:
            raw = self._auth_response.get("blacklisted_hashes") or []
        if not isinstance(raw, list):
            return []
        cleaned: list[str] = []
        for item in raw:
            digest = str(item or "").strip().lower()
            if len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest):
                cleaned.append(digest)
        return cleaned

    def _sign(self, payload_bytes: bytes) -> str:
        return hmac.new(self._shared_secret, payload_bytes, hashlib.sha256).hexdigest()

    def _verify_tls_pin(self, url: str, context: ssl.SSLContext) -> bool:
        """Validate optional certificate pin for target HTTPS endpoint."""
        if not self._pinned_cert_sha256:
            return True

        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or 443
            if not host:
                return False

            with socket.create_connection((host, port), timeout=8) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)

            if cert_der is None:
                return False

            actual = hashlib.sha256(cert_der).hexdigest().lower()
            return hmac.compare_digest(actual, self._pinned_cert_sha256)
        except Exception:
            return False

    def _post_json(self, path: str, payload: dict, timeout: float = 10.0) -> _HttpResult:
        """Send signed JSON POST request and return parsed response wrapper."""
        url = f"{self.backend_url}{path}"
        body = _stable_json(payload)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ObserveProctorTelemetry/2.0",
            "X-Observe-Signature": self._sign(body),
        }

        ctx = _tls_context()
        if not self._verify_tls_pin(url, ctx):
            raise RuntimeError("TLS certificate pin verification failed")

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {}
            return _HttpResult(status=status, data=data)

    def authenticate_session(self) -> bool:
        """
        Authenticate telemetry session and obtain server nonce/time.

        Returns False on any validation, transport, or response error.
        """
        if not self.email or not self.login_token:
            with self._state_lock:
                self._authenticated = False
                self._session_nonce = None
            return False

        payload = {
            "email": self.email,
            "login_token": self.login_token,
            "hardware_fingerprint": self.hardware_fingerprint,
            "client_time": time.time(),
        }

        try:
            res = self._post_json("/v1/session/nonce", payload, timeout=10.0)
            if res.status != 200:
                with self._state_lock:
                    self._authenticated = False
                    self._session_nonce = None
                    self._auth_response = {}
                return False

            nonce = str(res.data.get("session_nonce") or "").strip()
            server_time = float(res.data.get("server_time") or 0.0)
            if not nonce or server_time <= 0:
                with self._state_lock:
                    self._authenticated = False
                    self._session_nonce = None
                    self._auth_response = {}
                return False

            with self._state_lock:
                self._session_nonce = nonce
                self._auth_response = dict(res.data or {})
                self._time_offset_sec = server_time - time.time()
                self._sequence_id = 0
                self._authenticated = True
            return True
        except Exception:
            with self._state_lock:
                self._auth_response = {}
                self._authenticated = False
                self._session_nonce = None
            return False

    def _corrected_now(self) -> float:
        with self._state_lock:
            return time.time() + self._time_offset_sec

    def generate_payload(self, check_results: dict) -> dict[str, Any]:
        """Generate signed telemetry payload with replay-protection fields."""
        with self._state_lock:
            self._sequence_id += 1
            sequence_id = self._sequence_id
            session_nonce = self._session_nonce

        payload_core = {
            "email": self.email,
            "session_nonce": session_nonce,
            "hardware_fingerprint": self.hardware_fingerprint,
            "sequence_id": sequence_id,
            "timestamp": self._corrected_now(),
            "results": check_results,
        }

        # Hash of the semantic payload body for replay/tamper checks.
        payload_hash = _sha256_hex(_stable_json(payload_core))
        payload_core["payload_hash"] = payload_hash
        return payload_core

    def send_telemetry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Send telemetry to backend.

        Fail-closed return shape always includes a blocking server decision
        on transport/authentication failures.
        """
        with self._state_lock:
            is_authenticated = self._authenticated
            session_nonce = self._session_nonce

        if not is_authenticated or not session_nonce:
            return {
                "ok": False,
                "error": "session_not_authenticated",
                "server_decision": {"is_safe": False, "action": "block"},
            }

        try:
            res = self._post_json("/v1/telemetry", payload, timeout=10.0)
            if res.status != 200:
                return {
                    "ok": False,
                    "error": f"http_{res.status}",
                    "server_decision": {"is_safe": False, "action": "block"},
                }

            decision = res.data.get("server_decision") or {}
            if not isinstance(decision, dict):
                decision = {}

            return {
                "ok": True,
                "server_decision": {
                    "is_safe": bool(decision.get("is_safe", False)),
                    "action": str(decision.get("action", "block")),
                    "reasons": decision.get("reasons", []),
                },
                "server_time": res.data.get("server_time"),
            }
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, RuntimeError):
            return {
                "ok": False,
                "error": "transport_or_tls_failure",
                "server_decision": {"is_safe": False, "action": "block"},
            }
        except Exception:
            return {
                "ok": False,
                "error": "unexpected_error",
                "server_decision": {"is_safe": False, "action": "block"},
            }

