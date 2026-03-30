"""OS and environment risk checks for proctoring enforcement.

Combines platform/version validation with VM, RDP, sandbox, anti-debug, and
clock-integrity signals, then prepares a local safety verdict and optional
server-side telemetry decision.
"""

import platform
import subprocess
import ctypes
import os
import socket
import struct
import time
import threading
import winreg
import uuid
import re

import wmi

try:
    import psutil
except ImportError:
    psutil = None

try:
    import cpufeature
except ImportError:
    cpufeature = None

# Optional higher-phase dependencies (graceful fallback when unavailable).
try:
    from .integrity import IntegrityChecker, _dll as _antitamper_dll
except (ImportError, ModuleNotFoundError):
    IntegrityChecker = None
    _antitamper_dll = None

try:
    from .telemetry import TelemetryClient
except (ImportError, ModuleNotFoundError):
    TelemetryClient = None

try:
    from .hasher import generate_self_hash
except (ImportError, ModuleNotFoundError):
    generate_self_hash = None

# Core local-check dependencies.
from .hw_checks import HardwareChecker
from .logger import logger


_antitamper_lock = threading.Lock()


# NTP helper

def _ntp_offset_seconds(server: str = "pool.ntp.org", timeout: float = 4.0) -> float | None:
    """
    Query an NTP server over UDP and return local clock offset in seconds.

    Positive offset means local clock is ahead of NTP time.
    Returns None when query fails.
    """
    NTP_PACKET_FORMAT = "!12I"
    NTP_DELTA = 2208988800  # seconds between 1900 and 1970

    try:
        packet = bytearray(48)
        packet[0] = 0b00_100_011   # LI=0, VN=4, Mode=3 (client)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(packet, (server, 123))
            data, _ = s.recvfrom(1024)

        if len(data) < 48:
            return None

        unpacked = struct.unpack(NTP_PACKET_FORMAT, data[:48])
        # NTP transmit timestamp uses words 10 and 11.
        ntp_tx = unpacked[10] + unpacked[11] / 2**32
        ntp_time = ntp_tx - NTP_DELTA
        local_time = time.time()
        return local_time - ntp_time   # positive = local is ahead of NTP
    except Exception:
        return None


def _mac_family_is_link(family: int) -> bool:
    """
    Return True if the address family represents a link-layer (MAC) address.

    Handles psutil.AF_LINK when available and common raw family values used
    across platforms for hardware-link addresses.
    """
    try:
        import psutil as _ps
        if family == _ps.AF_LINK:
            return True
    except Exception:
        pass
    # Common raw values for link-layer
    return family in (17, 18, 23)


class OSEnvChecker:
    def __init__(self, process_monitor=None, vision_proctor=None, audio_proctor=None, email: str = "", login_token: str = ""):
        self.os_name      = platform.system()
        self.os_release   = platform.release()
        self.os_version   = platform.version()
        self.architecture = platform.machine()
        self.is_windows   = self.os_name == "Windows"
        self.is_mac       = self.os_name == "Darwin"
        self.process_monitor  = process_monitor
        self.vision_proctor   = vision_proctor
        self.audio_proctor    = audio_proctor
        self.email        = email              # User's email for authentication
        self.login_token  = login_token        # Login token from /v1/auth/login
        self._last_telemetry  = None
        self._telemetry_client = None
        self._cached_clock_integrity = None
        self._sandbox_sleep0_timing_checked = False
        self._sandbox_sleep0_timing_value = None
        self._state_lock = threading.RLock()

    def set_credentials(self, email: str, login_token: str):
        """Update user credentials after login completes."""
        with self._state_lock:
            self.email = email
            self.login_token = login_token
        print(f"[OSEnvChecker] Credentials updated for user: {email}")

    def set_telemetry_client(self, telemetry_client):
        """Inject an already-authenticated TelemetryClient for reuse."""
        with self._state_lock:
            self._telemetry_client = telemetry_client

    def prime_clock_integrity(self):
        """Run clock integrity once (before isolation) and cache the result."""
        with self._state_lock:
            if self._cached_clock_integrity is not None:
                return dict(self._cached_clock_integrity)

        computed = self.check_clock_integrity()
        with self._state_lock:
            if self._cached_clock_integrity is None:
                self._cached_clock_integrity = computed
            return dict(self._cached_clock_integrity)

    def run_all_checks(self):
        """Run local checks and optionally request a server-side environment decision."""
        with self._state_lock:
            cached_clock_integrity = self._cached_clock_integrity
            email = self.email
            login_token = self.login_token
            telemetry = self._telemetry_client

        # Anti-debug checks (when integrity module is available).
        debug_check = {"detected": False, "level": "unavailable"}
        if IntegrityChecker:
            try:
                integrity = IntegrityChecker()
                debug_check = integrity.check_debugger_present()
                integrity.hide_from_debugger()
            except Exception as e:
                print(f"[OSEnvChecker] IntegrityChecker error: {e}")

        # Local environment evidence collection.
        hw = HardwareChecker()
        hw_results = hw.run_all_checks()

        proc_results = None
        if self.process_monitor:
            proc_results = self.process_monitor.scan_environment()

        audio_results = None
        if self.audio_proctor:
            audio_results = self.audio_proctor.get_latest_telemetry()

        vision_results = None
        if self.vision_proctor:
            vision_results = self.vision_proctor.get_latest_telemetry()

        # Binary/source integrity hash (optional by deployment phase).
        binary_hash = "unavailable"
        if generate_self_hash:
            try:
                binary_hash = generate_self_hash()
            except Exception:
                pass

        clock_integrity = cached_clock_integrity
        if clock_integrity is None:
            clock_integrity = {
                "tampered": False,
                "offset_seconds": None,
                "message": "Clock integrity not primed yet.",
            }

        results = {
            "binary_integrity_hash": binary_hash,
            "os_details":     self.get_os_details(),
            "os_enforcement": self.check_minimum_os(),
            "vm_detected":    self.detect_virtual_machine(),
            "rdp_detected":   self.detect_rdp_sessions(),
            "sandbox_detected": self.detect_sandbox(),
            "clock_integrity":  clock_integrity,
            "hw_checks":        hw_results,
            "anti_debug":       debug_check,
            "process_violations": proc_results,
            "audio_proctoring": audio_results,
            "vision_proctoring": vision_results,
        }

        results["client_raw_is_safe"] = (
            results["os_enforcement"]["passed"]
            and not results["vm_detected"]["detected"]
            and not results["rdp_detected"]["detected"]
            and not results["sandbox_detected"]["detected"]
            and not results["clock_integrity"]["tampered"]
            and not results["anti_debug"].get("detected", False)
            and hw_results["client_raw_hw_safe"]
        )

        # Optional server-side adjudication.
        if TelemetryClient and email and login_token:
            try:
                if telemetry is None:
                    telemetry = TelemetryClient(email=email, login_token=login_token)
                    with self._state_lock:
                        self._telemetry_client = telemetry
                with self._state_lock:
                    self._last_telemetry = telemetry
                if not telemetry.session_nonce and not telemetry.authenticate_session():
                    results["is_safe"]       = False
                    results["server_action"] = "block"
                    results["error"]         = "Failed to authenticate session with server."
                    return results

                payload         = telemetry.generate_payload(results)
                server_response = telemetry.send_telemetry(payload)

                decision = server_response.get("server_decision", {}) or {}
                action = str(decision.get("action", "block") or "block").strip().lower()
                # Enforce action semantics consistently.
                results["server_action"] = action
                results["is_safe"] = action != "block"

                if action == "block":
                    logger.critical_security_event("Server rejected environment", telemetry=results)
                elif action == "warn":
                    logger.warning("Server warning: environment flagged", telemetry=results, module="os_checks")
                else:
                    logger.info("Security checks passed", telemetry=results)
            except Exception as e:
                print(f"[OSEnvChecker] Telemetry unavailable (Phase 4+): {e}")
                results["is_safe"] = results.get("client_raw_is_safe", False)
                results["server_action"] = "local-checks-only"
        else:
            # Local-only decision path.
            results["is_safe"] = results.get("client_raw_is_safe", False)
            results["server_action"] = "local-checks-only" if not email else "auth-not-ready"

        return results

    def get_os_details(self):
        """Return normalized platform metadata used in telemetry payloads."""
        return {
            "name":         self.os_name,
            "release":      self.os_release,
            "version":      self.os_version,
            "architecture": self.architecture,
        }

    def check_minimum_os(self):
        """Validate minimum supported OS version.

        Windows requires major version >= 10.
        macOS requires major version >= 11.
        """
        passed  = False
        message = ""

        if self.is_windows:
            try:
                # Prefer platform.version() build string for version parsing.
                build_str = platform.version()   # "10.0.26200" on Win11
                major = int(build_str.split(".")[0])
                if major >= 10:
                    passed  = True
                else:
                    message = (
                        f"Unsupported Windows version: {self.os_release} "
                        f"(build {build_str}). Require Windows 10 or higher."
                    )
            except (ValueError, IndexError, AttributeError):
                # Fail closed when version parsing is unavailable/corrupted.
                passed  = False
                message = f"Cannot determine Windows version (release='{self.os_release}'). Blocked."

        elif self.is_mac:
            try:
                mac_ver_str = platform.mac_ver()[0]
                if not mac_ver_str:
                    raise ValueError("empty mac_ver string")
                major = int(mac_ver_str.split(".")[0])
                if major >= 11:
                    passed  = True
                else:
                    message = (
                        f"Unsupported macOS version: {mac_ver_str}. "
                        "Require macOS 11 or higher."
                    )
            except (ValueError, IndexError, AttributeError):
                passed  = False
                message = "Cannot determine macOS version. Blocked."
        else:
            message = "Unsupported Operating System."

        return {"passed": passed, "message": message}

    # Virtual machine detection

    def detect_virtual_machine(self):
        """
        Detect virtualization indicators.

        Evidence tiers:
          hard_detected: firmware, disk, registry, or MAC evidence sufficient to block.
          cpuid_hint: hypervisor CPUID signal (supporting evidence).
          mac_flags: soft host-adapter hints reported without hard block.
        """
        hard_detected = False
        cpuid_hint    = False
        flags         = []
        mac_flags     = []

        if self.is_windows:
            # CPUID hypervisor bit via native helper (soft indicator).
            if _antitamper_dll:
                try:
                    with _antitamper_lock:
                        hyp = _antitamper_dll.check_hypervisor()
                    if hyp == 1:
                        cpuid_hint = True
                        flags.append("CPUID hypervisor bit set (Hyper-V root partition or VM).")
                    elif hyp < 0:
                        flags.append(f"CPUID check error {hyp}.")
                except Exception as e:
                    flags.append(f"CPUID check exception: {e}")
            else:
                flags.append("anti_tamper.dll absent — CPUID hypervisor check unavailable.")

            # WMI BIOS/firmware model/vendor inspection.
            try:
                c              = wmi.WMI()
                system_info    = c.Win32_ComputerSystem()[0]
                bios_info      = c.Win32_BIOS()[0]
                baseboard_info = c.Win32_BaseBoard()[0]

                manufacturer  = (system_info.Manufacturer   or "").lower()
                model         = (system_info.Model           or "").lower()
                bios_version  = (bios_info.Version           or "").lower()
                baseboard_mfg = (baseboard_info.Manufacturer or "").lower()

                combined   = f"{manufacturer} {model} {bios_version} {baseboard_mfg}"
                VM_FIRMWARE = ["vmware", "virtualbox", "qemu", "xen", "bochs", "prl", "parallels"]
                for ind in VM_FIRMWARE:
                    if ind in combined:
                        hard_detected = True
                        flags.append(f"Firmware/SMBIOS indicates VM: '{ind}' in ({combined.strip()})")
                        break
                if not hard_detected and "microsoft corporation" in combined:
                    if "virtual" in model or "virtual" in bios_version:
                        hard_detected = True
                        flags.append("Firmware/SMBIOS indicates Hyper-V guest.")
            except Exception as e:
                flags.append(f"WMI Firmware error: {e}")

            # Virtual disk-model indicators.
            try:
                c        = wmi.WMI()
                VM_DISKS = ["vbox", "vmware", "qemu", "virtual hd", "vmm", "hyper-v"]
                for disk in c.Win32_DiskDrive():
                    disk_model = str(disk.Model).lower()
                    if any(v in disk_model for v in VM_DISKS):
                        hard_detected = True
                        flags.append(f"Virtual disk detected: {disk.Model}")
            except Exception:
                pass

            # Registry keys commonly installed by guest additions/tools.
            VM_REG_KEYS = [
                (winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\ACPI\DSDT\VBOX__",                  "VirtualBox ACPI"),
                (winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\ACPI\FADT\VBOX__",                  "VirtualBox FADT"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VMware, Inc.\VMware Tools",          "VMware Tools (guest)"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Oracle\VirtualBox Guest Additions",  "VirtualBox Guest Additions"),
            ]
            for hkey, path, name in VM_REG_KEYS:
                try:
                    winreg.CloseKey(winreg.OpenKey(hkey, path))
                    hard_detected = True
                    flags.append(f"Registry key present: {name} ({path})")
                except FileNotFoundError:
                    pass

        # MAC-address OUI indicators.
        HARD_VM_MACS = [
            "00:05:69", "00:0c:29", "00:1c:14",   # VMware guest
            "08:00:27",                            # VirtualBox guest
            "00:16:3e",                            # Xen guest
            "52:54:00",                            # QEMU/KVM guest
            "00:15:5d",                            # Hyper-V guest
        ]
        SOFT_VM_MACS = ["00:50:56"]   # VMware host-only (VMnet) — warn only

        try:
            if psutil:
                for iface, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if not _mac_family_is_link(int(addr.family)):
                            continue
                        raw = addr.address or ""
                        if not raw or raw in ("", "00:00:00:00:00:00"):
                            continue
                        mac = raw.lower().replace("-", ":")
                        for prefix in HARD_VM_MACS:
                            if mac.startswith(prefix):
                                hard_detected = True
                                flags.append(f"VM guest MAC on '{iface}': {mac} ({prefix})")
                                break
                        else:
                            for prefix in SOFT_VM_MACS:
                                if mac.startswith(prefix):
                                    mac_flags.append(
                                        f"VMware host adapter on '{iface}': {mac} "
                                        "(VMware installed on host — not inside VM)"
                                    )
                                    break
        except Exception as e:
            flags.append(f"MAC scan error: {e}")

        # CPUID alone is not conclusive on modern Windows host configurations.
        if cpuid_hint and hard_detected:
            flags.insert(0, "CPUID hypervisor bit corroborated by other VM indicators — confirmed VM.")
        elif cpuid_hint and not hard_detected:
            # Likely Hyper-V root partition (bare metal with VMware/WSL2/Docker installed)
            mac_flags.append("CPUID hypervisor bit set but no other VM indicators — likely Hyper-V root partition.")

        return {
            "detected":    hard_detected,
            "cpuid_hint":  cpuid_hint,
            "flags":       flags,
            "mac_hints":   mac_flags,
        }

    # RDP and remote-session detection

    def detect_rdp_sessions(self):
        """
        Detect RDP/remote-control execution context.

        Uses multiple indicators including SM_REMOTESESSION, session-ID
        comparison, and known remote-control process heuristics.
        """
        detected = False
        flags    = []

        if not self.is_windows:
            return {"detected": detected, "flags": flags}

        try:
            # SM_REMOTESESSION metric.
            if ctypes.windll.user32.GetSystemMetrics(0x1000) != 0:
                detected = True
                flags.append("GetSystemMetrics(SM_REMOTESESSION) indicates active RDP session.")
        except AttributeError:
            pass

        try:
            # Compare active console session to current process session.
            kernel32 = ctypes.windll.kernel32
            console_session_id = kernel32.WTSGetActiveConsoleSessionId()

            our_session_id = ctypes.c_ulong(0)
            kernel32.ProcessIdToSessionId(
                kernel32.GetCurrentProcessId(),
                ctypes.byref(our_session_id)
            )

            if our_session_id.value != console_session_id:
                detected = True
                flags.append(
                    f"Process session ID ({our_session_id.value}) != "
                    f"console session ID ({console_session_id}) — "
                    "process is running inside an RDP/remote session."
                )
        except Exception as e:
            flags.append(f"WTS session comparison error: {e}")

        try:
            # Process heuristic for common remote-control clients.
            remote_procs = {
                "teamviewer.exe", "anydesk.exe", "tvnserver.exe",
                "mstsc.exe", "screenconnect.client.exe", "logmein.exe",
                "vncserver.exe", "rdpclip.exe", "ultravnc.exe",
                "supremo.exe", "rustdesk.exe", "ultraviewer.exe",
            }
            if psutil:
                for p in psutil.process_iter(["name"]):
                    name = (p.info["name"] or "").lower()
                    if name in remote_procs:
                        detected = True
                        flags.append(f"Remote control software running: {name}")
        except Exception as e:
            flags.append(f"Process list failure: {e}")

        return {"detected": detected, "flags": flags}

    # Sandbox and analysis-environment detection

    def detect_sandbox(self):
        """
        Detect sandbox and dynamic-analysis environments.

        Combines process, registry, module, username, memory, and timing
        indicators for broad analysis-environment coverage.
        """
        detected = False
        flags    = []

        if not self.is_windows:
            return {"detected": detected, "flags": flags}

        # Sandbox/analysis process indicators.
        SANDBOX_PROCS = {
            # Windows Sandbox
            "vmsrvc.exe", "vmusrvc.exe",
            # Sandboxie
            "sandboxiedcomlaunch.exe", "sandboxierpcss.exe", "sbieinj.exe",
            "sbiesvc.exe", "sbiesvcr.exe", "sboxs.exe",
            # Cuckoo
            "cuckoomon.dll", "analyzer.py", "cuckoo.py",
            # ANY.RUN
            "anyrun.exe",
            # Joe Sandbox / automated analysis
            "joeboxcontrol.exe", "joeboxserver.exe",
            # Generic VM/sandbox helpers
            "vboxservice.exe", "vboxtray.exe",     # VirtualBox guest additions
            "vmtoolsd.exe", "vmwaretray.exe",       # VMware guest tools
            "prl_cc.exe", "prl_tools.exe",          # Parallels
            "xenservice.exe",                        # Xen
            "qemu-ga.exe",                           # QEMU Guest Agent
            # Analysis / behaviour monitoring
            "capemon.dll", "wpespy.dll", "pstorec.dll",
            "apimonitor.exe", "wireshark.exe",
            "fakenet.exe", "inetclnt.dll",
        }

        try:
            if psutil:
                running = {(p.info["name"] or "").lower() for p in psutil.process_iter(["name"])}
                for proc in SANDBOX_PROCS:
                    if proc in running:
                        detected = True
                        flags.append(f"Sandbox process running: {proc}")
        except Exception:
            pass

        # Common sandbox account names.
        SANDBOX_USERS = {
            "wdagutilityaccount",   # Windows Sandbox
            "sandbox",
            "cuckoo",
            "virus",
            "malware",
            "analysis",
            "test",
        }
        try:
            username = (os.environ.get("USERNAME") or "").lower()
            if username in SANDBOX_USERS:
                detected = True
                flags.append(f"Sandbox username detected: {username}")
        except Exception:
            pass

        # Sandbox-related registry footprints.
        SANDBOX_REG = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Sandboxie-Plus", "Sandboxie-Plus"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\SbieDrv", "Sandboxie Driver"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\tzuk\Sandboxie", "Sandboxie (old)"),
        ]
        for hkey, path, name in SANDBOX_REG:
            try:
                winreg.CloseKey(winreg.OpenKey(hkey, path))
                detected = True
                flags.append(f"Sandbox registry key found: {name} ({path})")
            except FileNotFoundError:
                pass

        # Sandboxie module injection artifact.
        try:
            if ctypes.windll.kernel32.GetModuleHandleA(b"SbieDll.dll"):
                detected = True
                flags.append("SbieDll.dll loaded into process — Sandboxie active.")
        except Exception:
            pass

        # Low-memory heuristic.
        try:
            if psutil:
                total_gb = psutil.virtual_memory().total / (1024 ** 3)
                if total_gb < 1.5:
                    detected = True
                    flags.append(f"Very low RAM ({total_gb:.1f} GB) — may indicate sandbox.")
        except Exception:
            pass

        # Timing artifact check (computed once to avoid repeated overhead).
        if not self._sandbox_sleep0_timing_checked:
            self._sandbox_sleep0_timing_checked = True
            try:
                import timeit
                self._sandbox_sleep0_timing_value = timeit.timeit(
                    "ctypes.windll.kernel32.Sleep(0)",
                    setup="import ctypes", number=50
                )
            except Exception:
                self._sandbox_sleep0_timing_value = None

        t = self._sandbox_sleep0_timing_value
        if t is not None and t > 0.25:
            flags.append(f"Suspicious Sleep(0) latency ({t:.2f}s/50 calls) — possible emulation.")
            # Report-only signal due to potential false positives under load.

        return {"detected": detected, "flags": flags}

    # Clock integrity

    def check_clock_integrity(self, threshold_seconds: float = 60.0) -> dict:
        """
        Compare local clock with NTP time and flag large drift.

        If absolute offset exceeds threshold_seconds, result is marked tampered.

        Returns:
          { tampered: bool, offset_seconds: float|None, message: str }
        """
        offset = _ntp_offset_seconds()

        if offset is None:
            return {
                "tampered":       False,   # Fail open when NTP is unreachable.
                "offset_seconds": None,
                "message":        "NTP query failed (network may be blocked) — skipped.",
            }

        abs_offset = abs(offset)
        tampered   = abs_offset > threshold_seconds
        direction  = "ahead" if offset > 0 else "behind"
        message    = (
            f"Clock is {abs_offset:.1f}s {direction} of NTP time."
            + (" TIME MANIPULATION SUSPECTED." if tampered else "")
        )

        return {
            "tampered":       tampered,
            "offset_seconds": round(offset, 2),
            "message":        message,
        }
