"""Audit logging facade for console output and tamper-evident file logging.

When available, this module writes audit entries through SecureAuditLog.
If secure logging cannot be initialized, it falls back to plain file append
to preserve operability.
"""

import logging
import os
import sys
import threading
from datetime import datetime, timezone

try:
    from .secure_audit_log import SecureAuditLog
    _SECURE_LOG_AVAILABLE = True
except Exception:
    _SECURE_LOG_AVAILABLE = False


class ProctorLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Resolve runtime log directory under the project root.
        core_dir = os.path.dirname(os.path.abspath(__file__))
        new_version_dir = os.path.dirname(core_dir)
        self.log_dir = os.path.join(new_version_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "proctor_audit.log")
        self._write_lock = threading.RLock()

        # Prefer tamper-evident secure audit logging.
        if _SECURE_LOG_AVAILABLE:
            self._secure = SecureAuditLog(self.log_file)
            print("[Logger] Using HMAC-chained tamper-evident audit log.")
        else:
            self._secure = None
            print("[Logger] WARNING: SecureAuditLog unavailable — falling back to plain log.")

        # Console logger for local diagnostics and operator visibility.
        self._console = logging.getLogger("ObserveProctor.console")
        self._console.setLevel(logging.DEBUG)
        if not self._console.handlers:
            # In windowed executables, stdio streams may be unavailable.
            # NullHandler prevents repeated write errors in logging internals.
            stream = getattr(sys, "__stderr__", None) or getattr(sys, "__stdout__", None)
            if stream is not None and hasattr(stream, "write"):
                ch = logging.StreamHandler(stream)
                fmt = logging.Formatter("[%(levelname)s] %(message)s")
                ch.setFormatter(fmt)
                self._console.addHandler(ch)
            else:
                self._console.addHandler(logging.NullHandler())
        self._console.propagate = False

    def _write(self, level: str, module: str, msg: str, telemetry=None):
        """Write an audit record to secure log or plain fallback file."""
        with self._write_lock:
            if self._secure:
                self._secure.append(level, module, msg, telemetry)
            else:
                # Fallback path when secure log backend is unavailable.
                ts   = datetime.now(timezone.utc).isoformat()
                line = f'[{ts}] [{level}] [{module}] {msg}\n'
                try:
                    os.makedirs(self.log_dir, exist_ok=True)
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(line)
                except Exception:
                    pass

    def debug(self, msg: str, telemetry=None, module: str = ""):
        """Emit a DEBUG-level log entry."""
        self._console.debug(msg)
        self._write("DEBUG", module, msg, telemetry)

    def info(self, msg: str, telemetry=None, module: str = ""):
        """Emit an INFO-level log entry."""
        self._console.info(msg)
        self._write("INFO", module, msg, telemetry)

    def warning(self, msg: str, telemetry=None, module: str = ""):
        """Emit a WARNING-level log entry."""
        self._console.warning(msg)
        self._write("WARNING", module, msg, telemetry)

    def error(self, msg: str, telemetry=None, module: str = ""):
        """Emit an ERROR-level log entry."""
        self._console.error(msg)
        self._write("ERROR", module, msg, telemetry)

    def critical_security_event(self, msg: str, telemetry=None, module: str = ""):
        """Emit a CRITICAL-level security violation log entry."""
        full = f"SECURITY VIOLATION: {msg}"
        self._console.critical(full)
        self._write("CRITICAL", module, full, telemetry)

    def verify_log_integrity(self) -> tuple[bool, str]:
        """Verify the HMAC chain of the audit log. Returns (ok, reason)."""
        if self._secure:
            return self._secure.verify_chain()
        return False, "SecureAuditLog not available."


# Global singleton logger instance used across the application.
logger = ProctorLogger()
