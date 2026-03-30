"""
Deep virtual-camera detection via Windows SetupAPI.

This module inspects camera-class devices using manufacturer, friendly name,
hardware bus signature, and USB Vendor ID (VID) heuristics.

The goal is to identify software-virtualized camera endpoints that imitate
real devices through display names or driver metadata.
"""

import ctypes
import platform
import threading
from ctypes import wintypes

if platform.system() == "Windows":
    setupapi = ctypes.windll.setupapi

    class SP_DEVINFO_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize",    wintypes.DWORD),
            ("ClassGuid", ctypes.c_byte * 16),
            ("DevInst",   wintypes.DWORD),
            ("Reserved",  ctypes.POINTER(ctypes.c_ulong)),
        ]

    DIGCF_PRESENT    = 0x00000002
    SPDRP_HARDWAREID = 0x00000001
    SPDRP_MFG        = 0x0000000B
    SPDRP_FRIENDLYNAME = 0x0000000C


# Known real USB camera vendor IDs (USB\VID_XXXX).
# Virtual cameras generally do not expose a genuine USB VID.
REAL_CAMERA_USB_VIDS = {
    # Logitech
    "046d",
    # Microsoft (LifeCam family)
    "045e",
    # Realtek (integrated laptops)
    "0bda",
    # Sunplus (HP/Lenovo embedded cams)
    "04f2",
    # IMC (Lenovo ThinkPad)
    "13d3",
    # Chicony (Dell, HP laptops)
    "04f2", "04ca",
    # Azurewave (ASUS)
    "0408",
    # Quanta (HP EliteBook)
    "0408",
    # Apple FaceTime
    "05ac",
    # Razer Kiyo
    "1532",
    # Elgato / Corsair
    "0fd9",
    # Brio / StreamCam (Logitech high-end)
    "046d",
    # Sony (PS Eye, VAIO cams)
    "054c",
    # Canon
    "04a9",
    # Nikon
    "04b0",
    # Samsung
    "04e8",
    # HTC
    "0bb4",
    # Lenovo integrated
    "17ef",
    # Dell (MediaTek-based)
    "0a12",
    # Generic UVC (widely used in cheap cams)
    "1e4e", "1b3f", "2b3e",
    # Intel RealSense
    "8086",
    # Ricoh (Pentax)
    "05ca",
}

# Known virtual-camera software keywords.
VIRTUAL_MFG_KEYWORDS = [
    "obs", "virtual", "xsplit", "snap camera", "manycam",
    "splitcam", "iriun", "droidcam", "epoccam", "reincubate",
    "logi capture", "dev1", "e2eSoft", "creative virtual",
]

# Hardware ID bus prefixes typically used by real camera hardware.
REAL_BUS_PREFIXES = ("usb\\", "uvc\\", "acpi\\", "pci\\", "sd\\")

_setupapi_lock = threading.Lock()


def _get_device_property(device_info_set, devinfo_data, prop_type) -> str:
    if platform.system() != "Windows":
        return ""

    buf_size = wintypes.DWORD(0)
    setupapi.SetupDiGetDeviceRegistryPropertyW(
        device_info_set, ctypes.byref(devinfo_data), prop_type,
        None, None, 0, ctypes.byref(buf_size)
    )
    if buf_size.value == 0:
        return ""

    buf = ctypes.create_unicode_buffer(buf_size.value // 2)
    setupapi.SetupDiGetDeviceRegistryPropertyW(
        device_info_set, ctypes.byref(devinfo_data), prop_type,
        None, buf, buf_size, None
    )
    return buf.value


def _extract_vid(hw_id: str) -> str | None:
    """
        Extract lowercase USB Vendor ID from a hardware ID string.

        Example:
            "USB\\VID_046D&PID_085B\\..." -> "046d"

        Returns None when no VID is present.
    """
    import re
    m = re.search(r"vid[_&]([0-9a-f]{4})", hw_id.lower())
    return m.group(1) if m else None


def detect_virtual_cameras_deep() -> dict:
    """
        Probe imaging devices via SetupAPI and flag suspicious virtual-camera traits.

        Heuristics:
        1) Manufacturer/friendly-name keyword match for known virtual camera tools.
        2) Hardware bus signature validation (real cameras typically expose USB/UVC/ACPI/PnP paths).
        3) USB VID extraction and allowlist validation for likely physical hardware.

        Returns a dictionary with detection boolean and descriptive flags.
    """
    if platform.system() != "Windows":
        return {"detected": False, "flags": ["SetupAPI deep check requires Windows."]}

    detected = False
    flags    = []

    # KSCATEGORY_CAPTURE GUID: {65E8773D-8F56-11D0-A3B9-00A0C9223196}
    guid_bytes = bytes([
        0x3D, 0x77, 0xE8, 0x65,
        0x56, 0x8F,
        0xD0, 0x11,
        0xA3, 0xB9,
        0x00, 0xA0, 0xC9, 0x22, 0x31, 0x96,
    ])

    with _setupapi_lock:
        h_devinfo = setupapi.SetupDiGetClassDevsW(guid_bytes, None, None, DIGCF_PRESENT)
        if h_devinfo == -1:
            return {"detected": False, "flags": ["SetupDiGetClassDevs failed."]}

        devinfo_data = SP_DEVINFO_DATA()
        devinfo_data.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)

        idx = 0
        while setupapi.SetupDiEnumDeviceInfo(h_devinfo, idx, ctypes.byref(devinfo_data)):
            mfg           = _get_device_property(h_devinfo, devinfo_data, SPDRP_MFG)
            friendly_name = _get_device_property(h_devinfo, devinfo_data, SPDRP_FRIENDLYNAME)
            hw_id         = _get_device_property(h_devinfo, devinfo_data, SPDRP_HARDWAREID)

            mfg_l  = mfg.lower()
            fn_l   = friendly_name.lower()
            hwid_l = hw_id.lower()
            vid    = _extract_vid(hwid_l)

            # Check 1: known virtual-camera keyword signal.
            if any(v in mfg_l or v in fn_l for v in VIRTUAL_MFG_KEYWORDS):
                detected = True
                flags.append(
                    f"Virtual camera software detected via SetupAPI: "
                    f"name='{friendly_name}' mfg='{mfg}' hwid='{hw_id}'"
                )
                idx += 1
                continue

            # Check 2: bus signature validation.
            # Real cameras usually expose usb/uvc/acpi/pci-style identifiers.
            real_bus = any(hwid_l.startswith(p) for p in REAL_BUS_PREFIXES)
            if not real_bus:
                detected = True
                flags.append(
                    f"Virtual camera: no real hardware bus in HWID "
                    f"name='{friendly_name}' hwid='{hw_id}'"
                )
                idx += 1
                continue

            # Check 3: USB VID validation against known physical-camera vendors.
            if vid is None:
                # Bus-like ID without VID remains suspicious.
                detected = True
                flags.append(
                    f"Camera with bus but no USB VID (synthetic HW ID): "
                    f"name='{friendly_name}' hwid='{hw_id}'"
                )
            elif vid not in REAL_CAMERA_USB_VIDS:
                # Unknown VID is flagged for review, not hard blocked.
                flags.append(
                    f"Camera with unrecognised USB VID 0x{vid}: "
                    f"name='{friendly_name}' mfg='{mfg}' hwid='{hw_id}'"
                )

            idx += 1

        setupapi.SetupDiDestroyDeviceInfoList(h_devinfo)
    return {"detected": detected, "flags": flags}
