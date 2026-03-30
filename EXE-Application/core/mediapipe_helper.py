"""Resolve MediaPipe model resources across development and bundled runtimes.

This module centralizes lookup logic for face_landmarker.task so the same
code path works in source execution and PyInstaller-packaged executables.
"""

import os
import sys
from pathlib import Path


def get_mediapipe_model_path(model_filename: str = "face_landmarker.task") -> str:
    """
    Locate a MediaPipe model file across known runtime locations.

    Search order:
    1. Current working directory
    2. Script directory (source/development runs)
    3. sys._MEIPASS (PyInstaller extraction directory)
    4. Module directory (core package)
    5. Parent of module directory (project root-style layout)

    Args:
        model_filename: Model filename to locate.

    Returns:
        Absolute path to the first matching model file.

    Raises:
        FileNotFoundError: If no candidate path contains the model file.
    """
    candidate_paths: list[str] = []

    # 1. Current working directory
    candidate_paths.append(str(Path.cwd() / model_filename))

    # 2. Script directory (development/source invocation path).
    if hasattr(sys, 'argv') and sys.argv[0]:
        script_dir = Path(os.path.abspath(sys.argv[0])).parent
        candidate_paths.append(str(script_dir / model_filename))

    # 3. PyInstaller extraction directory for bundled executables.
    if hasattr(sys, '_MEIPASS'):
        candidate_paths.append(str(Path(sys._MEIPASS) / model_filename))

    # 4. Module directory (core package path).
    module_dir = Path(__file__).resolve().parent
    candidate_paths.append(str(module_dir / model_filename))

    # 5. Parent directory (project layout where core is a subfolder).
    candidate_paths.append(str(module_dir.parent / model_filename))

    # Deduplicate while preserving order
    search_paths = list(dict.fromkeys(os.path.abspath(path) for path in candidate_paths))

    for path in search_paths:
        if os.path.isfile(path):
            return path

    possible_locations = "\n  - ".join(search_paths) if search_paths else "No search paths evaluated"
    raise FileNotFoundError(
        f"MediaPipe model file '{model_filename}' not found. "
        f"Searched:\n  - {possible_locations}\n"
        f"Ensure face_landmarker.task is included in the build."
    )


def ensure_mediapipe_resources():
    """
    Check MediaPipe resource availability at startup.

    Returns a tuple: (is_available, detail_message).
    """
    try:
        model_path = get_mediapipe_model_path()
        return True, f"MediaPipe model found at: {model_path}"
    except FileNotFoundError as e:
        return False, str(e)
