"""Hardware and peripheral validation for exam runtime.

This module performs startup checks for baseline system capacity, display
topology, and media devices, and also provides a background watcher for
mid-session USB or monitor topology changes.
"""

import platform
import ctypes
import os
import threading
import time

import psutil

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from screeninfo import get_monitors
except ImportError:
    get_monitors = None

from .setupapi_cam import detect_virtual_cameras_deep


def _import_wmi():
    """Lazily import wmi for Windows-only code paths."""
    import wmi as _wmi
    return _wmi


def _import_winreg():
    """Lazily import winreg for Windows-only code paths."""
    import winreg as _winreg
    return _winreg


class HardwareChecker:
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        # Optional callback invoked for watcher events: (event_type, detail).
        self.alert_callback = None
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self._state_lock = threading.RLock()

    def run_all_checks(self) -> dict:
        """Run all hardware validation checks and return results dict."""
        results = {
            "performance":   self.check_system_performance(),
            "monitors":      self.check_monitors(),
            "media_devices": self.enumerate_media_devices(),
        }
        results["client_raw_hw_safe"] = (
            results["performance"]["passed"]
            and results["monitors"]["passed"]
            and results["media_devices"]["passed"]
        )
        return results

    # System performance

    def check_system_performance(self) -> dict:
        """Verify baseline system capacity (CPU, RAM, disk)."""
        passed = True
        flags  = []

        mem         = psutil.virtual_memory()
        free_ram_gb = mem.available / (1024 ** 3)
        total_ram_gb = mem.total / (1024 ** 3)
        if free_ram_gb < 2.0:
            passed = False
            flags.append(f"Insufficient free RAM: {free_ram_gb:.2f} GB (total: {total_ram_gb:.2f} GB)")

        core_count    = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)
        logical_count = psutil.cpu_count(logical=True)
        if core_count and core_count < 2:
            passed = False
            flags.append(f"Insufficient CPU cores: {core_count} (require ≥ 2)")

        drive = "C:\\" if self.is_windows else "/"
        try:
            free_disk_gb = psutil.disk_usage(drive).free / (1024 ** 3)
            if free_disk_gb < 5.0:
                passed = False
                flags.append(f"Insufficient disk space: {free_disk_gb:.2f} GB free on {drive}")
        except Exception as e:
            flags.append(f"Disk check error: {e}")

        return {
            "passed":      passed,
            "cores":       core_count,
            "threads":     logical_count,
            "free_ram_gb": round(free_ram_gb, 2),
            "flags":       flags,
        }

    # Monitor topology

    def check_monitors(self) -> dict:
        """
        Enumerate connected displays and flag multi-monitor configurations.

        This method is used at startup and periodically by the continuous
        hardware watcher.
        """
        passed        = True
        flags         = []
        monitor_count = 0
        details       = []

        if get_monitors:
            try:
                monitors      = get_monitors()
                monitor_count = len(monitors)
                details       = [f"{m.width}x{m.height} @({m.x},{m.y})" for m in monitors]

                # Compare data sources to catch potential display topology anomalies.
                if self.is_windows:
                    sm_count = ctypes.windll.user32.GetSystemMetrics(80)
                    if sm_count != monitor_count:
                        flags.append(
                            f"Display topology mismatch: OS reports {sm_count}, "
                            f"screeninfo detects {monitor_count} — possible HW splitter/Miracast."
                        )

                if monitor_count > 1:
                    passed = False
                    flags.append(f"Multiple monitors detected: {monitor_count} connected.")
            except Exception as e:
                flags.append(f"screeninfo error: {e}")
        else:
            # Fallback to Windows API when screeninfo is unavailable.
            if self.is_windows:
                monitor_count = ctypes.windll.user32.GetSystemMetrics(80)
                if monitor_count > 1:
                    passed = False
                    flags.append(f"Multiple monitors (SM_CMONITORS): {monitor_count}")
            else:
                flags.append("Could not load screeninfo to check monitors.")

        return {
            "passed":  passed,
            "count":   monitor_count,
            "details": details,
            "flags":   flags,
        }

    # Media devices

    def enumerate_media_devices(self) -> dict:
        """
        Enumerate camera/microphone devices and detect virtualization indicators.

        Camera validation combines WMI inventory with deeper SetupAPI checks.
        Microphone validation flags known virtual-audio device patterns.
        """
        passed     = True
        flags      = []
        camera_info = []
        mic_info   = []

        # Camera checks
        if self.is_windows:
            try:
                wmi = _import_wmi()
                c   = wmi.WMI()
                # Query both classes for broader Windows version compatibility.
                all_cams = (
                    list(c.Win32_PnPEntity(PNPClass="Image")) +
                    list(c.Win32_PnPEntity(PNPClass="Camera"))
                )
                camera_info = [d.Name for d in all_cams if d.Name]

                if not camera_info:
                    passed = False
                    flags.append("No webcam found in system PnP registry.")
                else:
                    # Name-based scan is supplemental to hardware-ID validation.
                    VIRTUAL_NAME_KW = [
                        "obs", "virtual", "snap camera", "xsplit", "manycam",
                        "splitcam", "iriun", "droidcam", "epoccam",
                    ]
                    for d in all_cams:
                        name_l = (d.Name or "").lower()
                        if any(kw in name_l for kw in VIRTUAL_NAME_KW):
                            passed = False
                            flags.append(f"Virtual camera name detected (WMI): {d.Name}")

                # Deep validation path: SetupAPI hardware VID and bus checks.
                deep = detect_virtual_cameras_deep()
                if deep.get("detected"):
                    passed = False
                flags.extend(deep.get("flags", []))

            except Exception as e:
                flags.append(f"WMI camera enumeration error: {e}")

        # Microphone checks
        if sd:
            try:
                input_count = 0
                for dev in sd.query_devices():
                    if dev["max_input_channels"] > 0:
                        input_count += 1
                        name_l = dev["name"].lower()
                        mic_info.append(dev["name"])
                        VIRTUAL_AUDIO_KW = [
                            "virtual audio cable", "vac ", "voicemeeter",
                            "obs virtual", "blackhole", "soundflower",
                            "vb-audio", "virtual microphone", "cable output",
                        ]
                        if any(kw in name_l for kw in VIRTUAL_AUDIO_KW):
                            passed = False
                            flags.append(f"Virtual audio device detected: {dev['name']}")

                if input_count == 0:
                    passed = False
                    flags.append("No active microphone detected.")
            except Exception as e:
                flags.append(f"SoundDevice error: {e}")
        else:
            flags.append("sounddevice not available for audio check.")

        return {
            "passed":      passed,
            "cameras":     camera_info,
            "microphones": mic_info,
            "flags":       flags,
        }

    # Continuous USB and monitor watcher

    def start_continuous_monitor(self, alert_callback=None):
        """
                Start a background watcher for mid-session hardware changes.

                Event callback signature:
                        callback(event_type: str, detail: dict)

                Supported event types:
                - "usb_inserted"
                - "monitor_changed"
        """
        with self._state_lock:
            self.alert_callback = alert_callback
            if self._monitor_thread and self._monitor_thread.is_alive():
                return
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._watch_loop,
                daemon=True,
                name="HW-Watcher",
            )
            self._monitor_thread.start()
        print("[HW] Continuous USB + monitor watcher started.")

    def stop_continuous_monitor(self):
        """Stop the background hardware watcher thread."""
        self._stop_event.set()
        with self._state_lock:
            thread = self._monitor_thread

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.5)

        with self._state_lock:
            if self._monitor_thread is thread and (thread is None or not thread.is_alive()):
                self._monitor_thread = None

    def _get_usb_device_set(self) -> set:
        """Return a set of currently enumerated USB device identifiers."""
        result = set()
        try:
            if self.is_windows:
                winreg = _import_winreg()
                key_path = r"SYSTEM\CurrentControlSet\Enum\USB"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as base:
                    i = 0
                    while True:
                        try:
                            vid_name = winreg.EnumKey(base, i)
                            try:
                                with winreg.OpenKey(base, vid_name) as vid_key:
                                    j = 0
                                    while True:
                                        try:
                                            pid_name = winreg.EnumKey(vid_key, j)
                                            result.add(f"{vid_name}\\{pid_name}")
                                            j += 1
                                        except OSError:
                                            break
                            except OSError:
                                pass
                            i += 1
                        except OSError:
                            break
        except Exception:
            # Fallback proxy when registry enumeration is unavailable.
            try:
                result = {d.device for d in psutil.disk_partitions()}
            except Exception:
                pass
        return result

    def _watch_loop(self):
        """Poll hardware state and emit callbacks for relevant topology changes."""
        try:
            prev_usb      = self._get_usb_device_set()
            prev_monitors = self.check_monitors()["count"]
        except Exception:
            prev_usb      = set()
            prev_monitors = 1

        USB_POLL_INTERVAL = 4     # seconds between USB checks
        MON_POLL_INTERVAL = 5     # seconds between monitor checks
        last_mon_check    = time.time()

        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=USB_POLL_INTERVAL):
                break

            # USB change detection
            try:
                cur_usb = self._get_usb_device_set()
                new_devs = cur_usb - prev_usb
                if new_devs:
                    detail = {
                        "new_devices": sorted(new_devs),
                        "timestamp":   time.time(),
                    }
                    print(f"[HW] USB device(s) inserted mid-exam: {sorted(new_devs)}")
                    with self._state_lock:
                        callback = self.alert_callback
                    if callback:
                        try:
                            callback("usb_inserted", detail)
                        except Exception:
                            pass
                prev_usb = cur_usb
            except Exception as e:
                print(f"[HW] USB watcher error: {e}")

            # Monitor change detection
            now = time.time()
            if now - last_mon_check >= MON_POLL_INTERVAL:
                last_mon_check = now
                try:
                    cur_mon = self.check_monitors()
                    cur_count = cur_mon["count"]
                    if cur_count != prev_monitors:
                        detail = {
                            "previous": prev_monitors,
                            "current":  cur_count,
                            "passed":   cur_mon["passed"],
                            "flags":    cur_mon["flags"],
                            "timestamp": now,
                        }
                        print(f"[HW] Monitor count changed mid-exam: {prev_monitors} → {cur_count}")
                        with self._state_lock:
                            callback = self.alert_callback
                        if callback:
                            try:
                                callback("monitor_changed", detail)
                            except Exception:
                                pass
                    prev_monitors = cur_count
                except Exception as e:
                    print(f"[HW] Monitor watcher error: {e}")

        with self._state_lock:
            if self._monitor_thread is threading.current_thread():
                self._monitor_thread = None
