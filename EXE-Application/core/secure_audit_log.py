"""
Tamper-evident audit logging with an HMAC chain.

Each record is stored as a JSON line containing timestamp, level, module,
message, previous MAC, and current MAC.

The chain allows verification to detect deleted, modified, or tampered
entries between writes and submission.

On Windows, the MAC key is persisted as a DPAPI-protected secret. A portable
random-key fallback is used when DPAPI is unavailable. Legacy key validation
is retained for backward verification of older log files.
"""

import hashlib
import hmac
import json
import os
import platform
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Optional

if platform.system() == "Windows":
    import winreg
else:
    winreg = None  # type: ignore


# Key-management helpers

def _dpapi_key_path() -> str:
    """Return path to the DPAPI-protected audit log key file."""
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(base, "ObserveProctor", "audit_key.dpapi")


def _portable_key_path() -> str:
    """Return path for non-DPAPI random MAC key fallback."""
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(base, "ObserveProctor", "audit_key.bin")


def _load_or_create_dpapi_key() -> Optional[bytes]:
    """
    Load existing DPAPI-protected MAC key or create one on first run.

    Returns None when DPAPI support is unavailable.
    """
    if platform.system() != "Windows":
        return None

    try:
        from .dpapi_secrets import protect, unprotect
    except Exception:
        return None

    key_path = _dpapi_key_path()
    try:
        if os.path.isfile(key_path):
            with open(key_path, "rb") as f:
                blob = f.read()
            return unprotect(blob)
        else:
            # First run: generate random key, protect it, and persist to disk.
            key = os.urandom(32)
            blob = protect(key)
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(blob)
            print(f"[AuditLog] DPAPI-protected MAC key created: {key_path}")
            return key
    except Exception as e:
        print(f"[AuditLog] DPAPI key load/create failed ({e}) — using portable random key.")
        return None


def _load_or_create_portable_key() -> Optional[bytes]:
    """
    Load or create a random local MAC key when DPAPI is unavailable.

    This fallback still avoids machine-derivable key material.
    """
    key_path = _portable_key_path()
    try:
        if os.path.isfile(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
            if len(key) == 32:
                return key

        key = os.urandom(32)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
        print(f"[AuditLog] Portable MAC key created: {key_path}")
        return key
    except Exception as e:
        print(f"[AuditLog] Portable key load/create failed ({e}).")
        return None


def _mac_key_legacy() -> bytes:
    """Build legacy machine-derived key for backward log verification only."""
    parts = []
    if winreg is not None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            ) as k:
                guid, _ = winreg.QueryValueEx(k, "MachineGuid")
                parts.append(str(guid))
        except Exception:
            pass
    try:
        parts.append(socket.gethostname())
    except Exception:
        pass
    try:
        parts.append(platform.processor())
    except Exception:
        pass
    raw = "|".join(parts).encode("utf-8")
    machine_fp = hashlib.sha256(raw).digest()
    return hmac.new(machine_fp, b"observe_audit_log_chain_key_v2", hashlib.sha256).digest()


_dpapi_key = _load_or_create_dpapi_key()
_portable_key = _load_or_create_portable_key() if _dpapi_key is None else None
_LOG_KEY = _dpapi_key or _portable_key or os.urandom(32)
_legacy_key_cached = _mac_key_legacy()
_LEGACY_KEY = _legacy_key_cached   # Backward-compatibility verification key.
_ZERO_MAC    = "0" * 64   # Chain root for first entry.


def _compute_mac(prev_mac: str, timestamp: str, message: str) -> str:
    msg = (prev_mac + timestamp + message).encode("utf-8")
    return hmac.new(_LOG_KEY, msg, hashlib.sha256).hexdigest()


def _compute_mac_with_key(key: bytes, prev_mac: str, timestamp: str, message: str) -> str:
    msg = (prev_mac + timestamp + message).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


class SecureAuditLog:
    """
    Append-only HMAC-chained log writer and verifier.

    Writes are protected with a lock so concurrent log events preserve
    deterministic chain ordering.
    """

    def __init__(self, log_path: str):
        self._path    = log_path
        self._lock    = threading.Lock()
        self._prev_mac: str = self._read_last_mac()

    def _read_last_mac(self) -> str:
        """Read the MAC of the last existing entry to continue the chain."""
        if not os.path.isfile(self._path):
            return _ZERO_MAC
        try:
            with open(self._path, "rb") as f:
                # Use final non-empty record to resume chain correctly.
                lines = f.read().strip().splitlines()
            for line in reversed(lines):
                try:
                    entry = json.loads(line.decode("utf-8"))
                    mac = entry.get("mac", "")
                    if mac:
                        return mac
                except Exception:
                    continue
        except Exception:
            pass
        return _ZERO_MAC

    def append(self, level: str, module: str, message: str,
                telemetry: Optional[dict] = None) -> None:
        """Append a tamper-evident entry to the log, including MAC chain."""
        with self._lock:
            try:
                ts = datetime.now(timezone.utc).isoformat()
                prev_mac = self._prev_mac
                mac = _compute_mac(prev_mac, ts, message)

                entry: dict = {
                    "timestamp": ts,
                    "level":     level,
                    "module":    module,
                    "message":   message,
                    "prev_mac":  prev_mac,
                    "mac":       mac,
                }
                if telemetry:
                    entry["telemetry"] = telemetry

                line = json.dumps(entry, default=str) + "\n"
                log_dir = os.path.dirname(self._path)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line)
                self._prev_mac = mac
            except Exception as e:
                print(f"[AuditLog] Write failed: {e}")

    def verify_chain(self) -> tuple[bool, str]:
        """
        Verify the integrity of the entire log chain.
        Returns (True, "OK") or (False, "reason").

        Tries both current and legacy keys so older pre-migration records
        continue to verify during transition periods.
        """
        if not os.path.isfile(self._path):
            return True, "No log file yet."

        prev = _ZERO_MAC
        try:
            with self._lock:
                with open(self._path, "rb") as f:
                    lines = f.read().strip().splitlines()
        except Exception as e:
            return False, f"Cannot read log: {e}"

        for i, raw in enumerate(lines, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw.decode("utf-8"))
            except Exception:
                return False, f"Line {i}: JSON parse error."

            stored_prev = entry.get("prev_mac", "")
            stored_mac  = entry.get("mac", "")
            ts          = entry.get("timestamp", "")
            msg         = entry.get("message", "")

            if not hmac.compare_digest(stored_prev, prev):
                return False, f"Line {i}: prev_mac chain break (deletion detected)."

            # Validate with current key first, then legacy key for old entries.
            expected = _compute_mac_with_key(_LOG_KEY, prev, ts, msg)
            if not hmac.compare_digest(stored_mac, expected):
                expected_legacy = _compute_mac_with_key(_LEGACY_KEY, prev, ts, msg)
                if not hmac.compare_digest(stored_mac, expected_legacy):
                    return False, f"Line {i}: MAC mismatch (modification detected)."

            prev = stored_mac

        return True, f"Chain intact ({len(lines)} entries)."

