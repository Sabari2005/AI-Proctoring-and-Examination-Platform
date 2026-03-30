"""Minimal .env loader with no third-party dependencies.

Loads the first available .env file from:
1. ENV_FILE env var (explicit path)
2. Same directory as sys.executable (frozen or EXE mode)
3. The directory passed as base_dir
4. Current working directory

Existing process environment variables are not overridden by default.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


def _strip_quotes(value: str) -> str:
    """Remove one pair of matching wrapping quotes from a value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _parse_env_lines(lines: Iterable[str]) -> dict[str, str]:
    """Parse .env lines into key/value pairs using simple shell-style rules."""
    parsed: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        parsed[key] = _strip_quotes(value)
    return parsed


def _candidate_env_paths(base_dir: str | None = None) -> list[Path]:
    """Return deduplicated candidate .env paths in load-priority order."""
    candidates: list[Path] = []

    explicit = os.environ.get("ENV_FILE", "").strip()
    if explicit:
        candidates.append(Path(explicit))

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")

    if base_dir:
        candidates.append(Path(base_dir).resolve() / ".env")

    candidates.append(Path.cwd() / ".env")

    seen: set[str] = set()
    unique: list[Path] = []
    for p in candidates:
        key = str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def load_env(base_dir: str | None = None, override: bool = False) -> str | None:
    """Load the first available .env file and return its path, else None."""
    for env_path in _candidate_env_paths(base_dir=base_dir):
        if not env_path.is_file():
            continue
        try:
            text = env_path.read_text(encoding="utf-8")
            parsed = _parse_env_lines(text.splitlines())
            for k, v in parsed.items():
                if override or k not in os.environ:
                    os.environ[k] = v
            print(f"[ENV] Loaded: {env_path}")
            return str(env_path)
        except Exception as exc:
            print(f"[ENV] Failed to load {env_path}: {exc}")
            continue
    return None
