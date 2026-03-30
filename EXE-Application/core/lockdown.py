"""Windows exam-session lockdown controls.

Provides keyboard shortcut interception, selected shell-policy mitigations,
Task Manager restrictions, and watchdogs for accessibility keyboard surfaces
and newly attached keyboard devices during a locked session.
"""

from __future__ import annotations
import atexit
import ctypes
from ctypes import wintypes
import platform
import psutil
import threading
import time
import winreg
from typing import Optional

# Initialize Windows-specific constants and APIs only on Windows.
if platform.system() == "Windows":
    user32   = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WH_KEYBOARD_LL = 13
    WM_KEYDOWN     = 0x0100
    WM_SYSKEYDOWN  = 0x0104
    WM_QUIT        = 0x0012

    # Virtual-key constants referenced by the hook handler.
    VK_TAB     = 0x09
    VK_SPACE   = 0x20
    VK_F4      = 0x73
    VK_F11     = 0x7A
    VK_SHIFT   = 0x10
    VK_CONTROL = 0x11
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_MENU    = 0x12   # Alt
    VK_ESCAPE  = 0x1B
    VK_LWIN    = 0x5B
    VK_RWIN    = 0x5C
    VK_UP      = 0x26
    VK_DOWN    = 0x28
    VK_LEFT    = 0x25
    VK_RIGHT   = 0x27
    VK_D       = 0x44
    VK_E       = 0x45
    VK_L       = 0x4C
    VK_R       = 0x52
    VK_S       = 0x53
    VK_X       = 0x58

    LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
    HHOOK = wintypes.HANDLE

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode",      wintypes.DWORD),
            ("scanCode",    wintypes.DWORD),
            ("flags",       wintypes.DWORD),
            ("time",        wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
        ]

    BlockInput = user32.BlockInput
    BlockInput.argtypes = [wintypes.BOOL]
    BlockInput.restype  = wintypes.BOOL

    RIM_TYPEKEYBOARD = 1

    class RAWINPUTDEVICELIST(ctypes.Structure):
        _fields_ = [
            ("hDevice", ctypes.c_void_p),
            ("dwType", ctypes.c_ulong),
        ]

    # Explicit ctypes signatures avoid return truncation on 64-bit builds.
    user32.SetWindowsHookExW.argtypes = [wintypes.INT, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = HHOOK
    user32.CallNextHookEx.argtypes = [HHOOK, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = [HHOOK]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD


def _get_raw_keyboard_devices() -> set:
    """
    Return a set of HANDLE values for raw-input keyboard devices.
    Used to detect new keyboard devices attached mid-exam.
    """
    if platform.system() != "Windows":
        return set()
    try:
        count = ctypes.c_uint(0)
        user32.GetRawInputDeviceList(
            None,
            ctypes.byref(count),
            ctypes.sizeof(RAWINPUTDEVICELIST),
        )
        if count.value == 0:
            return set()

        arr = (RAWINPUTDEVICELIST * count.value)()
        user32.GetRawInputDeviceList(
            arr,
            ctypes.byref(count),
            ctypes.sizeof(RAWINPUTDEVICELIST),
        )
        return {
            arr[i].hDevice
            for i in range(count.value)
            if arr[i].dwType == RIM_TYPEKEYBOARD
        }
    except Exception:
        return set()


# Registry-level mitigations

_TASKMGR_KEY  = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
_SAS_KEY      = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
_TOUCHPAD_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PrecisionTouchPad"
_EXPLORER_ADVANCED_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
_EXPLORER_POLICIES_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
_orig_taskmgr : Optional[int] = None
_orig_sas     : Optional[int] = None
_orig_touchpad_values: dict[str, Optional[int]] = {}
_orig_disabled_hotkeys: Optional[str] = None
_orig_explorer_policy_values: dict[str, Optional[int]] = {}
_orig_explorer_advanced_values: dict[str, Optional[int]] = {}
_registry_state_lock = threading.RLock()


def _apply_registry_mitigations():
    """
    Apply registry mitigations used during active lockdown.

    Changes include disabling Task Manager and restricting software-initiated
    Secure Attention Sequence generation. Previous values are cached for restore.
    """
    global _orig_taskmgr, _orig_sas
    if platform.system() != "Windows":
        return

    with _registry_state_lock:
        # Disable Task Manager for the current user.
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _TASKMGR_KEY,
                                0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                try:
                    _orig_taskmgr, _ = winreg.QueryValueEx(k, "DisableTaskMgr")
                except FileNotFoundError:
                    _orig_taskmgr = None
                winreg.SetValueEx(k, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        except Exception as e:
            print(f"[Lockdown] Could not disable Task Manager via registry: {e}")

        # Restrict software-generated SAS events.
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _SAS_KEY,
                                0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                try:
                    _orig_sas, _ = winreg.QueryValueEx(k, "SoftwareSASGeneration")
                except FileNotFoundError:
                    _orig_sas = None
                winreg.SetValueEx(k, "SoftwareSASGeneration", 0, winreg.REG_DWORD, 0)
        except Exception as e:
            print(f"[Lockdown] Could not set SoftwareSASGeneration: {e}")


def _restore_registry_mitigations():
    """Restore registry settings changed by _apply_registry_mitigations."""
    global _orig_taskmgr, _orig_sas
    if platform.system() != "Windows":
        return

    with _registry_state_lock:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _TASKMGR_KEY,
                                0, winreg.KEY_SET_VALUE) as k:
                if _orig_taskmgr is None:
                    try:
                        winreg.DeleteValue(k, "DisableTaskMgr")
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(k, "DisableTaskMgr", 0, winreg.REG_DWORD, _orig_taskmgr)
        except Exception:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _SAS_KEY,
                                0, winreg.KEY_SET_VALUE) as k:
                if _orig_sas is None:
                    try:
                        winreg.DeleteValue(k, "SoftwareSASGeneration")
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(k, "SoftwareSASGeneration", 0, winreg.REG_DWORD, _orig_sas)
        except Exception:
            pass

        _orig_taskmgr = None
        _orig_sas = None


def _apply_touchpad_mitigations():
    """
    Apply best-effort precision touchpad gesture restrictions.

    Intended to reduce gesture-based shell escapes (for example task view or
    desktop switching shortcuts). Values are restored on unlock.
    """
    global _orig_touchpad_values, _orig_disabled_hotkeys
    if platform.system() != "Windows":
        return

    touchpad_values = (
        "ThreeFingerSlideEnabled",
        "ThreeFingerTapEnabled",
        "FourFingerSlideEnabled",
        "FourFingerTapEnabled",
    )

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _TOUCHPAD_KEY) as k:
            for name in touchpad_values:
                try:
                    current, _ = winreg.QueryValueEx(k, name)
                    _orig_touchpad_values[name] = int(current)
                except FileNotFoundError:
                    _orig_touchpad_values[name] = None
                except Exception:
                    _orig_touchpad_values[name] = None
                try:
                    winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, 0)
                except Exception:
                    pass
    except Exception as e:
        print(f"[Lockdown] Could not apply touchpad mitigations: {e}")

    # Defense-in-depth: disable selected Win+ shell hotkeys.
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_ADVANCED_KEY) as k:
            try:
                existing, _ = winreg.QueryValueEx(k, "DisabledHotkeys")
                _orig_disabled_hotkeys = str(existing)
            except FileNotFoundError:
                _orig_disabled_hotkeys = None
                existing = ""
            except Exception:
                existing = ""

            chars = {c for c in str(existing).upper() if c.isalpha()}
            chars.update(set("DELRSX"))
            updated = "".join(sorted(chars))
            winreg.SetValueEx(k, "DisabledHotkeys", 0, winreg.REG_SZ, updated)
    except Exception as e:
        print(f"[Lockdown] Could not set DisabledHotkeys: {e}")


def _apply_shell_lockdown_mitigations(strict_mode: bool = False):
    """
    Apply shell-level policy restrictions during lockdown.

    strict_mode enables broader restrictions intended to reduce desktop/task
    switching escape paths while the exam lock is active.
    """
    global _orig_explorer_policy_values, _orig_explorer_advanced_values
    if platform.system() != "Windows":
        return

    # Disable shell Win+ hotkeys globally while locked.
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_POLICIES_KEY) as k:
            try:
                current, _ = winreg.QueryValueEx(k, "NoWinKeys")
                _orig_explorer_policy_values["NoWinKeys"] = int(current)
            except FileNotFoundError:
                _orig_explorer_policy_values["NoWinKeys"] = None
            winreg.SetValueEx(k, "NoWinKeys", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"[Lockdown] Could not set NoWinKeys policy: {e}")

    # Hide Task View entry points from the taskbar while locked.
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_ADVANCED_KEY) as k:
            for name, value in (("ShowTaskViewButton", 0), ("TaskbarDa", 0)):
                try:
                    current, _ = winreg.QueryValueEx(k, name)
                    _orig_explorer_advanced_values[name] = int(current)
                except FileNotFoundError:
                    _orig_explorer_advanced_values[name] = None
                try:
                    winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)
                except Exception:
                    pass

            if strict_mode:
                # Keep shell UI minimal while strict lock is active.
                for name in ("TaskbarMn", "ShowCortanaButton"):
                    try:
                        current, _ = winreg.QueryValueEx(k, name)
                        _orig_explorer_advanced_values[name] = int(current)
                    except FileNotFoundError:
                        _orig_explorer_advanced_values[name] = None
                    try:
                        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, 0)
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Lockdown] Could not apply explorer advanced lockdown values: {e}")


def _restore_touchpad_mitigations():
    """Restore touchpad and DisabledHotkeys values changed on lock."""
    global _orig_touchpad_values, _orig_disabled_hotkeys
    if platform.system() != "Windows":
        return

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _TOUCHPAD_KEY) as k:
            for name, original in _orig_touchpad_values.items():
                try:
                    if original is None:
                        winreg.DeleteValue(k, name)
                    else:
                        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(original))
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    _orig_touchpad_values = {}

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_ADVANCED_KEY) as k:
            if _orig_disabled_hotkeys is None:
                try:
                    winreg.DeleteValue(k, "DisabledHotkeys")
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(k, "DisabledHotkeys", 0, winreg.REG_SZ, _orig_disabled_hotkeys)
    except Exception:
        pass
    _orig_disabled_hotkeys = None

def _restore_shell_lockdown_mitigations():
    """Restore shell policy values changed during lockdown."""
    global _orig_explorer_policy_values, _orig_explorer_advanced_values
    if platform.system() != "Windows":
        return

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_POLICIES_KEY) as k:
            for name, original in _orig_explorer_policy_values.items():
                try:
                    if original is None:
                        winreg.DeleteValue(k, name)
                    else:
                        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(original))
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    _orig_explorer_policy_values = {}

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _EXPLORER_ADVANCED_KEY) as k:
            for name, original in _orig_explorer_advanced_values.items():
                try:
                    if original is None:
                        winreg.DeleteValue(k, name)
                    else:
                        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(original))
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    _orig_explorer_advanced_values = {}


class KeyboardLocker:
    """
    Manage Windows keyboard lockdown lifecycle for exam sessions.

    Uses a low-level keyboard hook plus optional policy mitigations and
    watchdog threads to reduce common shell escape paths.
    """
    
    def __init__(self):
        self.hook_id      = None
        self.locked       = False
        self._state_lock  = threading.RLock()
        self._block_input_engaged = False
        self._hook_ready = threading.Event()
        self._hook_install_error = ""
        self._hook_proc   = None      # Keep callback reference to prevent GC.
        self._win32_tid   = 0         # Win32 thread ID for message-post shutdown.
        self._known_kbd_devs: set = set()
        self.thread       = None
        self._osk_thread: Optional[threading.Thread] = None
        self._usb_watchdog_thread: Optional[threading.Thread] = None
        self._stop_event  = threading.Event()
        
        # Strict touchpad mode periodically reapplies touchpad mitigations.
        self._strict_touchpad_lockdown = False
        self._touchpad_refresh_thread: Optional[threading.Thread] = None
        self._touchpad_refresh_stop = threading.Event()
        self._strict_os_lockdown = False
        self._lifecycle_in_progress = False

        # Ensure best-effort unlock on interpreter exit.
        atexit.register(self._emergency_unlock)

    def _low_level_keyboard_handler(self, nCode, wParam, lParam):
        """Low-level keyboard hook callback that blocks restricted key chords."""
        if nCode == 0:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk  = kbd.vkCode

            is_alt  = bool(user32.GetAsyncKeyState(VK_MENU)    & 0x8000)
            is_ctrl = bool(
                user32.GetAsyncKeyState(VK_CONTROL) & 0x8000 or
                user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000 or
                user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000
            )
            is_shift = bool(user32.GetAsyncKeyState(VK_SHIFT)  & 0x8000)
            is_win  = bool(user32.GetAsyncKeyState(VK_LWIN)    & 0x8000 or
                           user32.GetAsyncKeyState(VK_RWIN)    & 0x8000)

            # Block Alt-based shell/window switching combinations.
            if is_alt and vk == VK_TAB:    return 1
            if is_alt and vk == VK_ESCAPE: return 1
            if is_alt and vk == VK_F4:     return 1
            if is_alt and vk == VK_SPACE:  return 1

            # Block Ctrl-based shell access combinations.
            if is_ctrl and vk == VK_ESCAPE: return 1
            if is_ctrl and is_shift and vk == VK_ESCAPE: return 1

            # Block Ctrl+Win virtual-desktop shortcuts.
            if is_ctrl and is_win and vk in {VK_D, VK_LEFT, VK_RIGHT, VK_F4}:
                return 1

            # Block Windows key and selected Win-key combinations.
            if vk in (VK_LWIN, VK_RWIN):  return 1
            if is_win:
                BLOCKED_WIN = {
                    VK_TAB, VK_D, VK_E, VK_L, VK_R,
                    VK_S, VK_X, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_F4, VK_SPACE,
                }
                if vk in BLOCKED_WIN:
                    return 1
                if self._strict_os_lockdown:
                    # Strict mode: suppress all Win-key combinations.
                    return 1

            if self._strict_os_lockdown and is_alt:
                # Strict mode: block broad Alt combinations used for shell/window switching.
                if vk in {VK_TAB, VK_ESCAPE, VK_F4, VK_SPACE, VK_F11}:
                    return 1

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _start_message_loop(self):
        """Install keyboard hook and run message pump on the same thread."""
        # Capture Win32 thread ID from inside the hook thread.
        self._win32_tid = kernel32.GetCurrentThreadId()

        self._hook_proc = HOOKPROC(self._low_level_keyboard_handler)
        # For WH_KEYBOARD_LL in-process usage, NULL hMod is valid and often
        # works more reliably than an explicit module handle in frozen builds.
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            None,
            0,
        )

        if not self.hook_id:
            # Retry once with explicit process module handle.
            self.hook_id = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._hook_proc,
                kernel32.GetModuleHandleW(None),
                0,
            )

        if not self.hook_id:
            err = int(kernel32.GetLastError() or ctypes.get_last_error() or 0)
            self._hook_install_error = f"SetWindowsHookExW failed (GetLastError={err})"
            print(f"[Lockdown] Failed to install keyboard hook: {self._hook_install_error}")
            with self._state_lock:
                self.locked = False
            self._hook_ready.set()
            return

        print("[Lockdown] Keyboard hook installed. System shortcuts disabled.")
        self._hook_ready.set()

        msg = wintypes.MSG()
        while self.locked and not self._stop_event.is_set():
            bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if bRet <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
        print("[Lockdown] Hook removed.")

    def _osk_watchdog(self):
        """Terminate explicit on-screen keyboard surfaces while locked."""
        # Restrict to explicit on-screen keyboard processes only.
        OSK_PROCS = {"osk.exe", "tabtip.exe"}
        while self.locked and not self._stop_event.is_set():
            try:
                for proc in psutil.process_iter(["name", "pid"]):
                    name = (proc.info["name"] or "").lower()
                    if name in OSK_PROCS:
                        proc.kill()
                        print(f"[Lockdown] Killed on-screen keyboard: {name} (PID {proc.info['pid']})")
            except Exception:
                pass
            time.sleep(2)

    def _usb_kbd_watchdog(self):
        """Detect keyboard devices attached after lockdown starts."""
        while self.locked and not self._stop_event.is_set():
            try:
                current = _get_raw_keyboard_devices()
                new_devices = current - self._known_kbd_devs
                if new_devices:
                    print(
                        f"[Lockdown] WARNING: {len(new_devices)} new keyboard device(s) detected mid-exam"
                    )
                    # Extend baseline so the same device does not repeatedly alert.
                    self._known_kbd_devs = current
            except Exception:
                pass
            time.sleep(4)

    def _touchpad_refresh_watchdog(self):
        """Re-apply touchpad mitigations periodically during strict mode."""
        while self.locked and not self._touchpad_refresh_stop.is_set():
            try:
                _apply_touchpad_mitigations()
                print("[Lockdown] Touchpad mitigations refreshed (strict mode)")
            except Exception:
                pass
            time.sleep(5)

    def lock_keyboard(
        self,
        use_block_input: bool = True,
        strict_touchpad: bool = False,
        strict_os: bool = False,
    ) -> bool:
        """
                Enter lockdown mode and start mitigation/watchdog components.

                Sequence:
                1) Apply registry and shell/touchpad mitigations.
                2) Optionally engage BlockInput.
                3) Install low-level keyboard hook thread.
                4) Start OSK and USB-keyboard watchdogs.
                5) Optionally start strict touchpad refresh watchdog.
        """
        if platform.system() != "Windows":
            return False

        with self._state_lock:
            if self.locked or self._lifecycle_in_progress:
                return False
            self._lifecycle_in_progress = True
            self.locked = True

        self._stop_event.clear()
        self._hook_ready.clear()
        with self._state_lock:
            self._hook_install_error = ""
        self._known_kbd_devs = _get_raw_keyboard_devices()
        self._strict_touchpad_lockdown = strict_touchpad
        self._strict_os_lockdown = strict_os
        self._touchpad_refresh_stop.clear()

        # Apply registry and shell-level mitigations.
        _apply_registry_mitigations()
        _apply_touchpad_mitigations()
        _apply_shell_lockdown_mitigations(strict_mode=strict_os)

        # Optional BlockInput: enabled only when explicitly requested.
        self._block_input_engaged = False
        if use_block_input:
            try:
                BlockInput(True)
                self._block_input_engaged = True
            except Exception as e:
                print(f"[Lockdown] BlockInput failed: {e}")

        # Start hook thread as daemon to avoid orphaning on abrupt process exit.
        self.thread = threading.Thread(
            target=self._start_message_loop,
            daemon=True,
            name="KB-Hook",
        )
        self.thread.start()

        # Wait briefly for hook install result for reliable fail-closed behavior.
        self._hook_ready.wait(timeout=2.0)
        with self._state_lock:
            still_locked = self.locked
        if not still_locked:
            if self._block_input_engaged:
                try:
                    BlockInput(False)
                except Exception:
                    pass
                self._block_input_engaged = False
            _restore_touchpad_mitigations()
            _restore_shell_lockdown_mitigations()
            _restore_registry_mitigations()
            with self._state_lock:
                self._lifecycle_in_progress = False
            return False

        # Start watchdogs.
        self._osk_thread = threading.Thread(
            target=self._osk_watchdog,
            daemon=True,
            name="OSK-Watchdog",
        )
        self._osk_thread.start()

        self._usb_watchdog_thread = threading.Thread(
            target=self._usb_kbd_watchdog,
            daemon=True,
            name="USB-KB-Watchdog",
        )
        self._usb_watchdog_thread.start()

        if strict_touchpad:
            self._touchpad_refresh_thread = threading.Thread(
                target=self._touchpad_refresh_watchdog,
                daemon=True,
                name="Touchpad-Refresh-Watchdog",
            )
            self._touchpad_refresh_thread.start()

        with self._state_lock:
            self._lifecycle_in_progress = False
        return True

    def unlock_keyboard(self):
        """
                Exit lockdown mode and restore modified OS state.

                This stops watchdog threads, removes hook/blocking state, and restores
                registry/policy values captured during lock activation.
        """
        with self._state_lock:
            if not self.locked or self._lifecycle_in_progress:
                return
            self._lifecycle_in_progress = True
            self.locked = False
            hook_thread = self.thread
            touchpad_thread = self._touchpad_refresh_thread
            osk_thread = self._osk_thread
            usb_thread = self._usb_watchdog_thread
        self._stop_event.set()
        self._touchpad_refresh_stop.set()
        if touchpad_thread and touchpad_thread.is_alive() and touchpad_thread is not threading.current_thread():
            touchpad_thread.join(timeout=1.0)
        self._touchpad_refresh_thread = None

        # Re-enable input if this lock session engaged BlockInput.
        if self._block_input_engaged:
            try:
                BlockInput(False)
            except Exception:
                pass
            self._block_input_engaged = False

        # Post WM_QUIT using the hook thread's Win32 thread ID.
        if self._win32_tid:
            user32.PostThreadMessageW(self._win32_tid, WM_QUIT, 0, 0)

        if hook_thread and hook_thread.is_alive() and hook_thread is not threading.current_thread():
            hook_thread.join(timeout=3)

        # Fallback: force unhook if message loop did not unhook in time.
        if self.hook_id:
            try:
                user32.UnhookWindowsHookEx(self.hook_id)
            except Exception:
                pass
            self.hook_id = None

        if osk_thread and osk_thread.is_alive() and osk_thread is not threading.current_thread():
            osk_thread.join(timeout=1.0)
        if usb_thread and usb_thread.is_alive() and usb_thread is not threading.current_thread():
            usb_thread.join(timeout=1.0)

        with self._state_lock:
            self.thread = None
            self._osk_thread = None
            self._usb_watchdog_thread = None
            self._touchpad_refresh_thread = None
            self._strict_touchpad_lockdown = False
            self._strict_os_lockdown = False
            self._lifecycle_in_progress = False

        # Restore system settings changed during lock.
        _restore_touchpad_mitigations()
        _restore_shell_lockdown_mitigations()
        _restore_registry_mitigations()
        print("[Lockdown] Keyboard unlocked.")

    def _emergency_unlock(self):
        """
        Best-effort atexit cleanup.

        Ensures hook/input/policy state is restored when process exits.
        """
        try:
            with self._state_lock:
                self.locked = False
                self._lifecycle_in_progress = False
            if self.hook_id:
                user32.UnhookWindowsHookEx(self.hook_id)
                self.hook_id = None
            BlockInput(False)
            _restore_touchpad_mitigations()
            _restore_shell_lockdown_mitigations()
            _restore_registry_mitigations()
        except Exception:
            pass

    def is_locked(self) -> bool:
        """Returns True if keyboard is currently locked."""
        with self._state_lock:
            return self.locked

    def get_last_error(self) -> str:
        """Return last hook installation/runtime error, if any."""
        with self._state_lock:
            return self._hook_install_error
