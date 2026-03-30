"""Public exports for core proctoring infrastructure.

This package exposes the primary building blocks used across the application,
including audit logging, secret handling, hardware checks, and thread
management helpers.
"""

# Re-export commonly used core symbols for convenient imports.
from .secure_audit_log import SecureAuditLog
from .logger import logger, ProctorLogger
from .dpapi_secrets import SecretStore, protect, unprotect, protect_str, unprotect_str
from .hw_checks import HardwareChecker
from .thread_priority import (
    StarvationWatchdog,
    elevate_current_thread,
    wrap_with_priority,
    record_heartbeat,
    get_stale_threads,
)

try:
    from .proctoring_service import ProctoringService
except Exception:
    ProctoringService = None

__all__ = [
    'SecureAuditLog',
    'logger',
    'ProctorLogger',

    'SecretStore',
    'protect',
    'unprotect',
    'protect_str',
    'unprotect_str',

    'HardwareChecker',

    'StarvationWatchdog',
    'elevate_current_thread',
    'wrap_with_priority',
    'record_heartbeat',
    'get_stale_threads',
    'ProctoringService',
]
