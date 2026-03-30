#!/usr/bin/env python
"""
ObserveProctor Universal Builder
Builds the packaged desktop executable for production distribution.
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
import argparse
import urllib.request
from urllib.parse import urlparse
from env_loader import load_env

PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

MAIN_SCRIPT = PROJECT_ROOT / "main.py"

MODEL_FILE = PROJECT_ROOT / "face_landmarker.task"
MANIFEST_FILE = PROJECT_ROOT / "ObserveProctor.manifest"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
ICON_FILE = PROJECT_ROOT / "assets" / "app_icon.ico"
CORE_DIR = PROJECT_ROOT / "core"
REFERENCE_DIR = PROJECT_ROOT.parent / "references"
ANTI_TAMPER_DLL = CORE_DIR / "anti_tamper.dll"
ANTI_TAMPER_LIB = CORE_DIR / "anti_tamper.lib"
ANTI_TAMPER_C = CORE_DIR / "anti_tamper.c"
LIGHTNING_AI_ALLOWED_HOSTS = {
    "8080-01kj5bj93vmpxwpzf2ywa1k639.cloudspaces.litng.ai",
}


def _is_allowed_lightning_host(host: str) -> bool:
    h = (host or "").strip().lower()
    if not h:
        return False
    if h in LIGHTNING_AI_ALLOWED_HOSTS:
        return True
    return h == "litng.ai" or h.endswith(".litng.ai")

LOG_FILE = PROJECT_ROOT / "build_log.txt"

SEP = ";" if sys.platform == "win32" else ":"


# Logging

def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf8") as f:
        f.write(msg + "\n")


# Cleanup

def clean():

    log("[STEP] Cleaning old build files")

    for folder in ["build", "dist"]:
        p = PROJECT_ROOT / folder
        if p.exists():
            shutil.rmtree(p)

    for root, dirs, files in os.walk(PROJECT_ROOT):

        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(Path(root) / d)
                dirs.remove(d)

    log("[OK] Clean complete")


# Dependency installation

def install_requirements(backend):

    log("[STEP] Installing requirements")

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    )

    # Install backend-specific compiler toolchain.
    if backend == "nuitka":
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "nuitka", "ordered-set", "zstandard"]
        )
        # Keep fallback compiler available for reliability.
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"]
        )
    else:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"]
        )

    log("[OK] Dependencies installed")


# MediaPipe model handling

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


def ensure_model():

    log("[STEP] Checking MediaPipe model")

    if MODEL_FILE.exists():
        log("[OK] face_landmarker.task present")
        return

    log("[DOWNLOAD] Downloading model")

    urllib.request.urlretrieve(MODEL_URL, MODEL_FILE)

    log("[OK] Model downloaded")


# MediaPipe location

def locate_mediapipe():

    try:

        import mediapipe

        mp_dir = Path(mediapipe.__file__).parent

        log(f"[OK] MediaPipe found: {mp_dir}")

        return mp_dir

    except Exception:

        log("[WARN] MediaPipe not installed")

        return None


def ensure_anti_tamper_artifacts():
    """Copy required anti-tamper artifacts from references/ into core/."""
    log("[STEP] Ensuring anti-tamper artifacts")

    mappings = [
        (REFERENCE_DIR / "anti_tamper.dll", ANTI_TAMPER_DLL),
        (REFERENCE_DIR / "anti_tamper.lib", ANTI_TAMPER_LIB),
        (REFERENCE_DIR / "anti_tamper.c", ANTI_TAMPER_C),
    ]

    for src, dst in mappings:
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log(f"[OK] Copied {src.name} -> {dst}")

    if not ANTI_TAMPER_DLL.exists():
        log("[ERROR] anti_tamper.dll is required for strict production build.")
        log(f"[ERROR] Expected at: {ANTI_TAMPER_DLL}")
        sys.exit(1)

    log("[OK] anti_tamper.dll present")


def ensure_application_icon():
    """Ensure the ICO application icon is available for packaging."""
    log("[STEP] Checking application icon")

    if ICON_FILE.exists():
        log(f"[OK] Application icon found: {ICON_FILE}")
        return

    log("[WARN] Application icon not found")
    log(f"[WARN] Expected at: {ICON_FILE}")
    log("[INFO] To create icon from SVG:")
    log("       python create_icon.py")
    log("[INFO] Or use: https://convertio.co/svg-ico/")
    log("[INFO] Proceeding without custom icon (using default)")



def validate_production_env():
    """Fail closed when required production environment values are missing or weak."""
    log("[STEP] Validating production environment")

    backend_url = (os.environ.get("VIRTUSA_SERVER_URL") or os.environ.get("VIRTUSA_BACKEND_URL") or "").strip()
    if not backend_url:
        log("[ERROR] Missing VIRTUSA_SERVER_URL (or VIRTUSA_BACKEND_URL).")
        sys.exit(1)
    if not backend_url.lower().startswith("https://"):
        log("[ERROR] Backend URL must use HTTPS for production.")
        sys.exit(1)
    backend_host = (urlparse(backend_url).hostname or "").lower()
    if not _is_allowed_lightning_host(backend_host):
        log("[ERROR] Backend URL must point to approved Lightning AI endpoint host.")
        log(f"[ERROR] Got host: {backend_host or 'missing'}")
        sys.exit(1)

    secret = (os.environ.get("VIRTUSA_PROCTOR_SECRET") or "").strip()
    if not secret or secret == "dev-shared-secret-change-me" or len(secret) < 24:
        log("[ERROR] VIRTUSA_PROCTOR_SECRET must be set to a strong production value (min 24 chars).")
        sys.exit(1)

    log("[OK] Production env validation passed")


def validate_required_build_inputs():
    """Fail fast when required build inputs are missing."""
    log("[STEP] Validating required build inputs")

    required = [
        MAIN_SCRIPT,
        MODEL_FILE,
        MANIFEST_FILE,
        PROJECT_ROOT / "assets",
        ANTI_TAMPER_DLL,
        ENV_FILE,
    ]

    missing = [str(p) for p in required if not p.exists()]
    if missing:
        log("[ERROR] Missing required build input(s):")
        for p in missing:
            log(f"[ERROR]   - {p}")
        sys.exit(1)

    log("[OK] Required build inputs present")


# Build executable

def _prepare_output_exe():
    """Ensure dist/ObserveProctor.exe is not locked before executable build runs."""
    exe = DIST_DIR / "ObserveProctor.exe"

    if sys.platform == "win32":
        try:
            # Kill running packaged instances that can lock the output file.
            subprocess.run(
                ["taskkill", "/F", "/IM", "ObserveProctor.exe", "/T"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            pass

    if not exe.exists():
        return

    # Retry deletion to handle transient AV/indexer locks.
    for attempt in range(1, 11):
        try:
            exe.unlink()
            log("[OK] Cleared previous dist/ObserveProctor.exe")
            return
        except PermissionError:
            if attempt == 10:
                log("[ERROR] dist/ObserveProctor.exe is locked. Close running ObserveProctor.exe and retry.")
                raise
            time.sleep(0.4)
        except Exception:
            # Non-permission errors should fail immediately.
            raise

def _run_and_stream(args):
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if process.stdout is not None:
        for line in process.stdout:
            log(line.rstrip())

    process.wait()
    return process.returncode


def build_with_pyinstaller():
    log("[STEP] Starting PyInstaller build")

    _prepare_output_exe()

    mp_dir = locate_mediapipe()

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(MAIN_SCRIPT),
        "--name", "ObserveProctor",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--windowed",
        "--manifest", str(MANIFEST_FILE),
        "--log-level=WARN",
        "--paths", str(PROJECT_ROOT),
        "--collect-all", "mediapipe",
        "--collect-all", "cv2",
        "--collect-submodules", "PyQt6",
        "--hidden-import", "numpy",
        "--hidden-import", "psutil",
        "--hidden-import", "sounddevice",
        "--hidden-import", "cryptography",
        "--hidden-import", "requests",
        "--hidden-import", "wmi",
        "--hidden-import", "core.exam_api",
        "--hidden-import", "core.proctoring_service",
        "--hidden-import", "core.lockdown",
        "--hidden-import", "win32api",
        "--hidden-import", "win32con",
        "--hidden-import", "win32gui",
        "--hidden-import", "pythoncom",
        "--hidden-import", "pywintypes",
        "--add-data", f"{MODEL_FILE}{SEP}.",
        # Bundle .env inside the executable to reduce runtime tampering risk.
        "--add-data", f"{ENV_FILE}{SEP}.",
        "--add-data", f"{PROJECT_ROOT / 'assets'}{SEP}assets",
        "--add-binary", f"{ANTI_TAMPER_DLL}{SEP}core",
    ]

    if mp_dir:
        args.extend(["--add-data", f"{mp_dir}{SEP}mediapipe"])

    if ICON_FILE.exists():
        args.extend(["--icon", str(ICON_FILE)])

    rc = _run_and_stream(args)
    if rc != 0:
        log("[ERROR] Build failed")
        sys.exit(1)

    log("[OK] Build finished")


def build_with_nuitka():
    log("[STEP] Starting Nuitka build")

    _prepare_output_exe()
    locate_mediapipe()

    args = [
        sys.executable,
        "-m",
        "nuitka",
        str(MAIN_SCRIPT),
        "--onefile",
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--output-dir=" + str(DIST_DIR),
        "--output-filename=ObserveProctor.exe",
        "--windows-console-mode=disable",
        "--enable-plugin=pyqt6",
        "--include-package=core",
        "--include-module=core.exam_api",
        "--include-module=core.proctoring_service",
        "--include-module=core.lockdown",
        "--include-package-data=mediapipe",
        "--include-package-data=cv2",
        "--include-data-files=" + f"{MODEL_FILE}=face_landmarker.task",
        # Keep secure runtime config embedded into the onefile payload.
        "--include-data-files=" + f"{ENV_FILE}=.env",
        "--include-data-dir=" + f"{PROJECT_ROOT / 'assets'}=assets",
        "--include-data-files=" + f"{ANTI_TAMPER_DLL}=core/anti_tamper.dll",
    ]

    if ICON_FILE.exists():
        args.append("--windows-icon-from-ico=" + str(ICON_FILE))

    rc = _run_and_stream(args)
    if rc != 0:
        log("[ERROR] Nuitka build failed")
        return False

    log("[OK] Build finished")
    return True


def build(backend, allow_fallback=True):
    if backend == "nuitka":
        success = build_with_nuitka()
        if not success:
            if not allow_fallback:
                sys.exit(1)
            log("[WARN] Falling back to PyInstaller backend to preserve build reliability")
            build_with_pyinstaller()
        return

    build_with_pyinstaller()


# Output verification

def verify():

    exe = DIST_DIR / "ObserveProctor.exe"

    if not exe.exists():
        log("[ERROR] EXE not produced")
        sys.exit(1)

    size = exe.stat().st_size / (1024 * 1024)

    # .env is bundled into the executable; only .env.example is copied externally.

    if ENV_EXAMPLE_FILE.exists():
        shutil.copy2(ENV_EXAMPLE_FILE, DIST_DIR / ".env.example")

    required_outputs = [
        exe,
    ]
    missing_outputs = [str(p) for p in required_outputs if not p.exists()]
    if missing_outputs:
        log("[ERROR] Missing required build output(s):")
        for p in missing_outputs:
            log(f"[ERROR]   - {p}")
        sys.exit(1)

    log(f"[SUCCESS] EXE created: {exe} ({size:.1f} MB)")


# Main entry point

def main():
    load_env(base_dir=str(PROJECT_ROOT))

    parser = argparse.ArgumentParser()

    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--backend",
        choices=["nuitka", "pyinstaller"],
        default="nuitka",
        help="Compiler backend for building ObserveProctor.exe",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable automatic PyInstaller fallback when Nuitka fails",
    )

    args = parser.parse_args()

    LOG_FILE.write_text("ObserveProctor Build Log\n\n")

    if args.clean:
        clean()

    install_requirements(args.backend)

    ensure_model()

    ensure_anti_tamper_artifacts()

    ensure_application_icon()

    validate_production_env()

    validate_required_build_inputs()

    build(args.backend, allow_fallback=not args.no_fallback)

    verify()

    log("\nBuild completed successfully")


if __name__ == "__main__":
    main()