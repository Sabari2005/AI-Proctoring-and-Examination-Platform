"""Runtime anti-tamper and anti-debug integrity checks.

This module loads anti_tamper.dll when available, validates its on-disk hash,
and combines native and Python checks to detect debugging, API patching, and
hooking attempts.
"""

import ctypes
import hashlib
import os
import platform
import sys
import threading

# Expected DLL hash generated during build.
_EXPECTED_DLL_SHA256: str = ""   # Populated by build.py.

try:
    # Import build-time hash pin written by build.py.
    from core.dll_hash import ANTI_TAMPER_DLL_SHA256 as _EXPECTED_DLL_SHA256
except ImportError:
    pass


_dll_call_lock = threading.Lock()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_anti_tamper_dll():
    """
        Locate, hash-verify, and load anti_tamper.dll.

        Behavior:
        - Missing DLL: return None.
        - Hash mismatch (when hash pin exists): reject load and return None.
        - No expected hash (development workflow): allow load with warning.
    """
    if platform.system() != "Windows":
        return None

    enforce_hash = bool(str(_EXPECTED_DLL_SHA256 or "").strip())
    if not enforce_hash:
        if getattr(sys, "frozen", False):
            print("[Integrity] CRITICAL: No DLL hash available in production build. Refusing to load.")
            return None
        print("[Integrity] WARNING: No DLL hash (dev mode). Run build.py before production.")

    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "anti_tamper.dll"))

    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(sys._MEIPASS, "anti_tamper.dll"))
        candidates.append(os.path.join(sys._MEIPASS, "core", "anti_tamper.dll"))

    for path in candidates:
        if not os.path.isfile(path):
            continue

        # Step 1: verify on-disk SHA-256 before loading the DLL.
        try:
            actual_hash = _sha256_file(path)
        except OSError as e:
            print(f"[Integrity] Cannot read DLL for hash check: {e}")
            continue

        if enforce_hash:
            if actual_hash.lower() != _EXPECTED_DLL_SHA256.lower():
                print(
                    f"[Integrity] CRITICAL: anti_tamper.dll SHA-256 MISMATCH!\n"
                    f"  Expected : {_EXPECTED_DLL_SHA256}\n"
                    f"  Actual   : {actual_hash}\n"
                    f"  Path     : {path}\n"
                    f"  POSSIBLE DLL REPLACEMENT ATTACK — refusing to load."
                )
                return None
            print(f"[Integrity] DLL hash verified OK  ({actual_hash[:16]}...)")
        else:
            print(f"[Integrity] WARNING: Loading DLL without hash pin in dev mode ({actual_hash[:16]}...).")

        # Step 2: load library and bind expected exports.
        try:
            dll = ctypes.CDLL(path)
            dll.check_hypervisor.restype  = ctypes.c_int
            dll.hide_all_threads.restype  = ctypes.c_int
            dll.check_api_patch.restype   = ctypes.c_int
            dll.check_ntdll_hook.restype  = ctypes.c_int
            return dll
        except OSError as e:
            print(f"[Integrity] Could not load anti_tamper.dll from {path}: {e}")

    return None


_dll = _load_anti_tamper_dll()
if _dll:
    print("[Integrity] anti_tamper.dll loaded — CPUID / thread hiding / API patch / NtQSI hook checks active.")
else:
    print("[Integrity] anti_tamper.dll not found or rejected — running Python-only checks.")


class IntegrityChecker:
    """High-level interface for debugger detection and thread hiding."""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        if self.is_windows:
            self.ntdll    = ctypes.windll.ntdll
            self.kernel32 = ctypes.windll.kernel32

    def check_debugger_present(self) -> dict:
        """Run layered debugger and tamper detection checks.

        Returns:
            Dictionary with detection boolean and explanatory flags.
        """
        detected = False
        flags    = []

        if not self.is_windows:
            return {"detected": detected, "flags": flags}

        try:
            proc = self.kernel32.GetCurrentProcess()

            # IsDebuggerPresent check.
            if self.kernel32.IsDebuggerPresent() != 0:
                detected = True
                flags.append("IsDebuggerPresent() triggered.")

            # CheckRemoteDebuggerPresent check.
            is_rdp = ctypes.c_int(0)
            self.kernel32.CheckRemoteDebuggerPresent(proc, ctypes.byref(is_rdp))
            if is_rdp.value != 0:
                detected = True
                flags.append("CheckRemoteDebuggerPresent() triggered.")

            # NtQueryInformationProcess: ProcessDebugPort (class 7).
            debug_port = ctypes.c_ulong(0)
            st = self.ntdll.NtQueryInformationProcess(
                proc, 7, ctypes.byref(debug_port), ctypes.sizeof(debug_port), None
            )
            if st >= 0 and debug_port.value != 0:
                detected = True
                flags.append("NtQueryInformationProcess(ProcessDebugPort) triggered.")

            # NtQueryInformationProcess: ProcessDebugFlags (class 31).
            debug_flags = ctypes.c_ulong(0)
            st = self.ntdll.NtQueryInformationProcess(
                proc, 31, ctypes.byref(debug_flags), ctypes.sizeof(debug_flags), None
            )
            if st >= 0 and debug_flags.value == 0:
                detected = True
                flags.append("NtQueryInformationProcess(ProcessDebugFlags) triggered.")

            # NtQueryInformationProcess: ProcessDebugObjectHandle (class 30).
            debug_handle = ctypes.c_void_p(0)
            st = self.ntdll.NtQueryInformationProcess(
                proc, 30, ctypes.byref(debug_handle), ctypes.sizeof(debug_handle), None
            )
            if st >= 0 and debug_handle.value:
                detected = True
                flags.append("NtQueryInformationProcess(ProcessDebugObjectHandle) triggered.")

            # Native CPUID hypervisor-bit signal.
            if _dll:
                with _dll_call_lock:
                    hyp = _dll.check_hypervisor()
                if hyp == 1:
                    flags.append("CPUID hypervisor bit set (running inside a hypervisor).")
                elif hyp < 0:
                    flags.append(f"CPUID check returned error {hyp}.")
            else:
                flags.append("anti_tamper.dll absent — CPUID check unavailable.")

            # Native API patch signature checks.
            if _dll:
                with _dll_call_lock:
                    patched = _dll.check_api_patch()
                if patched == 1:
                    detected = True
                    flags.append(
                        "In-memory API PATCH detected on kernel32/ntdll function — "
                        "debugger bypass attempt."
                    )
                elif patched < 0:
                    flags.append(f"API patch check error {patched}.")

            # Native NtQuerySystemInformation hook check.
            if _dll:
                with _dll_call_lock:
                    hooked = _dll.check_ntdll_hook()
                if hooked == 1:
                    detected = True
                    flags.append(
                        "NtQuerySystemInformation is HOOKED — possible kernel-mode "
                        "rootkit or debugger intercepting system calls."
                    )
                elif hooked < 0:
                    flags.append("NtQuerySystemInformation hook check error.")

        except Exception as e:
            flags.append(f"Debugger check exception: {e}")

        return {"detected": detected, "flags": flags}

    def hide_from_debugger(self) -> dict:
        """
        Attempt to hide process threads from debugger visibility.

        Preferred path uses anti_tamper.dll thread-hiding implementation.
        Fallback path uses direct Python/ctypes call for current thread only.
        """
        if not self.is_windows:
            return {"hidden_threads": 0, "method": "skipped_non_windows"}

        if _dll:
            with _dll_call_lock:
                count = _dll.hide_all_threads()
            if count >= 0:
                method = "dll_ntqsi" if count > 0 else "dll_toolhelp_fallback"
                print(f"[Integrity] {count} thread(s) hidden from debugger via DLL.")
                return {"hidden_threads": count, "method": method}
            print(f"[Integrity] hide_all_threads() error {count} — falling back.")

        # Fallback: hide only the current thread via direct ntdll call.
        try:
            st = self.ntdll.NtSetInformationThread(
                self.kernel32.GetCurrentThread(), 17, None, 0
            )
            ok = st >= 0
            return {"hidden_threads": 1 if ok else 0, "method": "python_current_thread_only"}
        except Exception as e:
            return {"hidden_threads": 0, "method": f"error: {e}"}
