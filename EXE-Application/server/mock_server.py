"""Secure proctoring backend for local and mock runtime.

Loads environment configuration, initializes database access, and exposes
authentication, exam lifecycle, telemetry, evidence, and health endpoints.

Security controls include request signing, replay protection, session binding,
rate limiting, enrollment checks, TTL cleanup, and optional TLS support.
"""

from __future__ import annotations

import base64
import collections
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import ssl
import sys
import threading
import time
import unicodedata
from typing import Any
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote, urlparse

# Bootstrap: load .env before importing DB modules.
# Resolve imports relative to this file location.
_SERVER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SERVER_DIR))   # ensure local imports work


class _TeeStream:
    def __init__(self, console_stream, file_stream):
        self._console_stream = console_stream
        self._file_stream = file_stream

    def write(self, data):
        text = data if isinstance(data, str) else str(data)
        try:
            self._console_stream.write(text)
        except Exception:
            pass
        try:
            self._file_stream.write(text)
        except Exception:
            pass
        return len(text)

    def flush(self):
        try:
            self._console_stream.flush()
        except Exception:
            pass
        try:
            self._file_stream.flush()
        except Exception:
            pass

    def __getattr__(self, item):
        return getattr(self._console_stream, item)

 
_SERVER_LOG_PATH = _SERVER_DIR / "log.txt"
_SERVER_LOG_FILE = open(_SERVER_LOG_PATH, "a", encoding="utf-8", buffering=1)
sys.stdout = _TeeStream(sys.stdout, _SERVER_LOG_FILE)
sys.stderr = _TeeStream(sys.stderr, _SERVER_LOG_FILE)

from env_loader import load_env  # noqa: E402  (must be after sys.path insertion)

load_env(base_dir=str(_SERVER_DIR))

# DB imports run after env loading so DATABASE_URL is available.
from db import get_db, ping_db  # noqa: E402
from models import (  # noqa: E402
    Answer,
    Candidate,
    CodeSubmission,
    CodingQuestion,
    Drive,
    ExamLaunchCode,
    DriveRegistration,
    ExamAttempt,
    ExamSection,
    LLMQuestionVariant,
    JitAnswerEvent,
    JitSectionSession,
    Question,
    TestCase,
    User,
)

# passlib bcrypt verification for login authentication.
try:
    from passlib.hash import bcrypt as _bcrypt  # type: ignore

    def _verify_password(plain: str, hashed: str) -> bool:
        return _bcrypt.verify(plain, hashed)

except ImportError:
    raise RuntimeError("passlib is required for production authentication (bcrypt verification).")


# Configuration
PORT               = int(os.environ.get("SERVER_PORT", "8080"))
NONCE_TTL_SECONDS  = 30 * 60          # 30 minutes
LOGIN_TOKEN_TTL_SECONDS = 2 * 3600   # 2 hours — login tokens expire after 2 hours (single-use per exam attempt)
MAX_SESSIONS       = 10_000
MAX_RATE_IPS       = 5_000
RATE_LIMIT_COUNT   = 10
RATE_LIMIT_WINDOW  = 60               # seconds
LOGIN_RATE_LIMIT_IP_COUNT = int(os.environ.get("VIRTUSA_LOGIN_RATE_LIMIT_IP_COUNT", "12") or 12)
LOGIN_RATE_LIMIT_EMAIL_COUNT = int(os.environ.get("VIRTUSA_LOGIN_RATE_LIMIT_EMAIL_COUNT", "20") or 20)
LOGIN_RATE_LIMIT_WINDOW = int(os.environ.get("VIRTUSA_LOGIN_RATE_LIMIT_WINDOW_SEC", "60") or 60)
LOGIN_ACTIVE_CHECK_INTERVAL_SECONDS = int(os.environ.get("VIRTUSA_LOGIN_ACTIVE_CHECK_INTERVAL_SEC", "30") or 30)
HEALTH_DB_CHECK_INTERVAL_SECONDS = max(1, int(os.environ.get("HEALTH_DB_CHECK_INTERVAL_SECONDS", "5")))
REQUEST_MAX_WORKERS = max(4, int(os.environ.get("VIRTUSA_SERVER_MAX_WORKERS", "64") or 64))
REQUEST_QUEUE_SIZE = max(16, int(os.environ.get("VIRTUSA_SERVER_REQUEST_QUEUE", "128") or 128))
REQUEST_HANDLER_TIMEOUT_SECONDS = max(5.0, float(os.environ.get("VIRTUSA_SERVER_REQUEST_TIMEOUT_SEC", "30") or 30))
SESSION_CLEANUP_INTERVAL_SECONDS = max(5, int(os.environ.get("VIRTUSA_SESSION_CLEANUP_INTERVAL_SEC", "15") or 15))
SESSION_PURGE_MIN_INTERVAL_SECONDS = max(2, int(os.environ.get("VIRTUSA_SESSION_PURGE_MIN_INTERVAL_SEC", "5") or 5))
CLIENT_LOGS_DIR = _SERVER_DIR / "client_logs"
EVIDENCE_FRAMES_DIR = _SERVER_DIR / "evidence_frames"
IP_BINDING_MODE = (os.environ.get("VIRTUSA_IP_BINDING_MODE", "private-any") or "private-any").strip().lower()
TRUST_PROXY_TLS = os.environ.get("VIRTUSA_TRUST_PROXY_TLS", "1").lower() in ("1", "true", "yes", "on")
ALLOW_NONCE_AUTO_ENROLL = os.environ.get("VIRTUSA_ALLOW_NONCE_AUTO_ENROLL", "1").lower() in ("1", "true", "yes", "on")
JIT_SERVICE_BASE_URL = (os.environ.get("JIT_SERVICE_BASE_URL") or "http://127.0.0.1:8002/v1").strip().rstrip("/")
JIT_SERVICE_TIMEOUT_SECONDS = float(os.environ.get("JIT_SERVICE_TIMEOUT_SECONDS", "20"))
REPORT_SERVICE_BASE_URL = (os.environ.get("REPORT_SERVICE_BASE_URL") or "http://127.0.0.1:8010").strip().rstrip("/")
REPORT_SERVICE_ENDPOINT = (os.environ.get("REPORT_SERVICE_ENDPOINT") or "/v1/reports/generate").strip()
REPORT_SERVICE_TIMEOUT_SECONDS = float(os.environ.get("REPORT_SERVICE_TIMEOUT_SECONDS", "90"))
REPORT_SERVICE_RETRY_COUNT = max(0, int(os.environ.get("REPORT_SERVICE_RETRY_COUNT", "2") or 2))
REPORT_SERVICE_RETRY_BACKOFF_SECONDS = max(0.0, float(os.environ.get("REPORT_SERVICE_RETRY_BACKOFF_SECONDS", "2") or 2))
REPORT_SERVICE_AUTH_TOKEN = (os.environ.get("REPORT_SERVICE_AUTH_TOKEN") or "").strip()
# Supabase evidence and log storage settings.
SUPABASE_URL              = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
EVIDENCE_BUCKET           = (os.environ.get("EVIDENCE_BUCKET") or "evidence-frames").strip()
EXAM_LOGS_BUCKET          = (os.environ.get("EXAM_LOGS_BUCKET") or "exam-logs").strip()

# Comma-separated SHA-256 hashes supplied by server security policy.
_RAW_BLACKLISTED_SHA256 = (os.environ.get("VIRTUSA_BLACKLISTED_SHA256") or "").strip()
SERVER_BLACKLISTED_SHA256: list[str] = []
for _item in [x.strip().lower() for x in _RAW_BLACKLISTED_SHA256.split(",") if x.strip()]:
    if len(_item) == 64 and all(ch in "0123456789abcdef" for ch in _item):
        SERVER_BLACKLISTED_SHA256.append(_item)

# When enabled, reject hardware fingerprints not present in enrolled registry.
_STRICT_ENROLLMENT = os.environ.get("VIRTUSA_STRICT_ENROLLMENT", "1").lower() in ("1", "true", "yes")
_SECRET_RAW = (os.environ.get("VIRTUSA_PROCTOR_SECRET") or "").strip()
if not _SECRET_RAW or _SECRET_RAW == "dev-shared-secret-change-me" or len(_SECRET_RAW) < 24:
    raise RuntimeError(
        "Invalid VIRTUSA_PROCTOR_SECRET. Set a strong production secret (min 24 chars) in server/.env"
    )
CLIENT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FRAMES_DIR.mkdir(parents=True, exist_ok=True)


# Helpers

def _shared_secret() -> bytes:
    return _SECRET_RAW.encode("utf-8")


def _stable_json(data: dict) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")


def _compute_sig(body: bytes) -> str:
    return hmac.new(_shared_secret(), body, hashlib.sha256).hexdigest()


def _normalize_coding_language(raw: str) -> str:
    aliases = {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "node": "javascript",
        "c++": "cpp",
        "cxx": "cpp",
        "golang": "go",
    }
    value = (raw or "python").strip().lower()
    return aliases.get(value, value)


def _coerce_question_id(raw: Any):
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        text = str(raw).strip()
        return text if text else None


def _safe_storage_component(value: Any, max_len: int = 80, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._- ")
    cleaned = cleaned[:max_len].strip("._- ")
    return cleaned or fallback


def _dedupe_variants_by_source(rows: list[LLMQuestionVariant]) -> list[LLMQuestionVariant]:
    by_source: dict[int, LLMQuestionVariant] = {}
    for row in rows:
        try:
            source_id = int(getattr(row, "source_question_id", 0) or 0)
        except Exception:
            source_id = 0
        if source_id <= 0:
            continue

        previous = by_source.get(source_id)
        if previous is None:
            by_source[source_id] = row
            continue

        prev_vid = int(getattr(previous, "variant_id", 0) or 0)
        cur_vid = int(getattr(row, "variant_id", 0) or 0)
        if cur_vid > prev_vid:
            by_source[source_id] = row

    return [by_source[sid] for sid in sorted(by_source.keys())]


def _is_morphing_mode(generation_mode: str | None) -> bool:
    return "morph" in str(generation_mode or "").strip().lower()


def _get_effective_variants_for_section(
    db: Session,
    candidate_id: int,
    drive_id: int,
    section_id: int,
) -> tuple[list[LLMQuestionVariant], str]:
    """
    Resolve variants for a section.
    Priority:
    1) selected_for_exam = true
    2) any candidate+exam variants for the section (recovery path)
    """
    selected_rows = (
        db.query(LLMQuestionVariant)
        .filter(
            LLMQuestionVariant.candidate_id == int(candidate_id),
            LLMQuestionVariant.exam_id == int(drive_id),
            LLMQuestionVariant.section_id == int(section_id),
            LLMQuestionVariant.selected_for_exam == True,
        )
        .order_by(LLMQuestionVariant.source_question_id, LLMQuestionVariant.variant_id.desc())
        .all()
    )
    if selected_rows:
        return _dedupe_variants_by_source(selected_rows), "selected"

    recovered_rows = (
        db.query(LLMQuestionVariant)
        .filter(
            LLMQuestionVariant.candidate_id == int(candidate_id),
            LLMQuestionVariant.exam_id == int(drive_id),
            LLMQuestionVariant.section_id == int(section_id),
        )
        .order_by(LLMQuestionVariant.source_question_id, LLMQuestionVariant.variant_id.desc())
        .all()
    )
    if recovered_rows:
        return _dedupe_variants_by_source(recovered_rows), "recovered_unselected"

    return [], "none"


def _supabase_upload(object_path: str, data: bytes, content_type: str, bucket: str = "") -> bool:
    """
    Upload bytes to Supabase Storage via REST API.
    Returns True on success, False on any failure.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return False

    target_bucket = bucket or EVIDENCE_BUCKET
    encoded_object_path = quote(str(object_path or ""), safe="/-_.~")
    url = f"{SUPABASE_URL}/storage/v1/object/{target_bucket}/{encoded_object_path}"
    req = urllib_request.Request(
        url=url,
        data=data,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            if resp.getcode() in (200, 201):
                return True
            print(f"[SERVER] ⚠ Supabase upload unexpected status {resp.getcode()}: {object_path}")
            return False
    except urllib_error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            pass
        print(f"[SERVER] ⚠ Supabase upload HTTP {exc.code} for {object_path}: {body}")
        return False
    except Exception as exc:
        print(f"[SERVER] ⚠ Supabase upload failed for {object_path}: {exc}")
        return False


def _supabase_signed_url(object_path: str, expires_in: int = 3600) -> str | None:
    """Generate a signed time-limited URL for a private evidence object."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    encoded_object_path = quote(str(object_path or ""), safe="/-_.~")
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{EVIDENCE_BUCKET}/{encoded_object_path}"
    body = json.dumps({"expiresIn": expires_in}).encode("utf-8")
    req = urllib_request.Request(
        url=url,
        data=body,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            signed_url = result.get("signedURL") or result.get("signedUrl") or ""
            if signed_url:
                return signed_url if signed_url.startswith("http") else f"{SUPABASE_URL}{signed_url}"
    except Exception as exc:
        print(f"[SERVER] ⚠ Supabase signed URL failed for {object_path}: {exc}")
    return None


def _trigger_report_ingest(email: str, launch_code: str) -> bool:
    """Call the report ingestion API (best-effort) after exam submission."""
    clean_email = (email or "").strip().lower()
    clean_launch = (launch_code or "").strip().upper()
    if not clean_email or not clean_launch:
        return False

    endpoint = REPORT_SERVICE_ENDPOINT if REPORT_SERVICE_ENDPOINT.startswith("/") else f"/{REPORT_SERVICE_ENDPOINT}"
    url = f"{REPORT_SERVICE_BASE_URL}{endpoint}"
    body = json.dumps({"email": clean_email, "launch_code": clean_launch}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if REPORT_SERVICE_AUTH_TOKEN:
        headers["x-report-service-token"] = REPORT_SERVICE_AUTH_TOKEN

    req = urllib_request.Request(url=url, data=body, headers=headers, method="POST")
    attempts = REPORT_SERVICE_RETRY_COUNT + 1
    for attempt in range(1, attempts + 1):
        try:
            with urllib_request.urlopen(req, timeout=REPORT_SERVICE_TIMEOUT_SECONDS) as resp:
                response_body = resp.read().decode("utf-8", errors="ignore")
                if resp.getcode() not in (200, 201):
                    print(
                        f"[SERVER] ⚠ Report ingest unexpected status {resp.getcode()} "
                        f"(attempt {attempt}/{attempts}): {response_body[:300]}"
                    )
                else:
                    print(
                        f"[SERVER] ✔ Report ingest triggered for {clean_email} ({clean_launch}) "
                        f"on attempt {attempt}/{attempts}"
                    )
                    return True
        except urllib_error.HTTPError as exc:
            details = ""
            try:
                details = exc.read().decode("utf-8", errors="ignore")[:500]
            except Exception:
                pass
            # 4xx usually indicates bad request/token and won't heal with retries.
            print(f"[SERVER] ⚠ Report ingest HTTP {exc.code} (attempt {attempt}/{attempts}): {details}")
            if 400 <= int(exc.code) < 500:
                break
        except Exception as exc:
            print(f"[SERVER] ⚠ Report ingest call failed (attempt {attempt}/{attempts}): {exc}")

        if attempt < attempts and REPORT_SERVICE_RETRY_BACKOFF_SECONDS > 0:
            sleep_for = REPORT_SERVICE_RETRY_BACKOFF_SECONDS * attempt
            time.sleep(sleep_for)
    return False


def _trigger_report_ingest_async(email: str, launch_code: str):
    """Trigger report ingest in a background thread (non-blocking)."""
    def _bg_ingest():
        try:
            _trigger_report_ingest(email=email, launch_code=launch_code)
        except Exception as exc:
            print(f"[SERVER] ⚠ Background report ingest error: {exc}")

    thread = threading.Thread(target=_bg_ingest, daemon=True)
    thread.start()


# Device enrollment registry
_enrolled_lock    = threading.Lock()
_enrolled_devices: dict[str, dict] = {}


def _is_device_enrolled(hw_fp: str, ip: str) -> tuple[bool, str]:
    if not hw_fp:
        return False, "No hardware fingerprint provided"
    with _enrolled_lock:
        if hw_fp in _enrolled_devices:
            return True, "enrolled"
        if _STRICT_ENROLLMENT:
            return False, "Device not enrolled (strict mode)"
        _enrolled_devices[hw_fp] = {
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "ip": ip,
        }
        print(f"[SERVER] ⚠ AUTO-ENROLLED new device: {hw_fp[:16]}... from {ip}")
        return True, "auto-enrolled"


def _enroll_device(hw_fp: str, ip: str, source: str = "manual") -> bool:
    """Enroll a hardware fingerprint idempotently."""
    if not hw_fp:
        return False
    with _enrolled_lock:
        if hw_fp in _enrolled_devices:
            return True
        _enrolled_devices[hw_fp] = {
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "ip": ip,
            "source": source,
        }
    return True


# Bounded LRU session store
_sessions_lock   = threading.Lock()
_ACTIVE_SESSIONS: collections.OrderedDict = collections.OrderedDict()


def _add_session(nonce: str, data: dict):
    with _sessions_lock:
        if len(_ACTIVE_SESSIONS) >= MAX_SESSIONS:
            _ACTIVE_SESSIONS.popitem(last=False)
        _ACTIVE_SESSIONS[nonce] = data


def _get_session(nonce: str) -> dict | None:
    with _sessions_lock:
        return _ACTIVE_SESSIONS.get(nonce)


def _update_session(nonce: str, key: str, value):
    with _sessions_lock:
        if nonce in _ACTIVE_SESSIONS:
            _ACTIVE_SESSIONS[nonce][key] = value


def _has_blocked_nonce_session(login_token: str, email: str) -> bool:
    """Return True if any active nonce session for this login identity is blocked."""
    token = (login_token or "").strip()
    mail = (email or "").strip().lower()
    if not token or not mail:
        return False
    with _sessions_lock:
        for sess in _ACTIVE_SESSIONS.values():
            if str(sess.get("state") or "").strip().lower() != "blocked":
                continue
            if str(sess.get("login_token") or "").strip() != token:
                continue
            if str(sess.get("email") or "").strip().lower() != mail:
                continue
            return True
    return False


# Bounded rate-limit dictionary (LRU eviction)
_rate_lock  = threading.Lock()
_nonce_rate: collections.OrderedDict = collections.OrderedDict()
_login_rate: collections.OrderedDict = collections.OrderedDict()


def _check_rate_limit(ip: str) -> bool:
    now          = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    with _rate_lock:
        if ip not in _nonce_rate:
            if len(_nonce_rate) >= MAX_RATE_IPS:
                _nonce_rate.popitem(last=False)
            _nonce_rate[ip] = []
        _nonce_rate[ip] = [t for t in _nonce_rate[ip] if t > window_start]
        if len(_nonce_rate[ip]) >= RATE_LIMIT_COUNT:
            return False
        _nonce_rate[ip].append(now)
        return True


def _check_login_rate_limit(ip: str, email: str) -> bool:
    """Rate-limit login attempts per IP and per email identity."""
    now = time.time()
    window_start = now - LOGIN_RATE_LIMIT_WINDOW
    key_ip = f"ip:{(ip or '').strip()}"
    key_email = f"email:{(email or '').strip().lower()}"

    with _rate_lock:
        for key in (key_ip, key_email):
            if key not in _login_rate:
                if len(_login_rate) >= MAX_RATE_IPS:
                    _login_rate.popitem(last=False)
                _login_rate[key] = []
            _login_rate[key] = [t for t in _login_rate[key] if t > window_start]

        if len(_login_rate[key_ip]) >= LOGIN_RATE_LIMIT_IP_COUNT:
            return False
        if len(_login_rate[key_email]) >= LOGIN_RATE_LIMIT_EMAIL_COUNT:
            return False

        _login_rate[key_ip].append(now)
        _login_rate[key_email].append(now)
        return True


def _prune_stale_rate_entries():
    cutoff = time.time() - max(RATE_LIMIT_WINDOW, LOGIN_RATE_LIMIT_WINDOW)
    with _rate_lock:
        stale = [
            ip for ip, ts in _nonce_rate.items()
            if not ts or all(t <= cutoff for t in ts)
        ]
        for ip in stale:
            del _nonce_rate[ip]

        stale_login = [
            key for key, ts in _login_rate.items()
            if not ts or all(t <= cutoff for t in ts)
        ]
        for key in stale_login:
            del _login_rate[key]


# Login session store (login_token -> session dictionary)
_LOGIN_SESSIONS: dict[str, dict] = {}
_login_sessions_lock = threading.Lock()


def _set_login_session(login_token: str, session_data: dict) -> None:
    with _login_sessions_lock:
        _LOGIN_SESSIONS[login_token] = session_data


def _get_login_session_snapshot(login_token: str) -> dict | None:
    with _login_sessions_lock:
        sess = _LOGIN_SESSIONS.get(login_token)
        return dict(sess) if isinstance(sess, dict) else None


def _update_login_session_fields(login_token: str, fields: dict[str, Any]) -> bool:
    if not fields:
        return False
    with _login_sessions_lock:
        sess = _LOGIN_SESSIONS.get(login_token)
        if not isinstance(sess, dict):
            return False
        sess.update(fields)
        return True


def _normalize_ip(ip: str) -> str:
    raw = (ip or "").strip().strip('"').lower()
    if raw.startswith("for="):
        raw = raw.split("=", 1)[1].strip().strip('"')

    # Proxy header formats: [IPv6]:port and IPv4:port.
    if raw.startswith("[") and "]" in raw:
        raw = raw[1:raw.index("]")]
    elif ":" in raw and raw.count(":") == 1:
        host_part, port_part = raw.rsplit(":", 1)
        if port_part.isdigit():
            raw = host_part

    if raw.startswith("::ffff:"):
        raw = raw.split("::ffff:", 1)[1]
    if raw == "::1":
        return "127.0.0.1"
    return raw


def _extract_forwarded_for(header_value: str) -> str:
    """Extract client IP from RFC7239 Forwarded header."""
    value = (header_value or "").strip()
    if not value:
        return ""
    first = value.split(",", 1)[0]
    for part in first.split(";"):
        token = part.strip()
        if token.lower().startswith("for="):
            return _normalize_ip(token)
    return ""


def _ip_matches(session_ip: str, request_ip: str) -> bool:
    if IP_BINDING_MODE in ("off", "disabled", "none"):
        return True

    a = _normalize_ip(session_ip)
    b = _normalize_ip(request_ip)
    if a == b:
        return True
    try:
        a_addr = ipaddress.ip_address(a)
        b_addr = ipaddress.ip_address(b)
        if a_addr.is_loopback and b_addr.is_loopback:
            return True

        # Tolerant proxy/NAT mode: treat any private IPv4 <-> private IPv4 as equivalent.
        # Useful behind ingress layers where RFC1918 address blocks can change hop-to-hop.
        if IP_BINDING_MODE in ("private-any", "private"):
            if (
                isinstance(a_addr, ipaddress.IPv4Address)
                and isinstance(b_addr, ipaddress.IPv4Address)
                and a_addr.is_private
                and b_addr.is_private
            ):
                return True

        # Proxy-tolerant mode for cloud ingress: if both are private IPv4
        # and the subnet matches, treat as equivalent client identity.
        if IP_BINDING_MODE in ("private-subnet", "subnet"):
            if (
                isinstance(a_addr, ipaddress.IPv4Address)
                and isinstance(b_addr, ipaddress.IPv4Address)
                and a_addr.is_private
                and b_addr.is_private
            ):
                a_net = ipaddress.ip_network(f"{a_addr}/24", strict=False)
                if b_addr in a_net:
                    return True
    except ValueError:
        pass
    return False


# Health endpoint cache to avoid DB ping on each /health request.
_health_lock = threading.Lock()
_last_health_check_epoch: float = 0.0
_last_health_db_ok: bool = False


def _get_cached_health() -> tuple[bool, float]:
    now = time.time()
    with _health_lock:
        global _last_health_check_epoch, _last_health_db_ok
        should_refresh = (now - _last_health_check_epoch) >= HEALTH_DB_CHECK_INTERVAL_SECONDS
        if should_refresh:
            _last_health_db_ok = ping_db()
            _last_health_check_epoch = now
        return _last_health_db_ok, _last_health_check_epoch


# Per-nonce sequence tracking for replay protection.
_seen_seq_lock  = threading.Lock()
_seen_sequences: dict[str, dict[str, set]] = {}
_purge_gate_lock = threading.Lock()
_last_purge_epoch: float = 0.0


def _check_and_record_seq(nonce: str, endpoint: str, seq_id) -> bool:
    with _seen_seq_lock:
        per_nonce = _seen_sequences.setdefault(nonce, {})
        seen = per_nonce.setdefault(endpoint, set())
        if seq_id in seen:
            return False
        seen.add(seq_id)
        return True


def _purge_expired_sessions():
    now     = time.time()
    expired = []
    with _sessions_lock:
        expired = [
            n for n, s in list(_ACTIVE_SESSIONS.items())
            if now - s.get("created_epoch", now) > NONCE_TTL_SECONDS
        ]
        for n in expired:
            del _ACTIVE_SESSIONS[n]
    if expired:
        with _seen_seq_lock:
            for n in expired:
                _seen_sequences.pop(n, None)
    # Purge expired login tokens
    with _login_sessions_lock:
        expired_logins = [
            t for t, s in list(_LOGIN_SESSIONS.items())
            if now - s.get("created_at", now) > LOGIN_TOKEN_TTL_SECONDS
        ]
        for t in expired_logins:
            del _LOGIN_SESSIONS[t]
    _prune_stale_rate_entries()


def _session_cleanup_worker(stop_event: threading.Event):
    while not stop_event.wait(SESSION_CLEANUP_INTERVAL_SECONDS):
        try:
            _purge_expired_sessions()
        except Exception as exc:
            print(f"[SERVER] Cleanup worker error: {exc}")


def _maybe_purge_expired_sessions() -> None:
    global _last_purge_epoch
    now = time.time()
    with _purge_gate_lock:
        if (now - _last_purge_epoch) < SESSION_PURGE_MIN_INTERVAL_SECONDS:
            return
        _last_purge_epoch = now
    _purge_expired_sessions()


# TLS certificate generation

def _create_self_signed_cert(cert_file: str, key_file: str) -> bool:
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return True
    try:
        import datetime
        import ipaddress

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Virtusa"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256(), default_backend())
        )
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        return True
    except Exception as exc:
        print(f"[SERVER] Certificate generation failed: {exc}")
        return False


# Question normalization helpers.
# Maps DB question_type values to UI renderer keys.
_QTYPE_MAP = {
    # MCQ
    "mcq": "mcq",
    "multiple choice": "mcq",
    "multiple_choice": "mcq",
    # MSQ must remain "msq" so the client renders multi-select input.
    "msq": "msq",
    "multiple select": "msq",
    "multiple_select": "msq",
    # FIB
    "fib": "fib",
    "fill in the blanks": "fib",
    "fill_blank": "fib",
    "fill_in_the_blank": "fib",
    # Numerical
    "numerical": "numerical",
    "numeric": "numerical",
    # Short answer
    "short": "short",
    "short answer": "short",
    "short_answer": "short",
    # Long answer
    "long": "long",
    "long answer": "long",
    "long_answer": "long",
    "essay": "long",
    # Coding
    "coding": "coding",
    "code": "coding",
    # Generic text fallback
    "text": "text",
}

def _normalise_qtype(raw: str) -> str:
    return _QTYPE_MAP.get((raw or "mcq").lower().strip(), "mcq")


# def _question_from_variant(v: LLMQuestionVariant, section_id: int) -> dict:
#     """Convert an LLMQuestionVariant ORM row into the UI question dict."""
#     try:
#         payload = json.loads(v.payload_json or "{}")
#     except (json.JSONDecodeError, TypeError):
#         payload = {}

#     qtype = _normalise_qtype(payload.get("question_type") or v.source_question_type)

#     options: list[str] = []
#     if qtype in ("mcq", "msq"):
#         raw_opts = payload.get("options") or []
#         if isinstance(raw_opts, list):
#             options = [str(o) for o in raw_opts]
#         else:
#             # Try option_a … option_d style
#             for key in ("option_a", "option_b", "option_c", "option_d"):
#                 val = payload.get(key)
#                 if val:
#                     options.append(str(val))

#     result = {
#         "id": v.variant_id,                          # variant_id used for answer tracking
#         "source_question_id": v.source_question_id,
#         "section_id": section_id,
#         "type": qtype,
#         "text": payload.get("question_text") or payload.get("question") or "",
#         "options": options,
#         "marks": int(payload.get("marks") or 1),
#         "language": payload.get("language") or "python",
#         "is_variant": True,
#     }

#     if qtype == "coding":
#         raw_test_cases = payload.get("test_cases") or payload.get("sample_test_cases") or []
#         sample_cases: list[dict] = []

#         def _append_case(case_id: str, tc: Any) -> None:
#             if not isinstance(tc, dict):
#                 return
#             is_hidden = bool(tc.get("is_hidden", False))
#             is_sample = bool(tc.get("is_sample", not is_hidden))
#             if not is_sample:
#                 return
#             sample_cases.append(
#                 {
#                     "id": str(case_id),
#                     "input": str(tc.get("input", "") or ""),
#                     "expected_output": str(
#                         tc.get("expected_output", tc.get("output", "")) or ""
#                     ),
#                     "explanation": str(tc.get("explanation", "") or ""),
#                     "is_sample": True,
#                 }
#             )

#         if isinstance(raw_test_cases, dict):
#             for tc_id, tc in raw_test_cases.items():
#                 _append_case(str(tc_id), tc)
#         elif isinstance(raw_test_cases, list):
#             for idx, tc in enumerate(raw_test_cases, start=1):
#                 _append_case(str(tc.get("id", idx) if isinstance(tc, dict) else idx), tc)

#         language_value = payload.get("language") or "python"
#         if isinstance(language_value, list):
#             supported_languages = [str(x).lower() for x in language_value if str(x).strip()]
#         else:
#             supported_languages = [str(language_value).lower()]

#         starter_code = payload.get("starter_code")
#         if not isinstance(starter_code, dict):
#             function_signature = str(payload.get("function_signature") or "").strip()
#             if function_signature:
#                 starter_code = {
#                     supported_languages[0]: (
#                         f"{function_signature}\n"
#                         "    # Write your solution here\n"
#                         "    pass\n"
#                     )
#                 }
#             else:
#                 starter_code = {}

#         constraints_raw = payload.get("constraints")
#         if isinstance(constraints_raw, dict):
#             constraints = json.dumps(constraints_raw, ensure_ascii=False)
#         elif constraints_raw is None:
#             constraints = ""
#         else:
#             constraints = str(constraints_raw)

#         result.update(
#             {
#                 "title": payload.get("title") or payload.get("question_text") or payload.get("question") or "Coding Challenge",
#                 "description": payload.get("description") or payload.get("question_text") or payload.get("question") or "",
#                 "difficulty": payload.get("difficulty") or "medium",
#                 "supported_languages": supported_languages,
#                 "starter_code": starter_code,
#                 "constraints": constraints,
#                 "examples": payload.get("examples") or [],
#                 "sample_test_cases": sample_cases,
#             }
#         )

#         # Backfill with canonical coding question metadata when available.
#         db = next(get_db())
#         try:
#             coding_q = db.query(CodingQuestion).filter(
#                 CodingQuestion.question_id == v.source_question_id
#             ).first()
#             if coding_q:
#                 if not result.get("description"):
#                     result["description"] = coding_q.problem_statement
#                 if not result.get("constraints"):
#                     result["constraints"] = coding_q.constraints or ""
#                 if not result.get("starter_code"):
#                     result["starter_code"] = coding_q.starter_code or {}
#                 if not result.get("supported_languages"):
#                     result["supported_languages"] = coding_q.supported_languages or ["python"]
#                 if not result.get("examples"):
#                     result["examples"] = coding_q.examples or []
#                 result["difficulty"] = result.get("difficulty") or coding_q.difficulty or "medium"
#                 result["time_limit_ms"] = (coding_q.execution_time_limit_seconds or 10) * 1000
#                 result["memory_limit_mb"] = coding_q.memory_limit_mb or 256

#                 if not result.get("sample_test_cases"):
#                     sample_tests = db.query(TestCase).filter(
#                         TestCase.coding_question_id == coding_q.coding_question_id,
#                         TestCase.is_sample == True,
#                     ).all()
#                     result["sample_test_cases"] = [
#                         {
#                             "id": str(tc.test_case_id),
#                             "input": tc.input_data,
#                             "expected_output": tc.expected_output,
#                             "explanation": tc.explanation or "",
#                             "is_sample": True,
#                         }
#                         for tc in sample_tests
#                     ]
#         except Exception as e:
#             print(f"[SERVER] Warning: Could not enrich coding variant details: {e}")
#         finally:
#             db.close()

#     return result

def _infer_qtype_from_morph_type(morph_type: str) -> str:
    """
    Infer question type from morph_type string when question_type
    is not stored in the variant payload.
    e.g. "fib_difficulty" → "fib", "msq_distractor" → "msq"
    """
    mt = str(morph_type or "").strip().lower()
    if mt.startswith("fib"):
        return "fib"
    if mt.startswith("msq"):
        return "msq"
    if mt.startswith("short"):
        return "short"
    if mt.startswith("long"):
        return "long"
    if mt.startswith("numerical"):
        return "numerical"
    if mt.startswith("code") or mt.startswith("coding"):
        return "coding"
    if mt in ("rephrase", "contextual", "distractor", "structural", "difficulty"):
        return "mcq"
    return ""


def _question_from_variant(v: LLMQuestionVariant, section_id: int) -> dict:
    """Convert an LLMQuestionVariant ORM row into the UI question dict."""
    try:
        payload = json.loads(v.payload_json or "{}")
    except (json.JSONDecodeError, TypeError):
        payload = {}

    # Determine question type: prefer payload field, then morph_type prefix,
    # then DB source_question_type column.
    raw_qtype = (
        payload.get("question_type")
        or payload.get("qtype")
        or _infer_qtype_from_morph_type(str(v.morph_type or ""))
        or str(v.source_question_type or "")
    )
    qtype = _normalise_qtype(raw_qtype)

    # Base question text
    question_text = (
        str(payload.get("question_text") or "").strip()
        or str(payload.get("question") or "").strip()
    )

    result = {
        "id":                 v.variant_id,
        "source_question_id": v.source_question_id,
        "section_id":         section_id,
        "type":               qtype,
        "text":               question_text,
        "options":            [],
        "marks":              int(payload.get("marks") or 1),
        "language":           payload.get("language") or "python",
        "is_variant":         True,
        "morph_type":         str(v.morph_type or ""),
        "semantic_score":     float(v.semantic_score or 0.0),
    }

    # MCQ handling.
    if qtype == "mcq":
        raw_opts = payload.get("options") or []
        if isinstance(raw_opts, list):
            result["options"] = [str(o) for o in raw_opts]
        else:
            for key in ("option_a", "option_b", "option_c", "option_d"):
                val = payload.get(key)
                if val:
                    result["options"].append(str(val))
        result["correct_answer"] = str(payload.get("correct_answer") or "")

    # MSQ handling.
    elif qtype == "msq":
        raw_opts = payload.get("options") or []
        if isinstance(raw_opts, list):
            result["options"] = [str(o) for o in raw_opts]
        raw_correct = payload.get("correct_answers") or []
        result["correct_answers"]   = [str(a) for a in raw_correct] if isinstance(raw_correct, list) else []
        result["partial_credit"]    = bool(payload.get("partial_credit", True))
        result["penalty_for_wrong"] = bool(payload.get("penalty_for_wrong", False))

    # Fill-in-the-blank handling.
    elif qtype == "fib":
        raw_answers = payload.get("correct_answers") or []
        result["correct_answers"]  = [str(a) for a in raw_answers] if isinstance(raw_answers, list) else []
        result["blank_positions"]  = payload.get("blank_positions") or []
        result["answer_tolerance"] = str(payload.get("answer_tolerance") or "case_insensitive")
        result["hint"]             = payload.get("hint")

    # Numerical handling.
    elif qtype == "numerical":
        result["correct_value"]  = payload.get("correct_value")
        result["unit"]           = str(payload.get("unit") or "")
        result["tolerance"]      = float(payload.get("tolerance") or 0.0)
        result["decimal_places"] = int(payload.get("decimal_places") or 2)
        result["formula"]        = str(payload.get("formula") or "")

    # Short-answer handling.
    elif qtype == "short":
        result["model_answer"]   = str(payload.get("model_answer") or "")
        result["keywords"]       = payload.get("keywords") or []
        result["min_words"]      = int(payload.get("min_words") or 10)
        result["max_words"]      = int(payload.get("max_words") or 100)
        result["grading_rubric"] = payload.get("grading_rubric") or {}

    # Long-answer handling.
    elif qtype == "long":
        result["rubric"]           = payload.get("rubric") or {}
        result["word_limit"]       = payload.get("word_limit") or {"min": 100, "max": 800}
        result["requires_examples"] = bool(payload.get("requires_examples", False))

    # Coding handling.
    elif qtype == "coding":
        raw_test_cases = payload.get("test_cases") or payload.get("sample_test_cases") or []
        sample_cases: list[dict] = []

        def _append_case(case_id, tc):
            if not isinstance(tc, dict):
                return
            is_hidden = bool(tc.get("is_hidden", False))
            is_sample = bool(tc.get("is_sample", not is_hidden))
            if not is_sample:
                return
            sample_cases.append({
                "id":              str(case_id),
                "input":           str(tc.get("input", "") or ""),
                "expected_output": str(tc.get("expected_output") or tc.get("output", "") or ""),
                "explanation":     str(tc.get("explanation", "") or ""),
                "is_sample":       True,
            })

        if isinstance(raw_test_cases, dict):
            for tc_id, tc in raw_test_cases.items():
                _append_case(str(tc_id), tc)
        elif isinstance(raw_test_cases, list):
            for idx, tc in enumerate(raw_test_cases, start=1):
                _append_case(str(tc.get("id", idx) if isinstance(tc, dict) else idx), tc)

        language_value = payload.get("language") or "python"
        supported_languages = (
            [str(x).lower() for x in language_value if str(x).strip()]
            if isinstance(language_value, list)
            else [str(language_value).lower()]
        )

        starter_code = payload.get("starter_code")
        if not isinstance(starter_code, dict):
            function_signature = str(payload.get("function_signature") or "").strip()
            starter_code = {
                supported_languages[0]: (
                    f"{function_signature}\n    # Write your solution here\n    pass\n"
                    if function_signature
                    else "# Write your solution here\n"
                )
            }

        constraints_raw = payload.get("constraints")
        constraints = (
            json.dumps(constraints_raw, ensure_ascii=False)
            if isinstance(constraints_raw, dict)
            else str(constraints_raw or "")
        )

        result.update({
            "title":               question_text or "Coding Challenge",
            "description":         question_text or "",
            "difficulty":          str(payload.get("difficulty_actual") or payload.get("difficulty") or "medium"),
            "supported_languages": supported_languages,
            "starter_code":        starter_code,
            "constraints":         constraints,
            "examples":            payload.get("examples") or [],
            "sample_test_cases":   sample_cases,
            "function_signature":  str(payload.get("function_signature") or "").strip(),
        })

        # Backfill from CodingQuestion DB row if available
        db = next(get_db())
        try:
            coding_q = db.query(CodingQuestion).filter(
                CodingQuestion.question_id == v.source_question_id
            ).first()
            if coding_q:
                if not result.get("description"):
                    result["description"] = coding_q.problem_statement
                if not result.get("constraints"):
                    result["constraints"] = coding_q.constraints or ""
                if not result.get("starter_code") or result["starter_code"] == {}:
                    result["starter_code"] = coding_q.starter_code or {}
                if not result.get("supported_languages"):
                    result["supported_languages"] = coding_q.supported_languages or ["python"]
                if not result.get("examples"):
                    result["examples"] = coding_q.examples or []
                result["difficulty"] = result.get("difficulty") or coding_q.difficulty or "medium"
                result["time_limit_ms"] = (coding_q.execution_time_limit_seconds or 10) * 1000
                result["memory_limit_mb"] = coding_q.memory_limit_mb or 256

                if not result.get("sample_test_cases"):
                    sample_tests = db.query(TestCase).filter(
                        TestCase.coding_question_id == coding_q.coding_question_id,
                        TestCase.is_sample == True,
                    ).all()
                    result["sample_test_cases"] = [
                        {
                            "id":              str(tc.test_case_id),
                            "input":           tc.input_data,
                            "expected_output": tc.expected_output,
                            "explanation":     tc.explanation or "",
                            "is_sample":       True,
                        }
                        for tc in sample_tests
                    ]
        except Exception as e:
            print(f"[SERVER] Warning: Could not enrich coding variant details: {e}")
        finally:
            db.close()

    return result


def _question_from_db(q: Question, section_id: int) -> dict:
    """Convert a Question ORM row into the UI question dict.
    
    For coding questions, includes full details: problem statement, constraints,
    test cases, supported languages, starter code, etc.
    """
    qtype = _normalise_qtype(q.question_type)

    # Try to decode payload_json first (may contain richer data)
    payload: dict = {}
    if q.payload_json:
        try:
            payload = json.loads(q.payload_json)
        except (json.JSONDecodeError, TypeError):
            payload = {}

    options: list[str] = []
    if qtype in ("mcq", "msq"):
        raw_opts = payload.get("options") or []
        if isinstance(raw_opts, list) and raw_opts:
            options = [str(o) for o in raw_opts]
        else:
            for val in (q.option_a, q.option_b, q.option_c, q.option_d):
                if val:
                    options.append(str(val))

    result = {
        "id": q.question_id,
        "source_question_id": q.question_id,
        "section_id": section_id,
        "type": qtype,
        "text": q.question_text or payload.get("question_text") or "",
        "options": options,
        "marks": int(q.marks or 1),
        "language": payload.get("language") or "python",
        "is_variant": False,
    }

    # Enrich coding questions with full metadata.
    if qtype == "coding":
        db = next(get_db())
        try:
            coding_q = db.query(CodingQuestion).filter(
                CodingQuestion.question_id == q.question_id
            ).first()
            
            if coding_q:
                # Fetch sample test cases only (not hidden ones)
                sample_tests = db.query(TestCase).filter(
                    TestCase.coding_question_id == coding_q.coding_question_id,
                    TestCase.is_sample == True
                ).all()
                
                result.update({
                    "title": q.question_text or "Coding Challenge",
                    "description": coding_q.problem_statement,
                    "difficulty": coding_q.difficulty,
                    "supported_languages": coding_q.supported_languages or ["python"],
                    "starter_code": coding_q.starter_code or {},
                    "constraints": coding_q.constraints,
                    "examples": coding_q.examples or [],
                    "time_limit_ms": (coding_q.execution_time_limit_seconds or 10) * 1000,
                    "memory_limit_mb": coding_q.memory_limit_mb or 256,
                    "sample_test_cases": [
                        {
                            "id": str(tc.test_case_id),
                            "input": tc.input_data,
                            "expected_output": tc.expected_output,
                            "explanation": tc.explanation or "",
                            "is_sample": True
                        }
                        for tc in sample_tests
                    ]
                })
        except Exception as e:
            print(f"[SERVER] Warning: Could not load coding question details: {e}")
        finally:
            db.close()

    return result


def _to_jit_question_type(raw: str | None) -> str:
    value = str(raw or "mcq").strip().lower()
    mapping = {
        "mcq": "mcq",
        "msq": "msq",
        "fill in the blanks": "fib",
        "fib": "fib",
        "numeric": "numerical",
        "numerical": "numerical",
        "short answer": "short",
        "short": "short",
        "long answer": "long",
        "long": "long",
        "coding": "coding",
        "mixed": "mixed",
    }
    return mapping.get(value, "mcq")


def _strip_return_annotation(signature: str) -> str:
    """Remove Python return annotations so signature parsing remains stable."""
    return re.sub(r'\)\s*->[^:]*:', '):', signature.strip())


_SIG_RE = re.compile(
    r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:?\s*$"
)

# Starter templates for languages returned by the JIT service.
_JIT_LANG_TEMPLATES: dict[str, str] = {
    "python":     "{signature}\n    # Write your solution here\n    pass\n",
    "javascript": "// {title}\nconst lines = require('fs').readFileSync(0,'utf-8').trim().split('\\n');\n// Write your solution here\nconsole.log();\n",
    "java":       "import java.util.*;\npublic class Solution {{\n    public static void main(String[] args) {{\n        Scanner sc = new Scanner(System.in);\n        // Write your solution here\n    }}\n}}\n",
    "cpp":        "#include <bits/stdc++.h>\nusing namespace std;\nint main() {{\n    ios::sync_with_stdio(false); cin.tie(nullptr);\n    // Write your solution here\n    return 0;\n}}\n",
    "go":         'package main\nimport "fmt"\nfunc main() {{\n    // Write your solution here\n    fmt.Println()\n}}\n',
    "rust":       "use std::io::{{self,Read}};\nfn main() {{\n    let mut input=String::new();\n    std::io::stdin().read_to_string(&mut input).unwrap();\n    // Write your solution here\n}}\n",
}


def _from_jit_question(question: dict, section_id: int, section_title: str) -> dict:
    """
    Convert a raw JIT-service question dict into the UI question dict consumed
    by the EXE client (CodingWidget / CodingSection).
    """
    qtype = _normalise_qtype(str(question.get("qtype", "mcq")))
    options = question.get("options") or []
    if not isinstance(options, list):
        options = []

    payload: dict[str, Any] = {
        "id":               str(question.get("question_id") or ""),
        "source_question_id": str(question.get("question_id") or ""),
        "section_id":       section_id,
        "section_title":    section_title,
        "type":             qtype,
        "text":             str(question.get("question_text") or ""),
        "options":          [str(o) for o in options],
        "marks":            1,
        "language":         "python",
        "is_variant":       False,
        "is_jit":           True,
        "question_number":  int(question.get("question_number") or 1),
    }

    if qtype != "coding":
        return payload

    # ── Coding enrichment ─────────────────────────────────────────────────────
    signature  = str(question.get("function_signature") or "").strip()
    title_text = str(question.get("question_text") or "Coding Challenge")

    # Parse with return annotation removed to simplify regex matching.
    cleaned_sig = _strip_return_annotation(signature)
    sig_match   = _SIG_RE.match(cleaned_sig)
    function_name: str       = sig_match.group(1) if sig_match else ""
    signature_params: list[str] = []
    if sig_match:
        for part in sig_match.group(2).split(","):
            token = part.strip()
            if not token:
                continue
            token = token.split("=", 1)[0].strip()
            token = token.split(":", 1)[0].strip()
            token = token.lstrip("*")
            if token and token != "self":
                signature_params.append(token)

    # Honor supported_languages from JIT payload; default to python.
    raw_langs = question.get("supported_languages") or question.get("languages") or []
    if isinstance(raw_langs, list) and raw_langs:
        supported_languages = [str(x).strip().lower() for x in raw_langs if str(x).strip()]
    else:
        supported_languages = ["python"]

    # Build starter_code for all supported languages.
    starter_code: dict[str, str] = {}
    for lang in supported_languages:
        lang_key = lang.lower().strip()
        if lang_key == "python" and signature:
            # Ensure the signature ends with a colon (JIT may omit it)
            sig_clean = signature.rstrip(": \t")
            starter_code[lang_key] = (
                f"{sig_clean}:\n"
                "    # Write your solution here\n"
                "    pass\n"
            )
        elif lang_key in _JIT_LANG_TEMPLATES:
            try:
                starter_code[lang_key] = _JIT_LANG_TEMPLATES[lang_key].format(
                    signature=signature or f"def {function_name or 'solution'}():",
                    title=function_name or "solution",
                )
            except (KeyError, IndexError):
                starter_code[lang_key] = _JIT_LANG_TEMPLATES[lang_key]
        else:
            starter_code[lang_key] = f"# Write your {lang_key} solution here\n"

    # Derive function args/kwargs from test-case input.
    def _derive_function_payload(tc_input: Any) -> tuple[list[Any], dict[str, Any]]:
        if not function_name:
            return [], {}

        # If input is serialized JSON text, attempt to parse before inference.
        if isinstance(tc_input, str):
            stripped = tc_input.strip()
            if stripped and stripped[0] in ("{", "["):
                try:
                    tc_input = json.loads(stripped)
                except (json.JSONDecodeError, ValueError):
                    pass

        if isinstance(tc_input, dict):
            if len(signature_params) == 1 and signature_params[0] in tc_input:
                return [tc_input.get(signature_params[0])], {}
            if signature_params and all(k in tc_input for k in signature_params):
                return [tc_input.get(k) for k in signature_params], {}
            if len(signature_params) == 1:
                return [tc_input], {}
            kwargs = {k: v for k, v in tc_input.items() if k in signature_params}
            return [], kwargs
        if isinstance(tc_input, list):
            if len(signature_params) == 1:
                return [tc_input], {}
            return list(tc_input), {}
        if tc_input is None:
            return [], {}
        return [tc_input], {}

    # Parse test cases.
    raw_test_cases = question.get("test_cases") or {}
    sample_cases: list[dict] = []

    def _build_tc(tc_id: str, tc: Any) -> dict | None:
        if not isinstance(tc, dict):
            return None
        tc_input_raw = tc.get("input", "")
        expected_raw = tc.get("output", tc.get("expected_output", ""))
        expected_missing = expected_raw is None

        # Decode serialized values so function-argument derivation works correctly.
        def _try_parse(value: Any) -> Any:
            if isinstance(value, str):
                stripped = value.strip()
                if stripped and stripped[0] in ("{", "[", '"') or stripped.lstrip("-").isdigit():
                    try:
                        return json.loads(stripped)
                    except (json.JSONDecodeError, ValueError):
                        pass
            return value

        tc_input   = _try_parse(tc_input_raw)
        expected   = _try_parse(expected_raw)

        # Keep input_text as string for display/stdin paths.
        input_text = (
            json.dumps(tc_input, ensure_ascii=False)
            if isinstance(tc_input, (dict, list))
            else str(tc_input)
        )
        # Keep expected_text as string for comparison paths.
        expected_text = (
            json.dumps(expected, ensure_ascii=False)
            if isinstance(expected, (dict, list))
            else str(expected)
        )

        fn_args, fn_kwargs = _derive_function_payload(tc_input)

        return {
            "id":                      str(tc_id),
            "input":                   input_text,
            "expected_output":         expected_text,
            "expected_output_missing": expected_missing,
            "explanation":             str(tc.get("explanation") or tc.get("category") or ""),
            "category":                str(tc.get("category") or "basic"),
            "is_sample":               True,
            "function_name":           function_name,
            "function_args":           fn_args,
            "function_kwargs":         fn_kwargs,
        }

    if isinstance(raw_test_cases, dict):
        for idx, (tc_id, tc) in enumerate(raw_test_cases.items(), start=1):
            built = _build_tc(str(tc_id or idx), tc)
            if built:
                sample_cases.append(built)
    elif isinstance(raw_test_cases, list):
        for idx, tc in enumerate(raw_test_cases, start=1):
            built = _build_tc(
                str(tc.get("id", idx) if isinstance(tc, dict) else idx), tc
            )
            if built:
                sample_cases.append(built)

    # Normalize constraints payload.
    constraints_raw = question.get("constraints") or ""
    if isinstance(constraints_raw, dict):
        # Serialize dict constraints only when meaningful keys are present.
        has_real = any(
            constraints_raw.get(k)
            for k in ("time_complexity", "space_complexity", "forbidden_builtins", "notes")
        )
        constraints = json.dumps(constraints_raw, ensure_ascii=False) if has_real else ""
    else:
        constraints = str(constraints_raw).strip()
    if not constraints and signature:
        # Fall back to function signature when structured constraints are absent.
        constraints = json.dumps({
            "function": signature,
        }, ensure_ascii=False)

    payload.update({
        "title":               title_text,
        "description":         title_text,
        "difficulty":          str(question.get("difficulty") or "medium"),
        "supported_languages": supported_languages,
        "starter_code":        starter_code,
        "constraints":         constraints,
        "examples":            [],
        "sample_test_cases":   sample_cases,
    })

    return payload


def _jit_post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    base = (JIT_SERVICE_BASE_URL or "").rstrip("/")
    rel = path.lstrip("/")

    candidates: list[str] = []
    candidates.append(f"{base}/{rel}")

    if not base.endswith("/v1") and "/v1/" not in base:
        candidates.append(f"{base}/v1/{rel}")
    if base.endswith("/v1"):
        base_no_v1 = base[:-3].rstrip("/")
        if base_no_v1:
            candidates.append(f"{base_no_v1}/{rel}")

    seen: set[str] = set()
    ordered_candidates = []
    for endpoint in candidates:
        if endpoint in seen:
            continue
        seen.add(endpoint)
        ordered_candidates.append(endpoint)

    last_exc: Exception | None = None
    for endpoint in ordered_candidates:
        req = urllib_request.Request(
            url=endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=JIT_SERVICE_TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8") if response else "{}"
                parsed = json.loads(raw or "{}")
                return parsed if isinstance(parsed, dict) else {}
        except urllib_error.HTTPError as exc:
            body_preview = ""
            try:
                body_preview = exc.read().decode("utf-8", errors="ignore")[:800]
            except Exception:
                body_preview = ""
            last_exc = exc
            if int(getattr(exc, "code", 0) or 0) == 404:
                continue
            raise RuntimeError(
                f"JIT service request failed at {endpoint}: {exc}. Response: {body_preview}"
            ) from exc
        except Exception as exc:
            last_exc = exc
            raise RuntimeError(f"JIT service request failed at {endpoint}: {exc}") from exc

    raise RuntimeError(
        f"JIT service request failed (all candidate endpoints 404): {ordered_candidates}. Last error: {last_exc}"
    )


def _jit_get(path: str) -> dict:
    base = (JIT_SERVICE_BASE_URL or "").rstrip("/")
    rel = path.lstrip("/")

    candidates: list[str] = []
    candidates.append(f"{base}/{rel}")

    if not base.endswith("/v1") and "/v1/" not in base:
        candidates.append(f"{base}/v1/{rel}")
    if base.endswith("/v1"):
        base_no_v1 = base[:-3].rstrip("/")
        if base_no_v1:
            candidates.append(f"{base_no_v1}/{rel}")

    seen: set[str] = set()
    ordered_candidates = []
    for endpoint in candidates:
        if endpoint in seen:
            continue
        seen.add(endpoint)
        ordered_candidates.append(endpoint)

    last_exc: Exception | None = None
    for endpoint in ordered_candidates:
        req = urllib_request.Request(
            url=endpoint,
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        try:
            with urllib_request.urlopen(req, timeout=JIT_SERVICE_TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8") if response else "{}"
                parsed = json.loads(raw or "{}")
                return parsed if isinstance(parsed, dict) else {}
        except urllib_error.HTTPError as exc:
            body_preview = ""
            try:
                body_preview = exc.read().decode("utf-8", errors="ignore")[:800]
            except Exception:
                body_preview = ""
            last_exc = exc
            if int(getattr(exc, "code", 0) or 0) == 404:
                continue
            raise RuntimeError(
                f"JIT service request failed at {endpoint}: {exc}. Response: {body_preview}"
            ) from exc
        except Exception as exc:
            last_exc = exc
            raise RuntimeError(f"JIT service request failed at {endpoint}: {exc}") from exc

    raise RuntimeError(
        f"JIT service request failed (all candidate endpoints 404): {ordered_candidates}. Last error: {last_exc}"
    )


def _fetch_jit_final_report(session_id: str) -> dict | None:
    sid = str(session_id or "").strip()
    if not sid:
        return None
    try:
        payload = _jit_get(f"session/{sid}/report")
    except Exception as exc:
        print(f"[SERVER] ⚠ Failed fetching JIT final report for {sid}: {exc}")
        return None
    if isinstance(payload, dict) and payload:
        return payload
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_candidate_id(db, email: str) -> int | None:
    """Return candidate_id for a given email, or None if not found."""
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        return None
    candidate = db.query(Candidate).filter(Candidate.user_id == user.user_id).first()
    return candidate.candidate_id if candidate else None


def _find_or_create_attempt(db, candidate_id: int, drive_id: int) -> ExamAttempt:
    """Return in-progress attempt or create a new one."""
    attempt = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.drive_id == drive_id,
            ExamAttempt.status == "started",
        )
        .first()
    )
    if attempt:
        return attempt

    attempt = ExamAttempt(
        candidate_id=candidate_id,
        drive_id=drive_id,
        start_time=datetime.now(timezone.utc),
        status="started",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _ensure_jit_section_sessions(db, attempt_id: int, sections: list[ExamSection]) -> list[JitSectionSession]:
    existing = (
        db.query(JitSectionSession)
        .filter(JitSectionSession.attempt_id == attempt_id)
        .order_by(JitSectionSession.section_order.asc())
        .all()
    )
    if existing:
        return existing

    for section in sections:
        db.add(
            JitSectionSession(
                attempt_id=attempt_id,
                section_id=section.section_id,
                section_order=int(section.order_index or 1),
                section_title=str(section.title or "Section"),
                question_type=_to_jit_question_type(getattr(section, "question_type", "mcq")),
                planned_question_count=int(section.planned_question_count or 0),
                asked_count=0,
                status="pending",
            )
        )
    db.commit()
    return (
        db.query(JitSectionSession)
        .filter(JitSectionSession.attempt_id == attempt_id)
        .order_by(JitSectionSession.section_order.asc())
        .all()
    )


def _start_jit_section_if_needed(
    db,
    section_session: JitSectionSession,
    candidate_id: int,
    force_restart: bool = False,
) -> dict:
    if (
        not force_restart
        and section_session.jit_session_id
        and isinstance(section_session.current_question_payload, dict)
    ):
        return section_session.current_question_payload

    # start_payload = {
    #     "section_topic": section_session.section_title,
    #     # JIT service enforces 1 <= num_questions <= 50.
    #     "num_questions": min(50, max(1, int(section_session.planned_question_count or 1))),
    #     "question_type": _to_jit_question_type(section_session.question_type),
    #     "start_difficulty": 2,
    #     "candidate_id": str(candidate_id),
    # }
    raw_difficulty = getattr(section_session, "start_difficulty", None)
    if raw_difficulty is None:
        # Try to read from the DB ExamSection.marks_weight as difficulty proxy
        raw_difficulty = 2
    try:
        start_difficulty = max(1, min(5, int(raw_difficulty or 2)))
    except (TypeError, ValueError):
        start_difficulty = 2

    start_payload = {
        "section_topic": section_session.section_title,
        "num_questions": min(50, max(1, int(section_session.planned_question_count or 1))),
        "question_type": _to_jit_question_type(section_session.question_type),
        "start_difficulty": start_difficulty,
        "candidate_id": str(candidate_id),
    }
    started = _jit_post("session/start", start_payload)
    first_question = started.get("first_question") or {}
    if not isinstance(first_question, dict) or not first_question.get("question_id"):
        raise RuntimeError("JIT service did not return first_question")

    section_session.jit_session_id = str(started.get("session_id") or "")
    section_session.current_question_payload = first_question
    section_session.asked_count = max(1, int(first_question.get("question_number") or 1))
    section_session.status = "active"
    db.commit()
    return first_question


def _upsert_answer(db, attempt_id: int, question_id: int, selected_option):
    """Insert or update a single answer row.
    
    Args:
        selected_option: Can be string, empty string, or None (for skipped questions).
    """
    existing = (
        db.query(Answer)
        .filter(Answer.attempt_id == attempt_id, Answer.question_id == question_id)
        .first()
    )
    # Convert selected_option to string if it's not None, otherwise store as None
    option_value = str(selected_option) if selected_option is not None else None
    
    if existing:
        existing.selected_option = option_value
    else:
        db.add(Answer(
            attempt_id=attempt_id,
            question_id=question_id,
            selected_option=option_value,
        ))
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# HTTPS server (optional TLS wrapper)
# ─────────────────────────────────────────────────────────────────────────────

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = REQUEST_QUEUE_SIZE

    def __init__(self, server_address, handler_class):
        self._request_slots = threading.BoundedSemaphore(REQUEST_MAX_WORKERS)
        super().__init__(server_address, handler_class)

    def process_request(self, request, client_address):
        if not self._request_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\n"
                    b"Content-Length: 0\r\n\r\n"
                )
            except Exception:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


class HTTPSServer(ThreadedHTTPServer):
    def __init__(self, server_address, handler_class, cert_file=None, key_file=None):
        self.cert_file = cert_file
        self.key_file  = key_file
        super().__init__(server_address, handler_class)

    def server_bind(self):
        super().server_bind()
        if (
            self.cert_file and self.key_file
            and os.path.exists(self.cert_file)
            and os.path.exists(self.key_file)
        ):
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(self.cert_file, self.key_file)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            self.socket = ctx.wrap_socket(self.socket, server_side=True)


# ─────────────────────────────────────────────────────────────────────────────
# Request handler
# ─────────────────────────────────────────────────────────────────────────────

class ProctorHandler(BaseHTTPRequestHandler):

    def setup(self):
        super().setup()
        try:
            self.connection.settimeout(REQUEST_HANDLER_TIMEOUT_SECONDS)
        except Exception:
            pass

    def log_message(self, fmt, *args):
        # Skip noisy health logs so aggressive polling does not flood stdout.
        if getattr(self, "path", "") == "/health":
            return
        print(f"[SERVER] {fmt % args}")

    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Virtusa-Signature")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            db_ok, checked_at = _get_cached_health()
            self._send_json({
                "status": "ok",
                "db": "connected" if db_ok else "error",
                "checked_at": checked_at,
                "time": time.time(),
            })
            return
        self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_POST(self):
        _maybe_purge_expired_sessions()

        path           = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))

        default_max_body = int(os.environ.get("VIRTUSA_MAX_REQUEST_BODY_BYTES", str(1_048_576)) or 1_048_576)
        evidence_max_body = int(os.environ.get("VIRTUSA_MAX_EVIDENCE_BODY_BYTES", str(8_388_608)) or 8_388_608)
        max_body = evidence_max_body if path == "/v1/evidence/save-frames" else default_max_body

        if content_length > max_body:
            self._send_json({"error": "Request body too large"}, 413)
            return

        body = self.rfile.read(content_length) if content_length else b""

        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        require_tls = os.environ.get("VIRTUSA_REQUIRE_TLS", "1").lower() in ("1", "true", "yes", "on")
        if require_tls and not self._is_tls_or_trusted_proxy_tls():
            self._send_json({"error": "tls_required"}, 426)
            return

        routes = {
            "/v1/auth/login":          lambda: self._handle_login(req_data),
            "/v1/session/nonce":       lambda: self._handle_nonce(req_data, body),
            "/v1/telemetry":           lambda: self._handle_telemetry(req_data, body),
            "/v1/evidence":            lambda: self._handle_evidence(req_data, body),
            "/v1/evidence/save-frames": lambda: self._handle_save_evidence_frames(req_data, body),
            "/v1/exam/bootstrap":      lambda: self._handle_exam_bootstrap(req_data, body),
            "/v1/exam/answer":         lambda: self._handle_exam_answer(req_data, body),
            "/v1/exam/submit":         lambda: self._handle_exam_submit(req_data, body),
            "/v1/exam/coding/run":     lambda: self._handle_exam_coding_run(req_data, body),
            "/v1/exam/coding/submit":  lambda: self._handle_exam_submit_coding(req_data, body),
            "/v1/exam/logs":           lambda: self._handle_exam_logs(req_data, body),
        }

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    # ── Signature verification ────────────────────────────────────────────────

    def _verify_signature(self, raw_body: bytes) -> bool:
        incoming = (self.headers.get("X-Virtusa-Signature", "") or "").strip().lower()
        if not incoming:
            return False

        # Strict signature policy: signature must be HMAC(raw_body, VIRTUSA_PROCTOR_SECRET).
        # Never accept alternate keys derived from client-controlled headers.
        if len(incoming) != 64 or any(ch not in "0123456789abcdef" for ch in incoming):
            return False

        expected = _compute_sig(raw_body)
        return hmac.compare_digest(incoming, expected)

    # ── Session gate ──────────────────────────────────────────────────────────

    def _session_gate(self, session_nonce: str) -> dict | None:
        session = _get_session(session_nonce)
        if not session:
            self._send_json({"error": "Invalid or expired nonce"}, 401)
            return None
        if session.get("state") == "blocked":
            self._send_json({"error": "Session blocked"}, 403)
            return None
        return session

    def _request_ip(self) -> str:
        """
        Resolve effective client IP, honoring proxy headers when present.
        This avoids false `ip_mismatch` when running behind Cloud/LB ingress.
        """
        forwarded = _extract_forwarded_for(self.headers.get("Forwarded", ""))
        if forwarded:
            return forwarded

        xff = (self.headers.get("X-Forwarded-For", "") or "").strip()
        if xff:
            first = xff.split(",", 1)[0].strip()
            if first:
                return _normalize_ip(first)

        true_client_ip = (self.headers.get("True-Client-IP", "") or "").strip()
        if true_client_ip:
            return _normalize_ip(true_client_ip)

        cf_connecting_ip = (self.headers.get("CF-Connecting-IP", "") or "").strip()
        if cf_connecting_ip:
            return _normalize_ip(cf_connecting_ip)

        x_real_ip = (self.headers.get("X-Real-IP", "") or "").strip()
        if x_real_ip:
            return _normalize_ip(x_real_ip)

        return _normalize_ip(self.client_address[0])

    def _is_tls_or_trusted_proxy_tls(self) -> bool:
        if isinstance(self.connection, ssl.SSLSocket):
            return True
        if not TRUST_PROXY_TLS:
            return False

        xfp = (self.headers.get("X-Forwarded-Proto", "") or "").strip().lower()
        if xfp:
            return "https" in [p.strip() for p in xfp.split(",") if p.strip()]

        forwarded = (self.headers.get("Forwarded", "") or "").lower()
        return "proto=https" in forwarded

    def _check_login_session(
        self,
        token: str,
        email: str,
        ip: str,
        require_active_user: bool = False,
    ) -> tuple[bool, str]:
        sess = _get_login_session_snapshot(token)
        if not sess:
            return False, "invalid_login_token"
        created_at = sess.get("created_at", 0)
        if time.time() - created_at > LOGIN_TOKEN_TTL_SECONDS:
            return False, "login_token_expired"
        if sess.get("email") != email:
            return False, "token_email_mismatch"
        if not _ip_matches(sess.get("ip", ""), ip):
            print(
                f"[SERVER] Login session IP mismatch: token={token[:8]}... "
                f"stored={sess.get('ip')} request={ip}"
            )
            return False, "ip_mismatch"

        if require_active_user:
            now = time.time()
            last_check = float(sess.get("last_user_active_check", 0.0) or 0.0)
            cached_active = sess.get("user_active")
            must_refresh = (cached_active is None) or ((now - last_check) >= LOGIN_ACTIVE_CHECK_INTERVAL_SECONDS)

            if must_refresh:
                user_id = sess.get("user_id")
                db = next(get_db())
                try:
                    user_row = None
                    if user_id:
                        user_row = db.query(User).filter(User.user_id == int(user_id)).first()
                    if user_row is None:
                        user_row = db.query(User).filter(User.email == email).first()

                    is_active = bool(user_row and user_row.is_active)
                    if not _update_login_session_fields(token, {
                        "user_active": is_active,
                        "last_user_active_check": now,
                    }):
                        return False, "invalid_login_token"
                except Exception:
                    # Fail closed for high-security endpoints when active-state cannot be verified.
                    return False, "user_status_check_failed"
                finally:
                    db.close()

                sess = _get_login_session_snapshot(token)
                if not sess:
                    return False, "invalid_login_token"

            if sess.get("user_active") is False:
                return False, "account_disabled"

        return True, "ok"

    # ── Decision engine ───────────────────────────────────────────────────────

    def _decision_engine(self, telemetry_results: dict) -> dict:
        reasons = []
        action  = "allow"

        vm         = telemetry_results.get("vm_detected", {})
        sandbox    = telemetry_results.get("sandbox_detected", {})
        rdp        = telemetry_results.get("rdp_detected", {})
        clock      = telemetry_results.get("clock_integrity", {})
        anti_debug = telemetry_results.get("anti_debug", {})
        audio      = telemetry_results.get("audio_proctoring", {}) or {}
        os_enf     = telemetry_results.get("os_enforcement", {})
        hw_checks  = telemetry_results.get("hw_checks", {})
        media      = hw_checks.get("media_devices", {})

        audio_unavailable = audio.get("severity") == "critical"

        BLOCK_CONDITIONS = [
            (vm.get("detected"),              "Virtual machine environment detected"),
            (anti_debug.get("detected"),       "Debugger attached to proctoring process"),
            (rdp.get("detected"),              "Remote desktop / screen-sharing active"),
            (sandbox.get("detected"),          "Sandbox environment detected"),
            (clock.get("tampered"),            "System clock manipulation detected"),
            (not os_enf.get("passed", True),   os_enf.get("message", "Unsupported OS")),
            (audio_unavailable,                "Audio monitoring unavailable — exam cannot proceed"),
        ]

        block_reason = next((r for c, r in BLOCK_CONDITIONS if c), None)

        if block_reason:
            action = "block"
            reasons.append(block_reason)
        else:
            hw_flags  = media.get("flags", [])
            WARN_KW   = ["virtual audio", "voicemeeter", "vb-audio", "obs virtual"]
            warn_flags = [f for f in hw_flags if any(k in f.lower() for k in WARN_KW)]
            warn_flags += vm.get("mac_hints", [])

            proc_violations = telemetry_results.get("process_violations", {}) or {}
            proc_bad = proc_violations.get("flagged_processes", [])

            if warn_flags or proc_bad:
                action = "warn"
                reasons.extend(warn_flags + proc_bad)
            elif telemetry_results.get("client_raw_is_safe") is False:
                action = "warn"
                reasons.append("client_local_checks_unhealthy")

        # Keep warning mode non-blocking; only explicit "block" is unsafe.
        return {"is_safe": action != "block", "action": action, "reasons": reasons}

    # ─────────────────────────────────────────────────────────────────────────
    # Endpoint handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_login(self, req_data: dict):
        """
        POST /v1/auth/login
        DB-backed: verifies bcrypt password against users table,
        returns login_token + candidate_id.
        """
        email    = (req_data.get("email") or "").strip().lower()
        password = req_data.get("password") or ""
        ip       = self._request_ip()

        if not email or not password:
            self._send_json({"error": "Email and password are required"}, 400)
            return

        if not _check_login_rate_limit(ip, email):
            self._send_json({"error": "Too many login attempts. Please try again later."}, 429)
            return

        db = next(get_db())
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                self._send_json({"error": "Invalid email or password"}, 401)
                return

            if not user.is_active:
                self._send_json({"error": "Account is disabled"}, 403)
                return

            if not _verify_password(password, str(user.password_hash)):
                self._send_json({"error": "Invalid email or password"}, 401)
                return

            candidate = db.query(Candidate).filter(Candidate.user_id == user.user_id).first()
            if not candidate:
                self._send_json({"error": "Candidate profile not found for this account"}, 404)
                return

            login_token = secrets.token_hex(32)
            _set_login_session(login_token, {
                "email":        email,
                "candidate_id": candidate.candidate_id,
                "user_id":      user.user_id,
                "ip":           ip,
                "created_at":   time.time(),
                "state":        "authenticated",
            })

            self._send_json({
                "status":       "authenticated",
                "login_token":  login_token,
                "candidate_id": candidate.candidate_id,
                "user_name":    candidate.full_name or "",
                "email":        email,
            })

        except Exception as exc:
            print(f"[SERVER] ❌ Login handler error: {exc}")
            self._send_json({"error": "Internal server error during login"}, 500)

        finally:
            db.close()

    def _handle_nonce(self, req_data: dict, raw_body: bytes):
        """POST /v1/session/nonce"""
        ip = self._request_ip()

        if not _check_rate_limit(ip):
            self._send_json({"error": "Too many nonce requests"}, 429)
            return

        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        email       = (req_data.get("email") or "").strip().lower()
        login_token = (req_data.get("login_token") or "").strip()
        hw          = (req_data.get("hardware_fingerprint") or "").strip()

        if not email or not login_token or not hw:
            self._send_json({"error": "email, login_token and hardware_fingerprint are required"}, 400)
            return

        ok, reason = self._check_login_session(login_token, email, ip)
        if not ok:
            print(
                f"[SERVER] Nonce reject: reason={reason} token={login_token[:8]}... "
                f"email={email} request_ip={ip}"
            )
            self._send_json({"error": reason}, 403)
            return

        enrolled, enroll_reason = _is_device_enrolled(hw, ip)
        if not enrolled and _STRICT_ENROLLMENT and ALLOW_NONCE_AUTO_ENROLL:
            # Cloud/public-link environments may see first-seen devices frequently.
            # Allow first-time enrollment only after successful login-token validation.
            if _enroll_device(hw, ip, source="nonce_auth"):
                enrolled = True
                enroll_reason = "auto-enrolled-after-auth"
                print(f"[SERVER] ⚠ Auto-enrolled device after nonce auth: {hw[:16]}... from {ip}")

        if not enrolled:
            print(
                f"[SERVER] Nonce reject: reason=device_not_enrolled detail={enroll_reason} "
                f"email={email} ip={ip} hw={hw[:16]}..."
            )
            self._send_json({"error": f"Device not enrolled: {enroll_reason}"}, 403)
            return

        session_nonce = secrets.token_hex(32)
        now           = time.time()
        server_ts     = datetime.now(timezone.utc).isoformat()

        _add_session(session_nonce, {
            "email":                email,
            "login_token":          login_token,
            "ip":                   ip,
            "hardware_fingerprint": hw,
            "created_at":           server_ts,
            "created_epoch":        now,
            "state":                "active",
            "last_sequence":        0,
            "last_sequence_by_endpoint": {"telemetry": 0, "evidence": 0},
            "seen_payload_hashes":  set(),
            "telemetry_count":      0,
            "evidence_count":       0,
        })

        print(f"[SERVER] ✔  Nonce issued: {session_nonce[:16]}... → {ip} hw={hw[:12]}...")
        self._send_json({
            "status":           "ok",
            "session_nonce":    session_nonce,
            "server_time":      now,
            "server_timestamp": server_ts,
            "blacklisted_hashes": SERVER_BLACKLISTED_SHA256,
        })

    def _validate_session_and_replay(
        self, req_data: dict, raw_body: bytes, endpoint: str
    ) -> tuple[bool, dict | None, str]:
        if not self._verify_signature(raw_body):
            return False, None, "invalid_signature"

        session_nonce = (req_data.get("session_nonce") or "").strip()
        email         = (req_data.get("email") or "").strip().lower()
        hw            = (req_data.get("hardware_fingerprint") or "").strip()
        seq           = int(req_data.get("sequence_id") or 0)
        payload_hash  = (req_data.get("payload_hash") or "").strip().lower()

        if not session_nonce or not email or not hw or seq <= 0:
            return False, None, "missing_required_fields"

        sess = _get_session(session_nonce)
        if not sess:
            return False, None, "unknown_session_nonce"
        if sess.get("state") == "blocked":
            return False, None, "session_blocked"
        if not _ip_matches(sess.get("ip", ""), self._request_ip()):
            return False, None, "ip_binding_mismatch"
        if sess.get("email") != email:
            return False, None, "email_binding_mismatch"
        if sess.get("hardware_fingerprint") != hw:
            return False, None, "hardware_binding_mismatch"

        if not _check_and_record_seq(session_nonce, endpoint, seq):
            return False, None, "sequence_replay_detected"

        seq_by_endpoint = sess.get("last_sequence_by_endpoint") or {}
        last_endpoint_seq = int(seq_by_endpoint.get(endpoint, 0) or 0)
        if seq <= last_endpoint_seq:
            return False, None, "sequence_not_monotonic"

        if payload_hash:
            if payload_hash in sess["seen_payload_hashes"]:
                return False, None, "payload_hash_replay_detected"
            sess["seen_payload_hashes"].add(payload_hash)

        seq_by_endpoint[endpoint] = seq
        _update_session(session_nonce, "last_sequence_by_endpoint", seq_by_endpoint)
        _update_session(session_nonce, "last_sequence", max(int(sess.get("last_sequence") or 0), seq))
        _update_session(session_nonce, "state", f"{endpoint}_received")
        return True, sess, "ok"

    def _handle_telemetry(self, req_data: dict, raw_body: bytes):
        """POST /v1/telemetry"""
        ok, sess, reason = self._validate_session_and_replay(req_data, raw_body, "telemetry")
        if not ok:
            self._send_json({"error": reason, "server_decision": {"is_safe": False, "action": "block"}}, 403)
            return

        supplied_hash = (req_data.get("payload_hash") or "").strip().lower()
        if supplied_hash:
            clone = dict(req_data)
            clone.pop("payload_hash", None)
            expected_hash = hashlib.sha256(_stable_json(clone)).hexdigest().lower()
            if not hmac.compare_digest(supplied_hash, expected_hash):
                self._send_json({"error": "payload_hash_mismatch", "server_decision": {"is_safe": False, "action": "block"}}, 403)
                return

        telemetry_results = req_data.get("results") or {}
        decision          = self._decision_engine(telemetry_results)

        session_nonce = req_data.get("session_nonce", "")
        seq_id        = req_data.get("sequence_id", "?")
        ts            = req_data.get("timestamp", "?")

        def _ok(f):  return "✅ PASS" if not f else "❌ FAIL"
        def _fl(lst): return ("  " + " | ".join(str(x) for x in lst)) if lst else ""

        vm         = telemetry_results.get("vm_detected", {})
        anti_debug = telemetry_results.get("anti_debug", {})
        rdp        = telemetry_results.get("rdp_detected", {})
        sandbox    = telemetry_results.get("sandbox_detected", {})
        hw_checks  = telemetry_results.get("hw_checks", {})
        media      = hw_checks.get("media_devices", {})
        monitors   = hw_checks.get("monitors", {})
        os_enf     = telemetry_results.get("os_enforcement", {})
        proc       = telemetry_results.get("process_violations", {}) or {}
        clock      = telemetry_results.get("clock_integrity", {})
        audio      = telemetry_results.get("audio_proctoring", {}) or {}
        integrity  = telemetry_results.get("binary_integrity_hash", "")

        mon_count = monitors.get("count") if isinstance(monitors, dict) else 0
        if mon_count is None:
            mon_count = 0

        if not integrity or integrity == "unavailable" or len(str(integrity)) < 5:
            integrity_display = "⚠ Not collected"
        else:
            integrity_display = str(integrity)[:32] + ("..." if len(str(integrity)) > 32 else "")

        print(f"\n{'─'*64}")
        print(f"  TELEMETRY  |  Session: {session_nonce[:16]}  |  {ts}  |  seq={seq_id}")
        print(f"{'─'*64}")
        print(f"  OS Version      : {_ok(not os_enf.get('passed', True))}  {os_enf.get('message', '')}")
        print(f"  VM Detection    : {_ok(vm.get('detected'))}  {_fl(vm.get('flags', []))}")
        if vm.get("mac_hints"):
            print("  VM MAC Hints    : ⚠ WARN  (VMware host adapters)")
        print(f"  Debugger        : {_ok(anti_debug.get('detected'))}  {_fl(anti_debug.get('flags', []))}")
        print(f"  RDP / Remote    : {_ok(rdp.get('detected'))}  {_fl(rdp.get('flags', []))}")
        print(f"  Sandbox         : {_ok(sandbox.get('detected'))}  {_fl(sandbox.get('flags', []))}")
        print(f"  Clock Integrity : {_ok(clock.get('tampered'))}  {clock.get('message', '')}")
        print(f"  Camera/Mic      : {_ok(not media.get('passed', True))}  {_fl(media.get('flags', []))}")
        mon_flags = monitors.get("flags", [])
        print(f"  Monitors        : {'❌ FAIL' if mon_flags else '✅ PASS'}  count={mon_count}  {_fl(mon_flags)}")
        proc_bad = proc.get("flagged_processes", [])
        print(f"  Processes       : {_ok(bool(proc_bad))}  {_fl(proc_bad)}")
        audio_crit = audio.get("severity") == "critical"
        print(f"  Audio Proctor   : {'❌ CRITICAL' if audio_crit else _ok(audio.get('detected'))}  {_fl(audio.get('flags', []))}")
        print(f"  File Hash       : {integrity_display}")
        print(f"{'─'*64}")

        if decision["action"] == "block":
            print(f"  DECISION → ❌ BLOCKED   Reason: {decision.get('reasons', [])}")
            _update_session(session_nonce, "state", "blocked")
        elif decision["action"] == "warn":
            print(f"  DECISION → ⚠  WARNING   Flags: {decision.get('reasons', [])}")
            _update_session(session_nonce, "state", "warned")
        else:
            print("  DECISION → ✅ ALLOWED   Environment clean.")
        print(f"{'─'*64}\n")

        current_sess = _get_session(session_nonce)
        if current_sess:
            _update_session(session_nonce, "telemetry_count", current_sess.get("telemetry_count", 0) + 1)

        self._send_json({
            "status":          "success",
            "server_time":     time.time(),
            "server_decision": decision,
        })

    def _handle_evidence(self, req_data: dict, raw_body: bytes):
        """POST /v1/evidence"""
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        session_nonce = (req_data.get("session_nonce") or "").strip()
        seq           = int(req_data.get("sequence_id") or 0)

        if not session_nonce or seq <= 0:
            self._send_json({"error": "missing session_nonce/sequence_id"}, 400)
            return

        sess = _get_session(session_nonce)
        if not sess:
            self._send_json({"error": "unknown_session_nonce"}, 403)
            return
        if sess.get("state") == "blocked":
            self._send_json({"error": "session_blocked"}, 403)
            return
        if not _ip_matches(sess.get("ip", ""), self._request_ip()):
            self._send_json({"error": "ip_binding_mismatch"}, 403)
            return

        if not _check_and_record_seq(session_nonce, "evidence", seq):
            self._send_json({"error": "sequence_replay_detected"}, 403)
            return

        seq_by_endpoint = sess.get("last_sequence_by_endpoint") or {}
        last_evidence_seq = int(seq_by_endpoint.get("evidence", 0) or 0)
        if seq <= last_evidence_seq:
            self._send_json({"error": "sequence_not_monotonic"}, 403)
            return

        seq_by_endpoint["evidence"] = seq
        _update_session(session_nonce, "last_sequence_by_endpoint", seq_by_endpoint)
        _update_session(session_nonce, "last_sequence", max(int(sess.get("last_sequence") or 0), seq))
        _update_session(session_nonce, "evidence_count", sess.get("evidence_count", 0) + 1)
        _update_session(session_nonce, "state", "evidence_received")

        self._send_json({"status": "accepted", "stored": True, "server_time": time.time()}, 201)

    def _handle_save_evidence_frames(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/evidence/save-frames
        Receives warning-triggered evidence frames (10 before + 10 after warning).
        Stores frames locally organized by username/testid/sectionid with timestamps.
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        session_nonce = (req_data.get("session_nonce") or "").strip()
        if not session_nonce:
            self._send_json({"error": "missing session_nonce"}, 400)
            return

        sess = _get_session(session_nonce)
        if not sess:
            self._send_json({"error": "unknown_session_nonce"}, 403)
            return

        if not _ip_matches(sess.get("ip", ""), self._request_ip()):
            self._send_json({"error": "ip_binding_mismatch"}, 403)
            return

        try:
            # Extract evidence metadata from session and request
            username = (
                req_data.get("username")
                or req_data.get("email")
                or sess.get("email")
                or "unknown"
            )
            testid = (
                req_data.get("test_id")
                or req_data.get("testid")
                or sess.get("exam_id")
                or "unknown"
            )
            sectionid = (
                req_data.get("section_id")
                or req_data.get("sectionid")
                or sess.get("section_id")
                or "unknown"
            )
            testid = str(testid).replace("..", "").replace("/", "_").replace("\\", "_").strip() or "unknown"
            sectionid = str(sectionid).replace("..", "").replace("/", "_").replace("\\", "_").strip() or "unknown"
            session_id = (req_data.get("session_id") or session_nonce)

            warning_text = str(req_data.get("warning_text", "unknown_warning"))
            trigger_time = float(req_data.get("trigger_time", time.time()))
            frames = req_data.get("frames") or []
            display_frames = req_data.get("display_frames") or []
            frame_count = int(req_data.get("frame_count", 0))
            display_frame_count = int(req_data.get("display_frame_count", len(display_frames)))

            if not frames and not display_frames:
                self._send_json({"error": "no_camera_or_display_frames_provided"}, 400)
                return

            username_safe = _safe_storage_component(str(username).replace("@", "_at_"), max_len=120, fallback="unknown_user")
            testid_safe = _safe_storage_component(testid, max_len=64, fallback="unknown_test")
            section_safe = _safe_storage_component(sectionid, max_len=64, fallback="unknown_section")

            # Create directory structure: evidence_frames/username/testid/sectionid/
            evidence_dir = EVIDENCE_FRAMES_DIR / username_safe / testid_safe / section_safe
            evidence_dir.mkdir(parents=True, exist_ok=True)

            # Create warning-specific subdirectory with timestamp
            warning_safe = _safe_storage_component(warning_text, max_len=60, fallback="warning")
            timestamp_str = datetime.fromtimestamp(trigger_time, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
            warning_dir = evidence_dir / f"{timestamp_str}_{warning_safe}"
            warning_dir.mkdir(parents=True, exist_ok=True)

            sb_base = f"{username_safe}/{testid_safe}/{section_safe}/{warning_dir.name}"
            supabase_enabled = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

            # Write metadata file
            metadata = {
                "session_nonce": session_nonce,
                "session_id": session_id,
                "username": username,
                "testid": testid,
                "sectionid": sectionid,
                "warning_text": warning_text,
                "trigger_time_iso": datetime.fromtimestamp(trigger_time, tz=timezone.utc).isoformat(),
                "frame_count": frame_count,
                "display_frame_count": display_frame_count,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "supabase_bucket": EVIDENCE_BUCKET if supabase_enabled else None,
                "supabase_base_path": sb_base if supabase_enabled else None,
                "supabase_frame_paths": [],
                "supabase_display_paths": [],
            }

            # Write individual frames
            frame_paths = []
            sb_frame_paths = []
            for frame_data in frames:
                try:
                    sequence = int(frame_data.get("sequence", 0))
                    phase = str(frame_data.get("phase", "unknown"))
                    frame_ts = float(frame_data.get("timestamp", trigger_time))
                    jpeg_b64 = frame_data.get("jpeg_b64", "")

                    if not jpeg_b64:
                        continue

                    # Decode JPEG
                    jpeg_bytes = base64.b64decode(jpeg_b64)

                    # Filename: 001_before_timestamp.jpg
                    phase_safe = _safe_storage_component(phase, max_len=20, fallback="phase")
                    frame_filename = f"{sequence:03d}_{phase_safe}_{frame_ts:.0f}.jpg"
                    frame_path = warning_dir / frame_filename

                    with open(frame_path, "wb") as f:
                        f.write(jpeg_bytes)

                    frame_paths.append(frame_filename)
                    if supabase_enabled:
                        sb_path = f"{sb_base}/{frame_filename}"
                        if _supabase_upload(sb_path, jpeg_bytes, "image/jpeg"):
                            sb_frame_paths.append(sb_path)

                except Exception as e:
                    print(f"[SERVER] ⚠ Failed to store frame {frame_data.get('sequence')}: {e}")
                    continue

            # Write display screenshots (if provided)
            display_paths = []
            sb_display_paths = []
            for display_data in display_frames:
                try:
                    sequence = int(display_data.get("sequence", 0))
                    phase = str(display_data.get("phase", "unknown"))
                    frame_ts = float(display_data.get("timestamp", trigger_time))
                    jpeg_b64 = display_data.get("jpeg_b64", "")

                    if not jpeg_b64:
                        continue

                    jpeg_bytes = base64.b64decode(jpeg_b64)
                    phase_safe = _safe_storage_component(phase, max_len=20, fallback="phase")
                    frame_filename = f"display_{sequence:03d}_{phase_safe}_{frame_ts:.0f}.jpg"
                    frame_path = warning_dir / frame_filename

                    with open(frame_path, "wb") as f:
                        f.write(jpeg_bytes)

                    display_paths.append(frame_filename)
                    if supabase_enabled:
                        sb_path = f"{sb_base}/{frame_filename}"
                        if _supabase_upload(sb_path, jpeg_bytes, "image/jpeg"):
                            sb_display_paths.append(sb_path)
                except Exception as e:
                    print(f"[SERVER] ⚠ Failed to store display frame {display_data.get('sequence')}: {e}")
                    continue

            # Write index file listing all stored frames
            with open(warning_dir / "frames.txt", "w", encoding="utf-8") as f:
                for fp in frame_paths:
                    f.write(f"{fp}\n")
                for dp in display_paths:
                    f.write(f"{dp}\n")

            metadata["supabase_frame_paths"] = sb_frame_paths
            metadata["supabase_display_paths"] = sb_display_paths

            metadata_bytes = json.dumps(metadata, indent=2, default=str).encode("utf-8")
            with open(warning_dir / "metadata.json", "wb") as f:
                f.write(metadata_bytes)
            if supabase_enabled:
                _supabase_upload(f"{sb_base}/metadata.json", metadata_bytes, "application/json")

            stored_count = len(frame_paths)
            display_stored_count = len(display_paths)
            sb_uploaded_count = len(sb_frame_paths) + len(sb_display_paths)
            sb_info = f"  Supabase: {sb_uploaded_count} files -> {sb_base}" if supabase_enabled else "  Supabase: not configured"
            print(
                f"[SERVER] ✔ Warning-triggered evidence stored:\n"
                f"  Username: {username}, TestID: {testid}, SectionID: {sectionid}\n"
                f"  Warning: {warning_text}\n"
                f"  Camera frames stored: {stored_count}/{frame_count}\n"
                f"  Display screenshots stored: {display_stored_count}/{display_frame_count}\n"
                f"  Location: {warning_dir.relative_to(EVIDENCE_FRAMES_DIR)}\n"
                f"{sb_info}"
            )

            self._send_json({
                "status": "stored",
                "warning_dir": str(warning_dir.name),
                "frames_stored": stored_count,
                "total_frames": frame_count,
                "display_frames_stored": display_stored_count,
                "total_display_frames": display_frame_count,
                "session_id": session_id,
                "test_id": str(testid),
                "section_id": str(sectionid),
                "supabase_uploaded": sb_uploaded_count,
                "supabase_path": sb_base if supabase_enabled else None,
            }, 201)

        except Exception as e:
            print(f"[SERVER] ❌ Evidence frame storage error: {e}")
            self._send_json({"error": f"Storage failed: {str(e)}"}, 500)

    # ── Exam endpoints ────────────────────────────────────────────────────────

    def _handle_exam_bootstrap(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/bootstrap
        Validates login session, checks exam schedule gate, and returns the
        full exam structure (sections + questions) for the candidate.

        Request:  { email, login_token, exam_id? }
        Response (waiting):  { status: "waiting", seconds_to_start: N, exam_date: ISO }
        Response (ready):    { status: "ready", exam_id, attempt_id, title, duration,
                               sections: [{id, title, order_index, questions: [...]}] }
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        email       = (req_data.get("email") or "").strip().lower()
        login_token = (req_data.get("login_token") or "").strip()
        requested_exam_id = req_data.get("exam_id")
        exam_launch_code = (req_data.get("exam_launch_code") or "").strip().upper()
        ip          = self._request_ip()

        if not email or not login_token:
            self._send_json({"error": "email and login_token are required"}, 400)
            return
        if not exam_launch_code:
            self._send_json({"error": "exam_launch_code is required"}, 400)
            return

        ok, reason = self._check_login_session(login_token, email, ip)
        if not ok:
            self._send_json({"error": reason}, 403)
            return

        login_sess  = _get_login_session_snapshot(login_token)
        if not login_sess:
            self._send_json({"error": "invalid_login_token"}, 403)
            return
        candidate_id = login_sess.get("candidate_id")
        if not candidate_id:
            self._send_json({"error": "candidate_context_missing"}, 403)
            return
        candidate_id = int(candidate_id)

        db = next(get_db())
        try:
            now_utc = datetime.now(timezone.utc)

            launch_row = (
                db.query(ExamLaunchCode)
                .filter(
                    ExamLaunchCode.launch_code == exam_launch_code,
                    ExamLaunchCode.candidate_id == candidate_id,
                )
                .first()
            )
            if not launch_row:
                self._send_json({"error": "invalid_exam_launch_code"}, 403)
                return

            if launch_row.used_at is not None:
                self._send_json({"error": "exam_launch_code_already_used"}, 403)
                return

            expires_at = launch_row.expires_at
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at is not None and now_utc > expires_at:
                self._send_json({"error": "exam_launch_code_expired"}, 403)
                return

            # Launch code is tied to one specific registered exam.
            if requested_exam_id is not None and int(requested_exam_id) != int(launch_row.drive_id):
                self._send_json({"error": "exam_launch_code_exam_mismatch"}, 403)
                return

            requested_exam_id = int(launch_row.drive_id)

            # ── Find registered drives for this candidate ──────────────────
            reg_query = (
                db.query(DriveRegistration)
                .filter(DriveRegistration.candidate_id == candidate_id)
            )
            if requested_exam_id:
                reg_query = reg_query.filter(DriveRegistration.drive_id == int(requested_exam_id))

            registrations = reg_query.all()
            if not registrations:
                self._send_json({"error": "No exam registrations found for this candidate"}, 404)
                return

            # ── Pick the drive ─────────────────────────────────────────────
            # If a specific exam_id was requested, use it; otherwise pick the
            # first published, upcoming drive.
            drive   = None

            if requested_exam_id:
                drive = db.query(Drive).filter(
                    Drive.drive_id == int(requested_exam_id),
                    Drive.is_published == True,
                ).first()
            else:
                # Find the most immediate upcoming (or currently running) drive
                drive_ids = [r.drive_id for r in registrations]
                candidates_drives = (
                    db.query(Drive)
                    .filter(
                        Drive.drive_id.in_(drive_ids),
                        Drive.is_published == True,
                    )
                    .order_by(Drive.exam_date)
                    .all()
                )
                for d in candidates_drives:
                    if d.exam_date is None:
                        drive = d   # un-scheduled → always accessible
                        break
                    exam_dt = d.exam_date
                    if exam_dt.tzinfo is None:
                        exam_dt = exam_dt.replace(tzinfo=timezone.utc)
                    end_window = exam_dt + timedelta(minutes=d.duration_minutes or 120)
                    if now_utc <= end_window:
                        drive = d
                        break

            if not drive:
                self._send_json({"error": "No active published exam found for this candidate"}, 404)
                return

            # ── Schedule gate ──────────────────────────────────────────────
            if drive.exam_date is not None:
                exam_dt = drive.exam_date
                if exam_dt.tzinfo is None:
                    exam_dt = exam_dt.replace(tzinfo=timezone.utc)

                if now_utc < exam_dt:
                    seconds_remaining = int((exam_dt - now_utc).total_seconds())
                    self._send_json({
                        "status":           "waiting",
                        "exam_date":        exam_dt.isoformat(),
                        "seconds_to_start": seconds_remaining,
                    })
                    return

            # ── Load sections ──────────────────────────────────────────────
            sections_db = (
                db.query(ExamSection)
                .filter(ExamSection.drive_id == drive.drive_id)
                .order_by(ExamSection.order_index)
                .all()
            )

            if not sections_db:
                self._send_json({"error": "Exam has no sections configured"}, 404)
                return

            attempt = _find_or_create_attempt(db, candidate_id, drive.drive_id)

            _update_login_session_fields(
                login_token,
                {
                    "exam_launch_code": exam_launch_code,
                    "last_drive_id": int(drive.drive_id),
                    "last_attempt_id": int(attempt.attempt_id),
                    "last_bootstrap_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            if str(drive.generation_mode or "static").lower() in {"jit", "jit_generator"}:
                section_sessions = _ensure_jit_section_sessions(db, int(attempt.attempt_id), sections_db)
                ordered_sessions = sorted(section_sessions, key=lambda row: (int(row.section_order or 1), int(row.jit_section_session_id or 0)))

                active_session = next((row for row in ordered_sessions if str(row.status or "pending") in {"pending", "active"}), None)
                if active_session is None:
                    active_session = ordered_sessions[-1] if ordered_sessions else None
                if active_session is None:
                    self._send_json({"error": "JIT section sessions missing"}, 500)
                    return

                first_question = _start_jit_section_if_needed(db, active_session, candidate_id)

                sections_out = []
                for sec in sections_db:
                    matching_session = next((row for row in ordered_sessions if int(row.section_id) == int(sec.section_id)), None)
                    questions_out = []
                    if matching_session and int(matching_session.section_id) == int(active_session.section_id):
                        questions_out = [
                            _from_jit_question(
                                first_question,
                                section_id=int(sec.section_id),
                                section_title=str(sec.title or "Section"),
                            )
                        ]
                    sections_out.append(
                        {
                            "id": sec.section_id,
                            "title": sec.title,
                            "order_index": sec.order_index,
                            "question_type": _to_jit_question_type(getattr(sec, "question_type", "mcq")),
                            "planned_question_count": int(sec.planned_question_count or 0),
                            "questions": questions_out,
                        }
                    )

                launch_row.used_at = datetime.now(timezone.utc)
                db.commit()

                print(
                    f"[SERVER] JIT bootstrap response: drive={drive.drive_id} "
                    "generation_mode=jit_generator is_jit=True"
                )

                self._send_json(
                    {
                        "status": "ready",
                        "exam_id": drive.drive_id,
                        "attempt_id": attempt.attempt_id,
                        "title": drive.title,
                        "duration": (drive.duration_minutes or 90) * 60,
                        "generation_mode": "jit_generator",
                        "is_jit": True,
                        "sections": sections_out,
                    }
                )
                return

            # ── Load questions (morphing exams must use LLM variants) ──
            generation_mode = str(drive.generation_mode or "static").lower()
            is_morphing_exam = _is_morphing_mode(generation_mode)

            has_any_variants = (
                db.query(LLMQuestionVariant)
                .filter(
                    LLMQuestionVariant.candidate_id == candidate_id,
                    LLMQuestionVariant.exam_id == drive.drive_id,
                )
                .first()
            ) is not None

            use_variants = is_morphing_exam or has_any_variants

            sections_out = []
            for sec in sections_db:
                if use_variants:
                    variant_rows, variant_mode = _get_effective_variants_for_section(
                        db=db,
                        candidate_id=int(candidate_id),
                        drive_id=int(drive.drive_id),
                        section_id=int(sec.section_id),
                    )
                    if variant_rows:
                        questions_out = [_question_from_variant(v, sec.section_id) for v in variant_rows]
                        if variant_mode == "recovered_unselected":
                            print(
                                "[SERVER] ⚠ Using recovered (unselected) variants for section. "
                                f"drive={drive.drive_id} section={sec.section_id}"
                            )
                    else:
                        if is_morphing_exam:
                            self._send_json(
                                {
                                    "error": "morphed_questions_missing",
                                    "detail": f"No LLM morphed variants found for section {sec.section_id}",
                                    "exam_id": int(drive.drive_id),
                                    "section_id": int(sec.section_id),
                                },
                                409,
                            )
                            return

                        base_rows = (
                            db.query(Question)
                            .filter(
                                Question.drive_id == drive.drive_id,
                                Question.section_id == sec.section_id,
                            )
                            .order_by(Question.question_id)
                            .all()
                        )
                        questions_out = [_question_from_db(q, sec.section_id) for q in base_rows]
                else:
                    rows = (
                        db.query(Question)
                        .filter(
                            Question.drive_id == drive.drive_id,
                            Question.section_id == sec.section_id,
                        )
                        .order_by(Question.question_id)
                        .all()
                    )
                    questions_out = [_question_from_db(q, sec.section_id) for q in rows]

                sections_out.append({
                    "id":          sec.section_id,
                    "title":       sec.title,
                    "order_index": sec.order_index,
                    "questions":   questions_out,
                })

            launch_row.used_at = datetime.now(timezone.utc)
            db.commit()

            total_questions = sum(len(s["questions"]) for s in sections_out)
            print(
                f"[SERVER] ✔ Bootstrap: candidate={candidate_id} "
                f"drive={drive.drive_id} sections={len(sections_out)} "
                f"questions={total_questions} attempt={attempt.attempt_id}"
            )
            print(
                f"[SERVER] Non-JIT bootstrap response: drive={drive.drive_id} "
                f"generation_mode={str(drive.generation_mode or 'static').lower()} is_jit=False"
            )

            self._send_json({
                "status":     "ready",
                "exam_id":    drive.drive_id,
                "attempt_id": attempt.attempt_id,
                "title":      drive.title,
                "duration":   (drive.duration_minutes or 90) * 60,   # seconds
                "generation_mode": str(drive.generation_mode or "static").lower(),
                "is_jit": False,
                "sections":   sections_out,
            })

        except Exception as exc:
            import traceback
            error_details = f"Bootstrap error: {type(exc).__name__}: {str(exc)}"
            traceback_info = traceback.format_exc()
            print(f"[SERVER] ❌ {error_details}")
            print(f"[SERVER] Traceback:\n{traceback_info}")
            
            # Determine error type for more helpful client message
            error_msg = "Internal server error during exam bootstrap"
            if "database" in str(exc).lower() or "connection" in str(exc).lower():
                error_msg = "Database connection error during exam bootstrap"
            elif "no sections" in str(exc).lower():
                error_msg = "Exam has no sections configured"
            elif "question" in str(exc).lower():
                error_msg = "Error loading exam questions"
            elif "attempt" in str(exc).lower():
                error_msg = "Error creating exam attempt"
            
            self._send_json({
                "error": error_msg,
                "error_code": type(exc).__name__
            }, 500)
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _handle_exam_answer(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/answer
        Persists (or updates) a single answer during the exam.

        Request: {
            email, login_token,
            exam_id, attempt_id,
            question_id,      # variant_id or source_question_id
            selected_option,  # text string
            timestamp (ISO)
        }
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        email        = (req_data.get("email") or "").strip().lower()
        login_token  = (req_data.get("login_token") or "").strip()
        ip           = self._request_ip()

        if not email or not login_token:
            self._send_json({"error": "email and login_token are required"}, 400)
            return

        ok, reason = self._check_login_session(login_token, email, ip)
        if not ok:
            self._send_json({"error": reason}, 403)
            return

        if _has_blocked_nonce_session(login_token, email):
            self._send_json({"error": "session_blocked"}, 403)
            return

        attempt_id   = req_data.get("attempt_id")
        question_id  = req_data.get("question_id")
        
        # For morphing exams, allow None/null answers (user skipped the question)
        # For JIT exams, use empty string as fallback
        if "answer" in req_data or "selected_option" in req_data:
            selected_opt = req_data.get("selected_option") or req_data.get("answer")
        else:
            selected_opt = ""

        if not attempt_id or not question_id:
            self._send_json({"error": "attempt_id and question_id are required"}, 400)
            return

        db = next(get_db())
        try:
            # Verify attempt belongs to this candidate
            login_sess   = _get_login_session_snapshot(login_token)
            if not login_sess:
                self._send_json({"error": "invalid_login_token"}, 403)
                return
            candidate_id = login_sess.get("candidate_id")

            attempt = db.query(ExamAttempt).filter(
                ExamAttempt.attempt_id == int(attempt_id),
                ExamAttempt.candidate_id == candidate_id,
            ).first()

            if not attempt:
                self._send_json({"error": "Attempt not found or not owned by this candidate"}, 403)
                return

            if attempt.status not in ("started",):
                if str(attempt.status or "").lower() in {"submitted", "completed"}:
                    # Idempotent success for late/retried answer calls after submit.
                    self._send_json(
                        {
                            "status": "saved",
                            "generation_mode": "jit_generator",
                            "next_question": None,
                            "section_complete": True,
                            "exam_complete": True,
                            "attempt_status": str(attempt.status),
                        }
                    )
                    return
                self._send_json({"error": f"Attempt is already {attempt.status}"}, 409)
                return

            drive = db.query(Drive).filter(Drive.drive_id == int(attempt.drive_id)).first()
            generation_mode = str(getattr(drive, "generation_mode", "static") or "static").lower()

            if generation_mode in {"jit", "jit_generator"}:
                time_taken_seconds = int(req_data.get("time_taken_seconds") or 0)
                confidence_raw = req_data.get("confidence")
                confidence = None
                try:
                    if confidence_raw is not None and str(confidence_raw).strip() != "":
                        confidence = int(confidence_raw)
                except (TypeError, ValueError):
                    confidence = None

                section_sessions = (
                    db.query(JitSectionSession)
                    .filter(JitSectionSession.attempt_id == int(attempt.attempt_id))
                    .order_by(JitSectionSession.section_order.asc(), JitSectionSession.jit_section_session_id.asc())
                    .all()
                )
                active_section = next((row for row in section_sessions if str(row.status or "pending") in {"active", "pending"}), None)
                if not active_section:
                    exam_complete = bool(section_sessions) and all(
                        str(row.status or "pending") == "completed" for row in section_sessions
                    )
                    if exam_complete:
                        # Idempotent success when JIT section(s) already completed.
                        latest_completed = None
                        if section_sessions:
                            latest_completed = sorted(
                                section_sessions,
                                key=lambda row: (int(row.section_order or 0), int(row.jit_section_session_id or 0)),
                            )[-1]
                        final_report_payload = None
                        # Compatibility: some older runtime model bundles may not expose
                        # JitSectionSession.final_report yet.
                        latest_report = getattr(latest_completed, "final_report", None) if latest_completed is not None else None
                        if isinstance(latest_report, dict):
                            final_report_payload = latest_report
                        self._send_json(
                            {
                                "status": "saved",
                                "generation_mode": "jit_generator",
                                "section_id": int(latest_completed.section_id) if latest_completed is not None else None,
                                "section_title": str(latest_completed.section_title or "Section") if latest_completed is not None else "Section",
                                "next_question": None,
                                "evaluation": {},
                                "adaptive_decision": {},
                                "section_complete": True,
                                "exam_complete": True,
                                "final_report": final_report_payload,
                            }
                        )
                        return
                    self._send_json({"error": "No active JIT section session"}, 409)
                    return

                current_question = active_section.current_question_payload or {}
                expected_question_id = str(current_question.get("question_id") or "")
                if expected_question_id and str(question_id) != expected_question_id:
                    self._send_json(
                        {
                            "error": "question_id_mismatch",
                            "expected_question_id": expected_question_id,
                        },
                        409,
                    )
                    return

                if not active_section.jit_session_id:
                    try:
                        _start_jit_section_if_needed(db, active_section, int(candidate_id))
                    except Exception as exc:
                        self._send_json(
                            {
                                "error": "jit_section_start_failed",
                                "detail": str(exc),
                            },
                            502,
                        )
                        return
                    current_question = active_section.current_question_payload or {}

                answer_for_jit = selected_opt
                # Track submitted language so JIT evaluator uses the correct runner.
                submitted_language = "python"
                if isinstance(answer_for_jit, str):
                    stripped = answer_for_jit.strip()
                    if stripped.startswith("[") and stripped.endswith("]"):
                        try:
                            parsed_answer = json.loads(stripped)
                            if isinstance(parsed_answer, list):
                                answer_for_jit = parsed_answer
                        except json.JSONDecodeError:
                            pass
                    elif stripped.startswith("{") and stripped.endswith("}"):
                        try:
                            parsed_answer = json.loads(stripped)
                            if isinstance(parsed_answer, dict):
                                # Extract language BEFORE overwriting answer_for_jit
                                lang_from_client = str(parsed_answer.get("language") or "").strip().lower()
                                if lang_from_client:
                                    submitted_language = lang_from_client
                                code_text = str(parsed_answer.get("source_code") or "").strip()
                                answer_for_jit = code_text if code_text else stripped
                        except json.JSONDecodeError:
                            pass

                submission_payload = {
                    "session_id": str(active_section.jit_session_id),
                    "question_id": str(question_id),
                    "question_number": int(req_data.get("question_number") or current_question.get("question_number") or 1),
                    "answer": answer_for_jit,
                    "time_taken_seconds": max(0, time_taken_seconds),
                    "confidence": confidence,
                    "language": submitted_language,
                }
                try:
                    jit_result = _jit_post("session/answer", submission_payload)
                except RuntimeError as exc:
                    msg = str(exc)
                    stale_completed = (
                        "HTTP Error 400" in msg
                        and "Session is already 'completed'." in msg
                    )

                    if stale_completed:
                        print(
                            "[SERVER] ⚠ Received stale answer for already completed JIT session. "
                            f"attempt={attempt.attempt_id}, section={active_section.section_id}. "
                            "Advancing to next section if available."
                        )

                        active_section.status = "completed"
                        active_section.current_question_payload = None
                        final_report_payload = _fetch_jit_final_report(active_section.jit_session_id)
                        if (
                            isinstance(final_report_payload, dict)
                            and final_report_payload
                            and hasattr(active_section, "final_report")
                        ):
                            active_section.final_report = final_report_payload

                        next_section = next(
                            (
                                row
                                for row in section_sessions
                                if int(row.section_order) > int(active_section.section_order)
                                and str(row.status or "pending") in {"pending", "active"}
                            ),
                            None,
                        )

                        next_question_payload = None
                        next_section_id = int(active_section.section_id)
                        next_section_title = str(active_section.section_title or "Section")
                        if next_section is not None:
                            try:
                                next_payload_raw = _start_jit_section_if_needed(db, next_section, int(candidate_id))
                            except Exception as start_exc:
                                db.commit()
                                self._send_json(
                                    {
                                        "error": "jit_next_section_start_failed",
                                        "detail": str(start_exc),
                                    },
                                    502,
                                )
                                return

                            next_question_payload = _from_jit_question(
                                next_payload_raw,
                                section_id=int(next_section.section_id),
                                section_title=str(next_section.section_title or "Section"),
                            )
                            next_section_id = int(next_section.section_id)
                            next_section_title = str(next_section.section_title or "Section")

                        db.commit()

                        refreshed_sections = (
                            db.query(JitSectionSession)
                            .filter(JitSectionSession.attempt_id == int(attempt.attempt_id))
                            .all()
                        )
                        exam_complete = all(
                            str(row.status or "pending") == "completed" for row in refreshed_sections
                        )
                        self._send_json(
                            {
                                "status": "saved",
                                "generation_mode": "jit_generator",
                                "section_id": next_section_id,
                                "section_title": next_section_title,
                                "next_question": next_question_payload,
                                "evaluation": {},
                                "adaptive_decision": {},
                                "section_complete": True,
                                "exam_complete": exam_complete,
                                "final_report": final_report_payload,
                            }
                        )
                        return

                    recoverable = (
                        "HTTP Error 400" in msg
                        and (
                            "Session '" in msg and "not found" in msg
                            or "No pending question found" in msg
                        )
                    )
                    if not recoverable:
                        raise

                    print(
                        "[SERVER] ⚠ JIT session state out-of-sync. "
                        f"Reinitializing section session for attempt={attempt.attempt_id}, "
                        f"section={active_section.section_id}."
                    )
                    restarted_question = _start_jit_section_if_needed(
                        db,
                        active_section,
                        int(candidate_id),
                        force_restart=True,
                    )
                    expected_after_restart = str(restarted_question.get("question_id") or "")
                    if expected_after_restart and str(question_id) != expected_after_restart:
                        self._send_json(
                            {
                                "error": "question_id_mismatch_after_jit_resync",
                                "expected_question_id": expected_after_restart,
                            },
                            409,
                        )
                        return

                    submission_payload["session_id"] = str(active_section.jit_session_id)
                    submission_payload["question_number"] = int(
                        restarted_question.get("question_number") or submission_payload["question_number"]
                    )
                    jit_result = _jit_post("session/answer", submission_payload)

                evaluation = jit_result.get("evaluation") or {}
                adaptive_decision = jit_result.get("adaptive_decision") or {}

                score_value = float(evaluation.get("score") or 0.0)
                db.add(
                    JitAnswerEvent(
                        attempt_id=int(attempt.attempt_id),
                        jit_section_session_id=int(active_section.jit_section_session_id),
                        question_id=str(question_id),
                        question_number=int(submission_payload["question_number"]),
                        question_payload=current_question,
                        submitted_answer=str(answer_for_jit),
                        time_taken_seconds=max(0, time_taken_seconds),
                        confidence=confidence,
                        evaluation=evaluation,
                        adaptive_decision=adaptive_decision,
                        score=int(round(score_value * 100.0)),
                        is_correct=str(evaluation.get("status") or "").lower() == "correct",
                    )
                )

                next_question_payload = None
                next_section_id = int(active_section.section_id)
                next_section_title = str(active_section.section_title or "Section")
                session_complete = bool(jit_result.get("session_complete"))

                if session_complete:
                    active_section.status = "completed"
                    active_section.current_question_payload = None
                    final_report_payload = jit_result.get("final_report")
                    if (not isinstance(final_report_payload, dict)) or (not final_report_payload):
                        final_report_payload = _fetch_jit_final_report(active_section.jit_session_id)
                    if (
                        isinstance(final_report_payload, dict)
                        and final_report_payload
                        and hasattr(active_section, "final_report")
                    ):
                        active_section.final_report = final_report_payload

                    next_section = next(
                        (
                            row
                            for row in section_sessions
                            if int(row.section_order) > int(active_section.section_order)
                            and str(row.status or "pending") in {"pending", "active"}
                        ),
                        None,
                    )
                    if next_section is not None:
                        try:
                            next_payload_raw = _start_jit_section_if_needed(db, next_section, int(candidate_id))
                        except Exception as exc:
                            self._send_json(
                                {
                                    "error": "jit_next_section_start_failed",
                                    "detail": str(exc),
                                },
                                502,
                            )
                            return
                        next_question_payload = _from_jit_question(
                            next_payload_raw,
                            section_id=int(next_section.section_id),
                            section_title=str(next_section.section_title or "Section"),
                        )
                        next_section_id = int(next_section.section_id)
                        next_section_title = str(next_section.section_title or "Section")
                    else:
                        next_question_payload = None
                else:
                    next_raw = jit_result.get("next_question") or {}
                    if not isinstance(next_raw, dict) or not next_raw.get("question_id"):
                        self._send_json({"error": "JIT next question missing"}, 502)
                        return
                    active_section.current_question_payload = next_raw
                    active_section.asked_count = max(int(active_section.asked_count or 0), int(next_raw.get("question_number") or 1))
                    next_question_payload = _from_jit_question(
                        next_raw,
                        section_id=int(active_section.section_id),
                        section_title=str(active_section.section_title or "Section"),
                    )

                # Commit with rollback safety to preserve server stability.
                try:
                    db.commit()
                except Exception as commit_err:
                    print(f"[JIT_PERSIST] ERROR: Database commit failed: {commit_err}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    # Keep response path stable for client while logging server-side issue.

                exam_complete = all(str(row.status or "pending") == "completed" for row in section_sessions)

                # Keep response structure stable for existing EXE client contract.
                self._send_json(
                    {
                        "status": "saved",
                        "generation_mode": "jit_generator",
                        "section_id": next_section_id,
                        "section_title": next_section_title,
                        "next_question": next_question_payload,
                        "evaluation": evaluation,
                        "adaptive_decision": adaptive_decision,
                        "section_complete": session_complete,
                        "exam_complete": exam_complete,
                        "final_report": final_report_payload if session_complete else None,
                    }
                )
                return

            # For variant questions, question_id is variant_id — map it back to
            # source_question_id so the answers table FK is satisfied.
            resolved_question_id = int(question_id)
            variant_row = db.query(LLMQuestionVariant).filter(
                LLMQuestionVariant.variant_id == resolved_question_id,
            ).first()
            if variant_row:
                resolved_question_id = variant_row.source_question_id

            _upsert_answer(db, int(attempt_id), resolved_question_id, selected_opt)

            # Non-JIT progression payload for server-driven UIs (e.g., llm_morphing flow).
            sections_db = (
                db.query(ExamSection)
                .filter(ExamSection.drive_id == int(drive.drive_id))
                .order_by(ExamSection.order_index)
                .all()
            )

            gen_mode = str(getattr(drive, "generation_mode", "static") or "static").lower()
            is_morphing_exam = _is_morphing_mode(gen_mode)
            has_any_variants = (
                db.query(LLMQuestionVariant)
                .filter(
                    LLMQuestionVariant.candidate_id == int(candidate_id),
                    LLMQuestionVariant.exam_id == int(drive.drive_id),
                )
                .first()
            ) is not None
            use_variants = is_morphing_exam or has_any_variants

            ordered_questions: list[dict] = []
            for sec in sections_db:
                if use_variants:
                    variant_rows, _variant_mode = _get_effective_variants_for_section(
                        db=db,
                        candidate_id=int(candidate_id),
                        drive_id=int(drive.drive_id),
                        section_id=int(sec.section_id),
                    )
                    if variant_rows:
                        payloads = [_question_from_variant(v, int(sec.section_id)) for v in variant_rows]
                    else:
                        if is_morphing_exam:
                            self._send_json(
                                {
                                    "error": "morphed_questions_missing",
                                    "detail": f"No LLM morphed variants found for section {sec.section_id}",
                                    "exam_id": int(drive.drive_id),
                                    "section_id": int(sec.section_id),
                                },
                                409,
                            )
                            return

                        rows = (
                            db.query(Question)
                            .filter(
                                Question.drive_id == int(drive.drive_id),
                                Question.section_id == int(sec.section_id),
                            )
                            .order_by(Question.question_id)
                            .all()
                        )
                        payloads = [_question_from_db(q, int(sec.section_id)) for q in rows]
                else:
                    rows = (
                        db.query(Question)
                        .filter(
                            Question.drive_id == int(drive.drive_id),
                            Question.section_id == int(sec.section_id),
                        )
                        .order_by(Question.question_id)
                        .all()
                    )
                    payloads = [_question_from_db(q, int(sec.section_id)) for q in rows]

                for p in payloads:
                    p["_section_title"] = str(sec.title or "Section")
                    ordered_questions.append(p)

            current_raw_id = str(question_id).strip()
            resolved_raw_id = str(resolved_question_id).strip()
            current_idx = -1
            for idx, p in enumerate(ordered_questions):
                pid = str(p.get("id") or "").strip()
                psid = str(p.get("source_question_id") or "").strip()
                if pid == current_raw_id or pid == resolved_raw_id or psid == resolved_raw_id:
                    current_idx = idx
                    break

            next_question_payload = None
            section_complete = False
            exam_complete = False
            next_section_id = None
            next_section_title = ""

            if ordered_questions:
                answered_rows = (
                    db.query(Answer.question_id)
                    .filter(Answer.attempt_id == int(attempt_id))
                    .all()
                )
                answered_ids = {str(row[0]) for row in answered_rows if row and row[0] is not None}

                if 0 <= current_idx < len(ordered_questions) - 1:
                    next_question_payload = ordered_questions[current_idx + 1]
                elif current_idx == len(ordered_questions) - 1:
                    next_question_payload = None
                else:
                    # Fallback when ids cannot be matched reliably in payload.
                    for p in ordered_questions:
                        pid = str(p.get("id") or "")
                        psid = str(p.get("source_question_id") or "")
                        if pid not in answered_ids and psid not in answered_ids:
                            next_question_payload = p
                            break

                if next_question_payload is not None:
                    next_section_id = next_question_payload.get("section_id")
                    next_section_title = str(next_question_payload.get("_section_title") or "Section")
                    current_section_id = ordered_questions[current_idx].get("section_id") if current_idx >= 0 else None
                    section_complete = (current_section_id is not None) and (current_section_id != next_section_id)
                else:
                    exam_complete = True
                    section_complete = True

            self._send_json(
                {
                    "status": "saved",
                    "generation_mode": str(generation_mode or "static").lower(),
                    "question_id": resolved_question_id,
                    "next_question": next_question_payload,
                    "section_id": next_section_id,
                    "section_title": next_section_title,
                    "section_complete": bool(section_complete),
                    "exam_complete": bool(exam_complete),
                }
            )

        except Exception as exc:
            print(f"[SERVER] ❌ Answer save error: {exc}")
            self._send_json({"error": "Internal server error saving answer"}, 500)
        finally:
            db.close()

    def _handle_exam_submit(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/submit
        Finalises the exam attempt: persists any remaining answers, closes the
        attempt, and marks it as submitted.

        All existing HMAC + session binding checks are still enforced.
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "Invalid signature"}, 401)
            return

        session_nonce = (req_data.get("session_nonce") or "").strip()
        if not session_nonce:
            self._send_json({"error": "Missing session_nonce"}, 400)
            return

        session = self._session_gate(session_nonce)
        if session is None:
            return

        submit_fp  = req_data.get("hardware_fingerprint", "")
        session_fp = session.get("hardware_fingerprint", "")
        if session_fp and submit_fp:
            if not hmac.compare_digest(submit_fp, session_fp):
                self._send_json({"error": "Hardware fingerprint mismatch"}, 403)
                return

        submitter_ip = self._request_ip()
        if session.get("ip") and not _ip_matches(session.get("ip", ""), submitter_ip):
            self._send_json({"error": "IP mismatch"}, 403)
            return

        login_token = (session.get("login_token") or "").strip()
        session_email = (session.get("email") or "").strip().lower()
        if not login_token or not session_email:
            self._send_json({"error": "invalid_session_context"}, 403)
            return

        ok, reason = self._check_login_session(
            login_token,
            session_email,
            submitter_ip,
            require_active_user=True,
        )
        if not ok:
            self._send_json({"error": reason}, 403)
            return

        answers    = req_data.get("answers", {})
        attempt_id = req_data.get("attempt_id")
        total      = req_data.get("total_questions", len(answers))
        duration   = req_data.get("session_duration_seconds", 0)
        timestamp  = req_data.get("submitted_at", "?")
        email      = session.get("email", "")

        print("\n" + "=" * 60)
        print("[SERVER] *** EXAM SUBMISSION RECEIVED ***")
        print(f"[SERVER] Session   : {session_nonce[:16]}...")
        print(f"[SERVER] Timestamp : {timestamp}")
        print(f"[SERVER] Answered  : {len(answers)}/{total}")
        print(f"[SERVER] Duration  : {duration // 60}m {duration % 60}s")
        print("=" * 60)

        # Persist to DB if attempt_id and email are known
        if attempt_id and email:
            db = next(get_db())
            try:
                login_token = session.get("login_token", "")
                login_sess  = _get_login_session_snapshot(login_token) or {}
                candidate_id = login_sess.get("candidate_id")

                if candidate_id:
                    attempt = db.query(ExamAttempt).filter(
                        ExamAttempt.attempt_id == int(attempt_id),
                        ExamAttempt.candidate_id == candidate_id,
                    ).first()

                    if attempt and attempt.status == "started":
                        # Persist any answers sent in the submit payload
                        for q_id_str, ans_val in answers.items():
                            try:
                                q_id = int(q_id_str)
                                # Resolve variant → source question
                                variant = db.query(LLMQuestionVariant).filter(
                                    LLMQuestionVariant.variant_id == q_id
                                ).first()
                                resolved = variant.source_question_id if variant else q_id
                                _upsert_answer(db, int(attempt_id), resolved, str(ans_val))
                            except (ValueError, TypeError):
                                continue

                        attempt.status   = "submitted"
                        attempt.end_time = datetime.now(timezone.utc)
                        db.commit()
                        print(f"[SERVER] ✔ Attempt {attempt_id} marked submitted in DB")

            except Exception as exc:
                print(f"[SERVER] ❌ Submit DB error: {exc}")
            finally:
                db.close()

        login_snapshot = _get_login_session_snapshot(login_token) or {}
        report_launch_code = str(login_snapshot.get("exam_launch_code") or req_data.get("exam_launch_code") or "").strip().upper()
        if report_launch_code:
            # Trigger report ingest in background (non-blocking)
            _trigger_report_ingest_async(email=email, launch_code=report_launch_code)
        else:
            print("[SERVER] ⚠ Report ingest skipped: launch code missing in session context")

        _update_session(session_nonce, "state", "submitted")
        self._send_json({"status": "submitted"})

    def _handle_exam_coding_run(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/coding/run
        
        Proxy code execution to proctored-code-env backend.
        EXE calls this to test code during the exam.
        
        Request: {
            email, login_token, attempt_id, question_id,
            language (python|javascript|java|cpp|go|rust),
            source_code,
            stdin (optional test input)
        }
        
        Response: {
            stdout, stderr, exit_code, execution_time_ms, memory_used_kb,
            timed_out, public_test_results
        }
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        email = (req_data.get("email") or "").strip().lower()
        login_token = (req_data.get("login_token") or "").strip()
        ip = self._request_ip()

        ok, reason = self._check_login_session(login_token, email, ip, require_active_user=True)
        if not ok:
            self._send_json({"error": reason}, 403)
            return

        language = _normalize_coding_language(req_data.get("language", ""))
        source_code = str(req_data.get("source_code", "") or "")
        stdin = str(req_data.get("stdin", "") or "")
        question_id = _coerce_question_id(req_data.get("question_id"))
        attempt_id = req_data.get("attempt_id")

        if not language or not source_code:
            self._send_json({"error": "language and source_code required"}, 400)
            return

        # Verify attempt ownership before calling execution backend.
        login_sess = _get_login_session_snapshot(login_token) or {}
        candidate_id = login_sess.get("candidate_id")
        if not candidate_id:
            self._send_json({"error": "candidate_context_missing"}, 403)
            return

        if attempt_id not in (None, ""):
            try:
                attempt_id_int = int(attempt_id)
            except Exception:
                self._send_json({"error": "attempt_id must be an integer"}, 400)
                return

            db = next(get_db())
            try:
                attempt = db.query(ExamAttempt).filter(
                    ExamAttempt.attempt_id == attempt_id_int,
                    ExamAttempt.candidate_id == int(candidate_id),
                ).first()
                if not attempt:
                    self._send_json({"error": "attempt_not_found_or_unauthorized"}, 403)
                    return
            finally:
                db.close()

        # Call proctored-code-env backend via HTTP
        backend_url = os.getenv("CODING_BACKEND_URL", "http://localhost:8001").rstrip("/")
        internal_secret = os.getenv("VIRTUSA_INTERNAL_SECRET", "").strip()
        verify_tls = os.getenv("CODING_BACKEND_VERIFY_TLS", "1").lower() in ("1", "true", "yes", "on")
        
        if not backend_url or backend_url == "http://localhost:8001":
            print("[SERVER] ⚠️  CODING_BACKEND_URL not configured, using default localhost:8001")

        try:
            # Make HTTP call to backend (fallback to /internal/run for compatibility)
            import requests
            payload = {
                "language": language,
                "source_code": source_code,
                "stdin": stdin,
                "question_id": question_id,
            }
            headers = {
                "X-Virtusa-Secret": internal_secret,
                "X-Forwarded-For": ip,
                "Content-Type": "application/json",
            }

            last_http_error = None
            response = None
            for run_path in ("/api/v1/execute/run", "/api/v1/execute/internal/run"):
                try:
                    response = requests.post(
                        f"{backend_url}{run_path}",
                        json=payload,
                        headers=headers,
                        timeout=45,  # 10s execution + overhead
                        verify=verify_tls,
                    )
                    response.raise_for_status()
                    break
                except requests.HTTPError as http_err:
                    last_http_error = http_err
                    status_code = getattr(getattr(http_err, "response", None), "status_code", None)
                    body_preview = getattr(getattr(http_err, "response", None), "text", "") or ""
                    print(
                        f"[SERVER] ⚠ Coding backend HTTP error on {run_path}: "
                        f"status={status_code} body={body_preview[:500]}"
                    )
                    # Retry only for endpoint-not-found and method-not-allowed style compatibility cases.
                    if status_code in (404, 405):
                        continue
                    raise

            if response is None:
                if last_http_error:
                    raise last_http_error
                raise RuntimeError("No response from coding backend")

            result = response.json()

            # Persist run activity for audit/history in code_submissions.
            try:
                login_sess = _get_login_session_snapshot(login_token) or {}
                candidate_id = login_sess.get("candidate_id")
                resolved_attempt_id = int(attempt_id) if attempt_id is not None else None

                db = next(get_db())
                try:
                    if candidate_id and resolved_attempt_id is None:
                        latest_attempt = (
                            db.query(ExamAttempt)
                            .filter(
                                ExamAttempt.candidate_id == int(candidate_id),
                                ExamAttempt.status == "started",
                            )
                            .order_by(ExamAttempt.attempt_id.desc())
                            .first()
                        )
                        if latest_attempt is not None:
                            resolved_attempt_id = int(latest_attempt.attempt_id)

                    resolved_question_id = int(question_id) if str(question_id).strip().isdigit() else None
                    if resolved_question_id is not None:
                        variant_row = db.query(LLMQuestionVariant).filter(
                            LLMQuestionVariant.variant_id == resolved_question_id,
                        ).first()
                        if variant_row:
                            resolved_question_id = int(variant_row.source_question_id)

                    if candidate_id and resolved_attempt_id is not None and resolved_question_id is not None:
                        run_row = CodeSubmission(
                            attempt_id=int(resolved_attempt_id),
                            question_id=int(resolved_question_id),
                            candidate_id=int(candidate_id),
                            language=language,
                            source_code=source_code,
                            status="run",
                            test_results=result.get("public_test_results") or [],
                            passed_test_cases=sum(
                                1
                                for item in (result.get("public_test_results") or [])
                                if isinstance(item, dict) and item.get("passed")
                            ),
                            total_test_cases=len(result.get("public_test_results") or []),
                            execution_time_ms=result.get("execution_time_ms"),
                            memory_used_kb=result.get("memory_used_kb"),
                            stdout=result.get("stdout") or "",
                            stderr=result.get("stderr") or "",
                            is_final=False,
                            executed_at=datetime.now(timezone.utc),
                        )
                        db.add(run_row)
                        db.commit()
                finally:
                    db.close()
            except Exception as persist_exc:
                print(f"[SERVER] ⚠ Unable to persist code run row: {persist_exc}")
            
            print(f"[SERVER] ✓ Code executed: {language}, exit={result.get('exit_code')}, "
                  f"time={result.get('execution_time_ms')}ms")
            self._send_json(result)
            
        except Exception as e:
            response_body = ""
            status_code = None
            upstream_detail = None
            try:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                response_body = getattr(getattr(e, "response", None), "text", "") or ""
                parsed = getattr(e, "response", None)
                if parsed is not None:
                    try:
                        upstream_detail = parsed.json()
                    except Exception:
                        upstream_detail = None
            except Exception:
                pass
            if status_code is not None:
                print(f"[SERVER] ❌ Execution error: status={status_code} error={e}")
            else:
                print(f"[SERVER] ❌ Execution error: {e}")
            if response_body:
                print(f"[SERVER] ❌ Backend response body: {response_body[:1000]}")
            error_payload = {
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "execution_time_ms": 0,
                "memory_used_kb": 0,
                "timed_out": False,
            }
            if response_body:
                error_payload["backend_response_preview"] = response_body[:1000]
            if upstream_detail is not None:
                error_payload["backend_error"] = upstream_detail

            # Preserve upstream HTTP status when available so clients see the real failure.
            self._send_json(error_payload, int(status_code) if status_code else 503)

    def _handle_exam_submit_coding(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/coding/submit
        
        Save final code submission after user clicks submit or exam ends.
        Stores to code_submissions table with complete submission metadata.
        
        Request: {
            email, login_token,
            attempt_id, question_id,
            language, source_code,
            test_results (optional: from last run),
            execution_time_ms (optional),
            memory_used_kb (optional),
            stdout, stderr (optional)
        }
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "invalid_signature"}, 401)
            return

        email = (req_data.get("email") or "").strip().lower()
        login_token = (req_data.get("login_token") or "").strip()
        ip = self._request_ip()

        ok, reason = self._check_login_session(login_token, email, ip)
        if not ok:
            self._send_json({"error": reason}, 403)
            return

        attempt_id = req_data.get("attempt_id")
        question_id = _coerce_question_id(req_data.get("question_id"))
        language = req_data.get("language", "").lower()
        source_code = req_data.get("source_code", "")

        if not all([question_id, language, source_code]):
            self._send_json({"error": "Missing required fields: question_id, language, source_code"}, 400)
            return

        db = next(get_db())
        try:
            login_sess = _get_login_session_snapshot(login_token)
            if not login_sess:
                self._send_json({"error": "invalid_login_token"}, 403)
                return
            candidate_id = login_sess.get("candidate_id")

            resolved_attempt_id = int(attempt_id) if attempt_id is not None else None
            if resolved_attempt_id is None:
                latest_attempt = (
                    db.query(ExamAttempt)
                    .filter(
                        ExamAttempt.candidate_id == int(candidate_id),
                        ExamAttempt.status == "started",
                    )
                    .order_by(ExamAttempt.attempt_id.desc())
                    .first()
                )
                if latest_attempt is not None:
                    resolved_attempt_id = int(latest_attempt.attempt_id)

            if resolved_attempt_id is None:
                self._send_json({"error": "No active attempt found for candidate"}, 400)
                return

            # Verify attempt exists and belongs to this candidate
            attempt = db.query(ExamAttempt).filter(
                ExamAttempt.attempt_id == int(resolved_attempt_id),
                ExamAttempt.candidate_id == int(candidate_id),
            ).first()

            if not attempt:
                self._send_json({"error": "Attempt not found or unauthorized"}, 404)
                return

            resolved_question_id = int(question_id) if isinstance(question_id, int) else None
            if resolved_question_id is None:
                # JIT question IDs are string tokens (e.g. jit-...); accept submit even when
                # we cannot store a FK-backed code_submissions row.
                self._send_json(
                    {
                        "status": "accepted",
                        "submission_id": None,
                        "question_id": str(question_id),
                        "persisted": False,
                    },
                    202,
                )
                return
            variant_row = db.query(LLMQuestionVariant).filter(
                LLMQuestionVariant.variant_id == resolved_question_id,
            ).first()
            if variant_row:
                resolved_question_id = int(variant_row.source_question_id)

            # Create CodeSubmission record
            submission = CodeSubmission(
                attempt_id=int(resolved_attempt_id),
                question_id=int(resolved_question_id),
                candidate_id=int(candidate_id),
                language=language,
                source_code=source_code,
                status="submitted",
                submitted_at=datetime.now(timezone.utc),
            )
            
            # Optional: Include test results and metrics if provided
            if req_data.get("test_results"):
                submission.test_results = req_data.get("test_results", [])
                submission.passed_test_cases = sum(1 for r in submission.test_results if r.get("passed"))
                submission.total_test_cases = len(submission.test_results)
            
            if req_data.get("execution_time_ms") is not None:
                submission.execution_time_ms = int(req_data.get("execution_time_ms"))
            if req_data.get("memory_used_kb") is not None:
                submission.memory_used_kb = int(req_data.get("memory_used_kb"))
            if req_data.get("stdout"):
                submission.stdout = req_data.get("stdout")
            if req_data.get("stderr"):
                submission.stderr = req_data.get("stderr")

            db.add(submission)
            db.commit()
            db.refresh(submission)

            print(f"[SERVER] ✓ Code submission saved: id={submission.submission_id}, "
                  f"lang={language}, size={len(source_code)}")

            self._send_json({
                "status": "saved",
                "submission_id": submission.submission_id,
                "question_id": int(resolved_question_id)
            }, 201)

        except Exception as e:
            db.rollback()
            print(f"[SERVER] ❌ Coding submit error: {e}")
            self._send_json({"error": str(e)}, 500)
        finally:
            db.close()

    def _handle_exam_logs(self, req_data: dict, raw_body: bytes):
        """
        POST /v1/exam/logs
        Receives EXE runtime log content and optional process snapshot after exam submission.
        Saves locally and uploads best-effort copies to Supabase when configured.
        """
        if not self._verify_signature(raw_body):
            self._send_json({"error": "Invalid signature"}, 401)
            return

        session_nonce = (req_data.get("session_nonce") or "").strip()
        submitter_ip = self._request_ip()
        session = None
        auth_mode = "login_fallback"

        if session_nonce:
            candidate_session = _get_session(session_nonce)
            if candidate_session is not None:
                if candidate_session.get("ip") and not _ip_matches(candidate_session.get("ip", ""), submitter_ip):
                    self._send_json({"error": "IP mismatch"}, 403)
                    return
                session = candidate_session
                auth_mode = "nonce"

        if session is None:
            email = (req_data.get("email") or "").strip().lower()
            login_token = (req_data.get("login_token") or "").strip()
            if not email or not login_token:
                self._send_json({"error": "Missing auth context (session_nonce or email/login_token)"}, 400)
                return
            ok, reason = self._check_login_session(login_token, email, submitter_ip)
            if not ok:
                self._send_json({"error": reason}, 403)
                return
            session = {
                "email": email,
                "login_token": login_token,
                "ip": submitter_ip,
                "hardware_fingerprint": "",
            }

        submit_fp = req_data.get("hardware_fingerprint", "")
        session_fp = session.get("hardware_fingerprint", "")
        if session_fp and submit_fp and not hmac.compare_digest(submit_fp, session_fp):
            self._send_json({"error": "Hardware fingerprint mismatch"}, 403)
            return

        email = str(session.get("email") or req_data.get("email") or "unknown").strip().lower()
        log_text = str(req_data.get("log_text") or "")
        process_snapshot = req_data.get("process_snapshot") or {}
        attempt_id = req_data.get("attempt_id")
        upload_reason = str(req_data.get("upload_reason") or "finalize")
        ts = datetime.now(timezone.utc)

        safe_nonce = session_nonce[:16]
        safe_attempt = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(attempt_id or "unknown"))[:32]
        stem = f"attempt_{safe_attempt}_{safe_nonce or 'no_nonce'}_{ts.strftime('%Y%m%d_%H%M%S')}"

        log_file = CLIENT_LOGS_DIR / f"{stem}.log"
        process_file = CLIENT_LOGS_DIR / f"{stem}.process.json"

        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(log_text)
            with open(process_file, "w", encoding="utf-8") as f:
                json.dump(process_snapshot, f, ensure_ascii=True, indent=2, default=str)
        except Exception as exc:
            print(f"[SERVER] ❌ Failed to persist client logs: {exc}")
            self._send_json({"error": "Failed to persist client logs"}, 500)
            return

        log_bytes_count = len(log_text.encode("utf-8", errors="ignore"))
        supabase_enabled = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
        sb_log_path = None
        sb_process_path = None
        sb_meta_path = None

        if supabase_enabled:
            email_safe = email.replace("@", "_at_").replace("/", "_").replace("\\", "_")
            attempt_safe = str(attempt_id or "unknown")
            ts_str = ts.strftime("%Y%m%d_%H%M%S")
            sb_base = f"{email_safe}/{attempt_safe}/{ts_str}"

            log_bytes = log_text.encode("utf-8", errors="replace")
            sb_log_path = f"{sb_base}/exam.log"
            if not _supabase_upload(sb_log_path, log_bytes, "text/plain", bucket=EXAM_LOGS_BUCKET):
                sb_log_path = None

            proc_bytes = json.dumps(process_snapshot, ensure_ascii=True, indent=2, default=str).encode("utf-8")
            sb_process_path = f"{sb_base}/process.json"
            if not _supabase_upload(sb_process_path, proc_bytes, "application/json", bucket=EXAM_LOGS_BUCKET):
                sb_process_path = None

            metadata = {
                "email": email,
                "attempt_id": attempt_id,
                "session_nonce": session_nonce or "",
                "upload_reason": upload_reason,
                "auth_mode": auth_mode,
                "log_bytes": log_bytes_count,
                "stored_at": ts.isoformat(),
                "local_log": str(log_file.name),
                "local_process": str(process_file.name),
                "supabase_log": sb_log_path,
                "supabase_process": sb_process_path,
            }
            meta_bytes = json.dumps(metadata, indent=2, default=str).encode("utf-8")
            sb_meta_path = f"{sb_base}/metadata.json"
            if not _supabase_upload(sb_meta_path, meta_bytes, "application/json", bucket=EXAM_LOGS_BUCKET):
                sb_meta_path = None

        print(
            f"[SERVER] ✔ Client logs stored: {log_file.name}, {process_file.name} "
            f"(attempt={safe_attempt}, mode={auth_mode}, reason={upload_reason}, bytes={log_bytes_count})"
        )
        self._send_json({
            "status": "stored",
            "log_file": str(log_file.name),
            "process_file": str(process_file.name),
            "supabase_log": sb_log_path,
            "supabase_process": sb_process_path,
            "supabase_meta": sb_meta_path,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Server entry point
# ─────────────────────────────────────────────────────────────────────────────

def start_server(port: int, use_tls: bool = False, require_tls: bool = False):
    # Cert files are placed next to this script so the server folder is portable
    cert_file = str(_SERVER_DIR / "server.crt")
    key_file  = str(_SERVER_DIR / "server.key")

    protocol       = "HTTPS" if use_tls else "HTTP"
    certs_available = False

    if use_tls:
        certs_available = _create_self_signed_cert(cert_file, key_file)
        if not certs_available:
            if require_tls and not TRUST_PROXY_TLS:
                raise RuntimeError("TLS certificate unavailable and VIRTUSA_REQUIRE_TLS is enabled.")
            print("[SERVER] TLS certificate unavailable, falling back to HTTP.")
            use_tls  = False
            protocol = "HTTP"

    if require_tls and not use_tls and TRUST_PROXY_TLS:
        protocol = "HTTP (TLS terminated by trusted proxy)"

    if use_tls and certs_available:
        server = HTTPSServer(("0.0.0.0", port), ProctorHandler, cert_file, key_file)
    else:
        server = ThreadedHTTPServer(("0.0.0.0", port), ProctorHandler)

    cleanup_stop_event = threading.Event()
    cleanup_thread = threading.Thread(
        target=_session_cleanup_worker,
        args=(cleanup_stop_event,),
        name="session-cleanup-worker",
        daemon=True,
    )
    cleanup_thread.start()

    print("\n" + "=" * 80)
    print("  Virtusa ObserveProctor - Secure Mock Backend (DB-backed)")
    print("=" * 80)
    print(f"  Mode              : {protocol}")
    display_url = f"http://localhost:{port}" if "HTTP" in protocol else f"https://localhost:{port}"
    print(f"  URL               : {display_url}")
    print(f"  Nonce TTL         : {NONCE_TTL_SECONDS // 60} minutes")
    print(f"  Rate limit        : {RATE_LIMIT_COUNT} nonces / {RATE_LIMIT_WINDOW}s per IP")
    print(f"  Session cap       : {MAX_SESSIONS:,}")
    print(f"  Max workers       : {REQUEST_MAX_WORKERS}")
    print(f"  Request queue     : {REQUEST_QUEUE_SIZE}")
    print(f"  Request timeout   : {REQUEST_HANDLER_TIMEOUT_SECONDS:.1f}s")
    print(f"  Cleanup interval  : {SESSION_CLEANUP_INTERVAL_SECONDS}s")
    print(f"  Rate-limit IPs    : {MAX_RATE_IPS:,} (LRU eviction)")
    print(f"  Enrollment        : {'STRICT (reject unknown)' if _STRICT_ENROLLMENT else 'AUTO'}")
    print(f"  IP binding mode   : {IP_BINDING_MODE}")
    db_status = "✔ connected" if ping_db() else "✖ unreachable (check DATABASE_URL)"
    print(f"  Neon DB           : {db_status}")
    print("  Endpoints:")
    print("    GET  /health")
    print("    POST /v1/auth/login")
    print("    POST /v1/session/nonce")
    print("    POST /v1/telemetry")
    print("    POST /v1/evidence")
    print("    POST /v1/exam/bootstrap")
    print("    POST /v1/exam/answer")
    print("    POST /v1/exam/submit")
    print("    POST /v1/exam/logs")
    print("  Env               : VIRTUSA_PROCTOR_SECRET  DATABASE_URL  SERVER_PORT")
    print("[SERVER] Press Ctrl+C to stop\n")

    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        test_url = f"{SUPABASE_URL}/storage/v1/bucket"
        test_req = urllib_request.Request(
            url=test_url,
            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
            method="GET",
        )
        try:
            with urllib_request.urlopen(test_req, timeout=5) as resp:
                buckets = json.loads(resp.read().decode("utf-8"))
                bucket_names = [b.get("name") for b in buckets if isinstance(b, dict)]
                ev_ok = EVIDENCE_BUCKET in bucket_names
                logs_ok = EXAM_LOGS_BUCKET in bucket_names
                print("  Supabase         : ✔ connected")
                print(f"  Evidence bucket  : {'✔ ' + EVIDENCE_BUCKET if ev_ok else '❌ NOT FOUND'}")
                print(f"  Exam logs bucket : {'✔ ' + EXAM_LOGS_BUCKET if logs_ok else '❌ NOT FOUND'}")
        except Exception as sb_exc:
            print(f"  Supabase         : ⚠ could not verify - {sb_exc}")
    else:
        print("  Supabase         : ✗ not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        cleanup_stop_event.set()
        server.shutdown()
        server.server_close()
        cleanup_thread.join(timeout=2.0)
        print("[SERVER] Server stopped")


if __name__ == "__main__":
    require_tls = os.environ.get("VIRTUSA_REQUIRE_TLS", "1").lower() in ("1", "true", "yes", "on")
    use_tls = os.environ.get("VIRTUSA_TLS", "1").lower() in ("1", "true", "yes")
    if require_tls and not use_tls and not TRUST_PROXY_TLS:
        raise RuntimeError("TLS is required in production. Set VIRTUSA_TLS=1 or disable VIRTUSA_REQUIRE_TLS explicitly.")
    start_server(port=PORT, use_tls=use_tls, require_tls=require_tls)