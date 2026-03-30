"""Process, window, and extension monitoring for exam integrity.

Combines process-name heuristics with executable fingerprinting, window-title
inspection, WSL activity checks, and optional browser extension probing.
"""

import ctypes
import hashlib
import json
import os
import platform
import socket
import struct
import threading
import time
import urllib.request

import psutil

if platform.system() == "Windows":
    try:
        import win32api
        import win32con
        import win32gui
    except Exception:
        win32api = None
        win32con = None
        win32gui = None
else:
    win32api = None
    win32con = None
    win32gui = None

# Known-bad executable hashes populated at runtime.
# Populated at session start from /v1/session/nonce response field "blacklisted_hashes".
# Do not hardcode hashes here — they go stale and placeholder values bypass detection.
BLACKLISTED_SHA256: set[str] = set()

# PE import fingerprints for tool-category detection.
# These DLLs are imported by specific categories of tools.
# Hard to remove without breaking the binary.
CAPTURE_IMPORT_DLLS  = {"dxgi.dll", "d3d11.dll", "d3d9.dll", "nvifr64.dll",
                        "amdh264enc.dll", "obs.dll"}
REMOTE_IMPORT_DLLS   = {"rdpbase.dll", "anydesk.dll", "tvshared.dll",
                        "mstscax.dll", "rdpclip.exe"}
DEBUGGER_IMPORT_DLLS = {"dbghelp.dll", "symsrv.dll", "dbgeng.dll",
                        "sxsstypes.dll"}

# Suspicious process-name keyword fragments.
SUSPICIOUS_PROC_KEYWORDS = [
    "obs64", "obs32", "obs.exe", "obs-studio", "bandicam", "sharex", "fraps", "camtasia",
    "action64", "flashback",
    "anydesk", "teamviewer", "logmein", "rdclient", "supremo", "rustdesk",
    "x64dbg", "x32dbg", "cheatengine", "cheat engine", "wireshark", "fiddler",
    "processhacker", "procmon", "pestudio", "dnspy", "ghidra", "ida64",
    # Keep only auto-kill-safe collaboration/tooling keywords here.
    "discord", "skype", "zoom", "slack", "powertoys",
]

SUSPICIOUS_WINDOW_KEYWORDS = [
    "obs studio", "bandicam", "sharex", "anydesk", "teamviewer",
    "remote desktop", "x64dbg", "cheat engine", "wireshark", "fiddler",
    "discord", "zoom meeting", "microsoft teams", 
]

# Known WSL helper process names.
WSL_RUNNING_PROCS = {
    "wslhost.exe", "wslservice.exe",
    "ubuntu.exe", "kali.exe", "debian.exe",
}

# Browser extension blacklist (Chrome/Edge extension IDs).
BLACKLISTED_EXTENSION_IDS = {
    # Grammarly
    "kbfnbcaeplbcioakkpcpgfkobkghlhen",
    # GoFullPage (screen capture)
    "fdpohaocaechangangpjjfllnfblmejfhj",
    # Lightshot Screenshot
    "mbniclmhobmnbdlbpiphghaielnnpgdp",
    # Nimbus Screenshot & Screen Video Recorder
    "bpconcjcammlapcogcnnelfmaeghhagj",
    # Loom (screen recorder)
    "liecbddmkiiihnedobmlmillhodjkdmb",
    # Screencastify
    "mmeijimgabbpbgpdklnllpncmdofkcpn",
    # Awesome Screenshot
    "nlipoenfbbikpbjkfpfillcgkoblgpmj",
    # Scribe (workflow capture)
    "okfkdaglfjjjfefdcppliegebpoegaii",
    # ChatGPT extension (various)
    "jljodcgpokmoofoehnbbldpcbcpjcfef",
    # Compose AI
    "ddlbpoadnlelfggjpanjpgokgcfbaebk",
}


# PE import reader (pure Python, no pefile dependency).

def _read_pe_imports(path: str) -> set:
    """
    Parse the PE import table from the first 64 KB of an executable.
    Returns a set of imported DLL names (lowercase).
    On any error returns an empty set.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(65536)

        if len(data) < 64 or data[:2] != b"MZ":
            return set()

        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_offset + 24 > len(data):
            return set()
        if data[pe_offset:pe_offset + 4] != b"PE\0\0":
            return set()

        machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
        is64    = machine == 0x8664

        opt_offset = pe_offset + 24
        if is64:
            import_rva = struct.unpack_from("<I", data, opt_offset + 104)[0]
        else:
            import_rva = struct.unpack_from("<I", data, opt_offset + 96)[0]

        if import_rva == 0 or import_rva >= len(data):
            return set()

        imports = set()
        off = import_rva
        while off + 20 <= len(data):
            name_rva = struct.unpack_from("<I", data, off + 12)[0]
            if name_rva == 0:
                break
            if name_rva < len(data):
                end = data.find(b"\x00", name_rva)
                dll_name = data[name_rva:end].decode("ascii", errors="ignore").lower()
                if dll_name:
                    imports.add(dll_name)
            off += 20
        return imports
    except Exception:
        return set()


def _sha256_exe(path: str) -> str | None:
    """Return SHA-256 hex of an executable, or None on error."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# Browser extension probe via Chrome DevTools Protocol.

def _probe_browser_extensions(
    host: str = "127.0.0.1",
    port: int = 9222,
    timeout: float = 0.8,
) -> list:
    """
    Query Chrome/Edge DevTools Protocol to list loaded extensions.
    Returns list of flag strings for blacklisted extension IDs.
    Browser must be launched with --remote-debugging-port=9222.
    """
    flags = []
    try:
        url = f"http://{host}:{port}/json"
        req = urllib.request.urlopen(url, timeout=timeout)
        tabs = json.loads(req.read())
        for tab in tabs:
            tab_url = tab.get("url", "")
            ext_id  = tab.get("extensionId", "")

            # Extension URLs: chrome-extension://<id>/...
            if tab_url.startswith("chrome-extension://"):
                try:
                    ext_id = tab_url.split("/")[2]
                except IndexError:
                    pass

            if ext_id in BLACKLISTED_EXTENSION_IDS:
                title = tab.get("title", ext_id)
                flags.append(f"Blacklisted browser extension active: '{title}' ({ext_id})")

    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass   # CDP not available or browser not running with debug port
    except Exception as e:
        flags.append(f"CDP extension probe error: {e}")
    return flags


# Main monitor class

class ProcessMonitor:
    """Process/window integrity monitor with optional background scheduling."""

    def __init__(self, scan_interval: float = 10.0):
        self.is_windows    = platform.system() == "Windows"
        self.scan_interval = scan_interval
        self._blacklisted_sha256: set[str] = set(BLACKLISTED_SHA256)
        self._max_processes_per_scan = 350
        self._scan_cursor = 0

        # Cache expensive binary fingerprint work across scans.
        self._fingerprint_ttl_sec = 90.0
        self._fingerprint_cache: dict[str, tuple[float, int, str | None, set[str], float]] = {}
        self._fingerprint_cache_max = 1024

        # Background scanner lifecycle state.
        self._stop_event    = threading.Event()
        self._scan_thread: threading.Thread | None = None
        self._watchdog_thread: threading.Thread | None = None
        self._last_result: dict = {}
        self._result_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._on_violation = None

    def _get_binary_fingerprint_cached(self, exe_path: str) -> tuple[str | None, set[str]]:
        """Return (sha256, imports) using a TTL cache keyed by file stat."""
        try:
            stat = os.stat(exe_path)
        except Exception:
            return None, set()

        mtime = float(stat.st_mtime)
        size = int(stat.st_size)
        now = time.time()

        with self._state_lock:
            cached = self._fingerprint_cache.get(exe_path)
            if cached is not None:
                c_mtime, c_size, c_digest, c_imports, c_ts = cached
                if c_mtime == mtime and c_size == size and (now - c_ts) <= self._fingerprint_ttl_sec:
                    return c_digest, set(c_imports)

        digest = _sha256_exe(exe_path)
        imports = _read_pe_imports(exe_path)

        with self._state_lock:
            if len(self._fingerprint_cache) >= self._fingerprint_cache_max:
                # Drop oldest cached entry to bound memory.
                oldest_key = min(self._fingerprint_cache, key=lambda k: self._fingerprint_cache[k][4])
                self._fingerprint_cache.pop(oldest_key, None)
            self._fingerprint_cache[exe_path] = (mtime, size, digest, imports, now)

        return digest, imports

    def set_blacklisted_hashes(self, hashes) -> None:
        """Replace runtime SHA-256 blacklist with validated lower-hex values."""
        normalized: set[str] = set()
        for item in hashes or []:
            digest = str(item or "").strip().lower()
            if len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest):
                normalized.add(digest)
        with self._state_lock:
            self._blacklisted_sha256 = normalized

    def _check_process_binary(self, proc: psutil.Process, blacklisted: set[str]) -> list[str]:
        """
        Inspect process executable using SHA-256 and PE import fingerprints.

        Returns a list of violation flags for this process.
        """
        flags = []
        try:
            exe = proc.exe()
            if not exe or not os.path.isfile(exe):
                return flags

            # Cached hash/import retrieval reduces repeated file I/O.
            digest, imports = self._get_binary_fingerprint_cached(exe)
            if digest and digest in blacklisted:
                flags.append(
                    f"BLACKLISTED binary (SHA-256 match): {exe} "
                    f"(PID {proc.pid}, hash {digest[:16]}...)"
                )
                return flags

            # PE import fingerprinting as secondary behavioral signal.
            if imports & CAPTURE_IMPORT_DLLS:
                flags.append(
                    f"Screen-capture DLL imports in: {proc.name()} "
                    f"(PID {proc.pid}, imports: {imports & CAPTURE_IMPORT_DLLS})"
                )
            if imports & REMOTE_IMPORT_DLLS:
                flags.append(
                    f"Remote-access DLL imports in: {proc.name()} "
                    f"(PID {proc.pid}, imports: {imports & REMOTE_IMPORT_DLLS})"
                )
            if imports & DEBUGGER_IMPORT_DLLS:
                flags.append(
                    f"Debugger DLL imports in: {proc.name()} "
                    f"(PID {proc.pid}, imports: {imports & DEBUGGER_IMPORT_DLLS})"
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            pass
        except Exception as e:
            flags.append(f"Binary fingerprint error for PID {proc.pid}: {e}")
        return flags

    def _scan_all_windows(self) -> list[str]:
        """
        Enumerate top-level windows, including hidden windows.

        Uses IsWindow and style inspection to classify hidden/visible state
        while scanning suspicious titles.
        """
        flags = []
        if not self.is_windows or not win32gui or not win32con:
            return flags
        try:
            WS_VISIBLE = 0x10000000

            def _cb(hwnd, acc):
                if not win32gui.IsWindow(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True
                tl = title.lower()
                for kw in SUSPICIOUS_WINDOW_KEYWORDS:
                    if kw in tl:
                        style   = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                        visible = bool(style & WS_VISIBLE)
                        acc.append(
                            f"Suspicious {'hidden' if not visible else 'visible'} "
                            f"window: '{title}'"
                        )
                        break
                return True

            win32gui.EnumWindows(_cb, flags)
        except Exception as e:
            flags.append(f"Window enum error: {e}")
        return flags

 
    def _check_wsl_running(self) -> list[str]:
        """
                Multi-layer WSL activity detection.

                Layers:
                    A) Process list signals.
                    B) WSL network adapter signals.
                    C) Hyper-V VM name query signals.
        """
        flags = []

        # Layer A: process list signals.
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    info = getattr(proc, "info", {}) or {}
                    name = (info.get("name") or "").lower()
                    if name in {p.lower() for p in WSL_RUNNING_PROCS}:
                        flags.append(
                            f"WSL process detected: {info.get('name') or name} "
                            f"(PID {info.get('pid') or proc.pid})"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                    pass
        except Exception as e:
            flags.append(f"WSL process check error: {e}")

        # Layer B: WSL network adapter signal.
        try:
            for iface in psutil.net_if_addrs():
                if "wsl" in iface.lower():
                    flags.append(
                        f"WSL2 network adapter present: '{iface}' "
                        "(WSL2 Hyper-V network stack is active)"
                    )
                    break
        except Exception:
            pass

        # Layer C: Hyper-V VM listing heuristic.
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command",
                 "(Get-VM -ErrorAction SilentlyContinue).Name"],
                capture_output=True, text=True, timeout=2,
                creationflags=0x08000000   # CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "wsl" in line.strip().lower():
                        flags.append(
                            f"WSL2 Hyper-V VM detected via HCS: '{line.strip()}'"
                        )
        except Exception:
            pass

        return flags

    def scan_environment(self) -> dict:
        """
        Run a full process/window environment scan and return structured results.
        """
        flags = []

        # 1) Window scan.
        flags.extend(self._scan_all_windows())

        # 2) Process scan with name and binary fingerprint checks.
        own_pid = os.getpid()
        own_exe = None
        try:
            own_exe = os.path.abspath(psutil.Process(own_pid).exe()).lower()
        except Exception:
            pass
        
        scan_error = ""
        scanned_count = 0
        try:
            with self._state_lock:
                blacklisted_snapshot = set(self._blacklisted_sha256)

            all_procs = list(psutil.process_iter(["pid", "name", "exe"]))
            total_procs = len(all_procs)
            if total_procs > 0:
                with self._state_lock:
                    start_idx = self._scan_cursor % total_procs
                    scan_limit = min(total_procs, self._max_processes_per_scan)
                    self._scan_cursor = (start_idx + scan_limit) % total_procs

                ordered_procs = all_procs[start_idx:] + all_procs[:start_idx]
                procs_to_scan = ordered_procs[:scan_limit]
            else:
                procs_to_scan = []

            for proc in procs_to_scan:
                info = getattr(proc, "info", {}) or {}
                pid = info.get("pid")
                if pid == own_pid:
                    continue
                try:
                    scanned_count += 1
                    # Cooperative yield to avoid monitor CPU monopolization.
                    if scanned_count % 25 == 0:
                        time.sleep(0)

                    name = (info.get("name") or "").lower()
                    proc_exe_raw = info.get("exe") or ""
                    if not proc_exe_raw:
                        try:
                            proc_exe_raw = proc.exe() or ""
                        except Exception:
                            proc_exe_raw = ""
                    proc_exe = proc_exe_raw.lower()

                    # Whitelist own executable and direct parent/child relationship.
                    if name in ("observeproctor.exe", "observeproctor"):
                        continue
                    
                    # Also compare executable path to handle renamed binaries.
                    if own_exe and proc_exe and os.path.abspath(proc_exe) == own_exe:
                        continue
                    
                    # Skip direct parent/child relation with self process.
                    try:
                        if proc.ppid() == own_pid or psutil.Process(own_pid).ppid() == pid:
                            continue
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                    # Name-based heuristic (fast first pass).
                    if any(str(kw).lower() in name for kw in SUSPICIOUS_PROC_KEYWORDS):
                        flags.append(
                            f"Suspicious process name: {name} (PID {pid})"
                        )
                        # Still run binary checks to validate true identity.
                        flags.extend(self._check_process_binary(proc, blacklisted_snapshot))
                        continue

                    # Binary fingerprint checks for remaining processes.
                    flags.extend(self._check_process_binary(proc, blacklisted_snapshot))

                    # PE metadata as a secondary heuristic.
                    if self.is_windows and win32api and proc_exe_raw and os.path.exists(proc_exe_raw):
                        try:
                            lang, cp = win32api.GetFileVersionInfo(
                                proc_exe_raw, "\\VarFileInfo\\Translation"
                            )[0]
                            prefix  = f"\\StringFileInfo\\{lang:04X}{cp:04X}\\"
                            desc    = str(win32api.GetFileVersionInfo(proc_exe_raw, prefix + "FileDescription") or "")
                            company = str(win32api.GetFileVersionInfo(proc_exe_raw, prefix + "CompanyName") or "")
                            meta_blob = f"{desc} {company}".lower()
                            if any(str(kw).lower() in meta_blob for kw in SUSPICIOUS_PROC_KEYWORDS):
                                flags.append(
                                    f"Suspicious PE metadata: {name} ({desc} | {company})"
                                )
                        except Exception:
                            pass

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, KeyError):
                    pass
        except Exception as e:
            # Keep low-level scanner failures internal to avoid noisy UI artifacts.
            scan_error = f"{type(e).__name__}: {e}"
            print(f"[ProcMon] Process scanner degraded: {scan_error}")

        # 3) WSL activity checks.
        flags.extend(self._check_wsl_running())

        # 4) Browser extension probe via CDP.
        flags.extend(_probe_browser_extensions())

        flagged = list(dict.fromkeys(flags))
        result = {
            "flagged_processes": flagged,
            "is_clean":          len(flagged) == 0,
            "flags":             flagged,
            "timestamp":         time.time(),
            "scan_error":        scan_error,
            "scanned_processes": scanned_count,
        }
        with self._result_lock:
            self._last_result = result
        return result

    def start_background_scanning(self, on_violation=None):
        """
        Start background scanning with watchdog-based self-healing.

        The scanner runs every scan_interval seconds and invokes callback on
        non-clean results.

        If the scanner thread exits unexpectedly, the watchdog restarts it.
        """
        with self._state_lock:
            scan_alive = self._scan_thread is not None and self._scan_thread.is_alive()
            watchdog_alive = self._watchdog_thread is not None and self._watchdog_thread.is_alive()
            if scan_alive and watchdog_alive:
                # Already running; refresh callback only.
                self._on_violation = on_violation
                return

            self._stop_event.clear()
            self._on_violation = on_violation

        def _scan_loop():
            while not self._stop_event.is_set():
                try:
                    result = self.scan_environment()
                    with self._state_lock:
                        violation_cb = self._on_violation
                    if not result["is_clean"] and violation_cb:
                        try:
                            violation_cb(result)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[ProcMon] Scan error: {e}")
                self._stop_event.wait(self.scan_interval)

        def _watchdog():
            while not self._stop_event.is_set():
                should_restart = False
                with self._state_lock:
                    if self._scan_thread is None or not self._scan_thread.is_alive():
                        should_restart = True
                if should_restart and not self._stop_event.is_set():
                    print("[ProcMon] Scanner thread died — restarting.")
                    replacement = threading.Thread(
                        target=_scan_loop, daemon=True, name="ProcMon-Scanner"
                    )
                    with self._state_lock:
                        self._scan_thread = replacement
                    replacement.start()
                self._stop_event.wait(self.scan_interval + 2)

        self._scan_thread = threading.Thread(
            target=_scan_loop, daemon=True, name="ProcMon-Scanner"
        )
        self._scan_thread.start()

        self._watchdog_thread = threading.Thread(
            target=_watchdog, daemon=True, name="ProcMon-Watchdog"
        )
        self._watchdog_thread.start()

        print(f"[ProcMon] Background scanner started (interval: {self.scan_interval}s, watchdog active).")

    def stop_background_scanning(self):
        """Stop scanner/watchdog threads and clear callback state."""
        with self._state_lock:
            self._stop_event.set()
            scan_thread = self._scan_thread
            watchdog_thread = self._watchdog_thread
            self._scan_thread = None
            self._watchdog_thread = None
            self._on_violation = None
        if scan_thread is not None and scan_thread.is_alive():
            scan_thread.join(timeout=2.0)
        if watchdog_thread is not None and watchdog_thread.is_alive():
            watchdog_thread.join(timeout=2.0)

    def get_latest_result(self) -> dict:
        """Return a thread-safe copy of the most recent scan result."""
        with self._result_lock:
            return dict(self._last_result)
