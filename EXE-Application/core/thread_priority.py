"""
OS-level thread priority and heartbeat watchdog utilities.

These helpers reduce starvation risk for monitoring loops under heavy CPU load
by combining scheduler-priority hints with heartbeat-based liveness checks.

Typical usage:
- Wrap monitor threads with priority elevation.
- Record heartbeat in monitor loops.
- Run StarvationWatchdog to detect stale heartbeats.
"""

import ctypes
import platform
import threading
import time
from typing import Callable, Optional

# Windows thread-priority constants.
THREAD_PRIORITY_ABOVE_NORMAL = 1
THREAD_PRIORITY_HIGHEST      = 2
THREAD_PRIORITY_TIME_CRITICAL = 15

# Heartbeat timeout threshold used to flag potential starvation.
HEARTBEAT_TIMEOUT_S = 30.0

# Global heartbeat registry.
_heartbeat_lock = threading.Lock()
_heartbeats: dict[str, float] = {}   # thread_name → last_beat_time


def record_heartbeat(name: Optional[str] = None) -> None:
    """Call this at the top of each monitoring loop iteration."""
    name = name or threading.current_thread().name
    with _heartbeat_lock:
        _heartbeats[name] = time.monotonic()


def get_stale_threads(timeout: float = HEARTBEAT_TIMEOUT_S) -> list[str]:
    """Return names of threads whose heartbeat is older than timeout seconds."""
    now = time.monotonic()
    with _heartbeat_lock:
        return [n for n, t in _heartbeats.items() if now - t > timeout]


# Priority elevation helpers.

def elevate_current_thread(level: int = THREAD_PRIORITY_HIGHEST) -> bool:
    """
    Elevate the calling thread's OS priority.
    Returns True on success.

    Call this from inside the target thread, not from the parent spawner.
    """
    if platform.system() == "Windows":
        try:
            kernel32 = ctypes.windll.kernel32
            handle   = kernel32.GetCurrentThread()
            ok       = kernel32.SetThreadPriority(handle, level)
            if ok:
                print(f"[Priority] Thread '{threading.current_thread().name}' "
                      f"elevated to priority {level}.")
            else:
                err = kernel32.GetLastError()
                print(f"[Priority] SetThreadPriority failed: error {err}")
            return bool(ok)
        except Exception as e:
            print(f"[Priority] Elevation failed: {e}")
            return False

    elif platform.system() in ("Linux", "Darwin"):
        try:
            import os, signal
            os.setpriority(os.PRIO_PROCESS, 0, -10)   # Nice -10 increases scheduling priority.
            print(f"[Priority] Thread '{threading.current_thread().name}' niceness set to -10.")
            return True
        except Exception as e:
            print(f"[Priority] setpriority failed: {e}")
            return False

    return False


def wrap_with_priority(
    target: Callable,
    name: str,
    priority: int = THREAD_PRIORITY_HIGHEST,
    daemon: bool = True,
) -> threading.Thread:
    """
    Create a thread that elevates its own OS priority on startup
    and emits an initial heartbeat.

    Usage:
        t = wrap_with_priority(my_loop_fn, name="MyMonitor")
        t.start()
    """
    def _wrapper():
        elevate_current_thread(priority)
        record_heartbeat(name)
        target()

    return threading.Thread(target=_wrapper, name=name, daemon=daemon)


# Starvation watchdog.

class StarvationWatchdog:
    """
    Monitor thread heartbeats and trigger callback when a heartbeat is stale.
    """

    def __init__(self,
                 check_interval: float = 10.0,
                 timeout: float = HEARTBEAT_TIMEOUT_S,
                 on_starvation: Optional[Callable[[str], None]] = None):
        self._interval      = check_interval
        self._timeout       = timeout
        self._on_starvation = on_starvation or (
            lambda n: print(f"[Watchdog] ⚠ Thread '{n}' heartbeat stale — possible CPU starvation.")
        )
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="StarvationWatchdog", daemon=True
            )
            self._thread.start()
        print(f"[Watchdog] Starvation watchdog started "
              f"(check every {self._interval}s, timeout {self._timeout}s).")

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            thread = self._thread
            self._thread = None
            self._stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            stale = get_stale_threads(self._timeout)
            for name in stale:
                self._on_starvation(name)
