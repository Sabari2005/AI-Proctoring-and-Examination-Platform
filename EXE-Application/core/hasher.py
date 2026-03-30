"""Self-integrity hashing and background tamper monitoring.

This module computes a baseline hash over monitored runtime artifacts and
periodically recomputes the hash on a randomized schedule. On mismatch, it
invokes a registered callback and enforces process termination with a hard
timeout fallback.
"""

import hashlib
import hmac
import os
import platform
import random
import sys
import threading
import time
from typing import Callable

# ── Timing constants ──────────────────────────────────────────────────────────
INTERVAL_MIN   =  8    # Minimum randomized re-hash interval, in seconds.
INTERVAL_MAX   = 15    # Maximum randomized re-hash interval, in seconds.
KILL_TIMEOUT_S =  5    # Hard-exit fallback timeout after tamper detection.

# ── Per-session secret for callback tag (FIX 4) ───────────────────────────────
# Per-process secret for callback slot integrity tagging.
_SESSION_SECRET: bytes = os.urandom(32)

# ── State ─────────────────────────────────────────────────────────────────────
# Integrity monitor state
_baseline_hash: str | None = None
_hash_lock = threading.Lock()

# Callback slot state: (callable, integrity tag)
_cb_lock     = threading.Lock()
_callback_fn: Callable | None = None
_callback_tag: bytes | None   = None

# Monitor lifecycle state
_monitor_lock = threading.Lock()
_monitor_thread: threading.Thread | None = None
_monitor_stop_event = threading.Event()


# Internal helpers

def _compute_cb_tag(fn: Callable | None) -> bytes:
    """Compute an integrity tag for the callback slot value."""
    msg = str(id(fn)).encode()
    return hmac.new(_SESSION_SECRET, msg, hashlib.sha256).digest()


def _get_dll_path() -> str | None:
    """Locate anti_tamper.dll across frozen and source run layouts."""
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "anti_tamper.dll"))
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(sys._MEIPASS, "anti_tamper.dll"))
        candidates.append(os.path.join(sys._MEIPASS, "core", "anti_tamper.dll"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _hash_file_into(h: "hashlib._Hash", path: str, label: str = "") -> None:
    """Feed file bytes and optional namespace label into an existing hasher."""
    if label:
        h.update(label.encode())
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)


def _get_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Core hash computation

def generate_self_hash() -> str | None:
    """
    Compute SHA-256 over monitored runtime files.

    Frozen mode includes executable and anti_tamper.dll (or a missing marker).
    Source mode includes all Python files under core/ and anti_tamper.dll
    when present.

    Returns None on read/enumeration errors.
    """
    h = hashlib.sha256()

    try:
        if getattr(sys, "frozen", False):
            # Frozen distribution: hash executable payload first.
            _hash_file_into(h, sys.executable, label="EXE:")

            # Include native anti-tamper DLL in the digest scope.
            dll = _get_dll_path()
            if dll:
                _hash_file_into(h, dll, label="DLL:")
            else:
                # Missing DLL is represented explicitly in digest input.
                h.update(b"DLL:MISSING")

        else:
            # Source layout: hash all Python modules under core/.
            project_root = _get_project_root()
            core_dir = os.path.join(project_root, "core")

            if not os.path.isdir(core_dir):
                print(f"[Integrity] core/ not found at {core_dir}")
                return None

            py_files = sorted(
                os.path.join(root, f)
                for root, _, files in os.walk(core_dir)
                for f in files if f.endswith(".py")
            )
            if not py_files:
                # Empty source tree is treated as invalid integrity state.
                print("[Integrity] core/ has no .py files — treating as tamper evidence.")
                return None

            for path in py_files:
                rel = os.path.relpath(path, project_root)
                h.update(rel.encode())
                _hash_file_into(h, path)

            # Include DLL in source mode when available.
            dll = _get_dll_path()
            if dll:
                _hash_file_into(h, dll, label="DLL:")

        return h.hexdigest()

    except Exception as e:
        print(f"[Integrity] Hash computation error: {e}")
        return None


def verify_integrity(expected_hash: str | None = None) -> str | None:
    return generate_self_hash()


def set_baseline() -> str | None:
    global _baseline_hash
    with _hash_lock:
        _baseline_hash = generate_self_hash()
    print(f"[Integrity] Baseline hash set: {str(_baseline_hash)[:16]}...")
    return _baseline_hash


# Callback registration

def register_tamper_callback(callback: Callable):
    """
    Register callback invoked on detected hash mismatch.

    The callback slot is stored with an integrity tag. The tag is validated
    before invocation to detect in-memory callback slot replacement.
    """
    global _callback_fn, _callback_tag
    with _cb_lock:
        _callback_fn  = callback
        _callback_tag = _compute_cb_tag(callback)


def _invoke_callback_or_kill(reason: str):
    """
    Invoke tamper callback with forced termination fallback.

    Flow:
    1) Arm a kill timer.
    2) Validate callback slot integrity tag.
    3) Invoke callback best-effort; on failure, hard-exit immediately.
    """

    def _force_kill():
        time.sleep(KILL_TIMEOUT_S)
        print(f"[Integrity] FORCE KILL (tamper kill timeout reached).")
        os._exit(1)

    # Arm kill timer immediately so tamper handling cannot stall indefinitely.
    kill_thread = threading.Thread(target=_force_kill, daemon=True, name="TamperKill")
    kill_thread.start()

    # Verify callback slot has not been replaced in memory.
    with _cb_lock:
        fn  = _callback_fn
        tag = _callback_tag

    if fn is not None:
        expected_tag = _compute_cb_tag(fn)
        if not hmac.compare_digest(expected_tag, tag or b""):
            print("[Integrity] CRITICAL: Tamper callback slot was overwritten — killing immediately.")
            os._exit(1)

        try:
            fn(reason)
        except Exception as e:
            print(f"[Integrity] Callback raised: {e} — falling back to os._exit(1).")
            os._exit(1)
    else:
        # No callback registered: terminate directly.
        print("[Integrity] No callback registered — hard-killing process.")
        os._exit(1)


    # Monitor loop

def _continuous_hash_monitor(stop_event: threading.Event):
    """
    Background monitor that periodically validates runtime file integrity.

    Uses randomized sleep intervals to reduce predictability of check windows.
    """
    while not stop_event.is_set():
        # Randomized interval reduces predictability of check windows.
        sleep_for = random.uniform(INTERVAL_MIN, INTERVAL_MAX)
        if stop_event.wait(timeout=sleep_for):
            break

        t0      = time.monotonic()
        current = generate_self_hash()
        elapsed = time.monotonic() - t0

        if current is None:
            # Failed hash read is logged and retried on next interval.
            print("[Integrity] WARNING: Cannot read own files for re-hash check.")
            continue

        with _hash_lock:
            baseline = _baseline_hash

        if baseline and current != baseline:
            reason = (
                f"File integrity violation: hash changed "
                f"({str(baseline)[:12]}... → {str(current)[:12]}...). "
                f"Re-hash took {elapsed:.2f}s."
            )
            print(f"[Integrity] ⚠ TAMPER DETECTED — {reason}")
            _invoke_callback_or_kill(reason)
            return

    with _monitor_lock:
        global _monitor_thread
        _monitor_thread = None


def start_continuous_monitoring():
    """Start the background integrity monitor if not already running."""
    global _monitor_thread
    with _monitor_lock:
        if _monitor_thread and _monitor_thread.is_alive():
            return
        _monitor_stop_event.clear()
        _monitor_thread = threading.Thread(
            target=_continuous_hash_monitor,
            args=(_monitor_stop_event,),
            daemon=True,
            name="HashMonitor",
        )
        _monitor_thread.start()
    print(
        f"[Integrity] Continuous file hash monitoring started "
        f"(interval: {INTERVAL_MIN}–{INTERVAL_MAX}s random, "
        f"force-kill timeout: {KILL_TIMEOUT_S}s, DLL included)"
    )


def stop_continuous_monitoring(timeout: float = 2.0):
    """Request monitor shutdown and join thread best-effort."""
    _monitor_stop_event.set()
    with _monitor_lock:
        thread = _monitor_thread
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=timeout)


def is_monitor_running() -> bool:
    """Return True when the integrity monitor thread is active."""
    with _monitor_lock:
        return bool(_monitor_thread and _monitor_thread.is_alive())
