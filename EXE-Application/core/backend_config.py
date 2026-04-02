"""Backend endpoint resolution and production safety validation.

This module centralizes how the client resolves the backend URL from
environment variables and enforces strict runtime checks suitable for
production deployments.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

SERVER_URL_ENV_KEYS = ("OBSERVE_SERVER_URL", "OBSERVE_BACKEND_URL")
LIGHTNING_AI_ALLOWED_HOSTS = {
    "8080-01kj5bj93vmpxwpzf2ywa1k639.cloudspaces.litng.ai",
}


def _is_allowed_lightning_host(host: str) -> bool:
    """Return True when host belongs to the approved Lightning AI domain set.

    The allowlist supports explicit host entries and managed Lightning
    subdomains under litng.ai.
    """
    h = (host or "").strip().lower()
    if not h:
        return False
    if h in LIGHTNING_AI_ALLOWED_HOSTS:
        return True
    # Allow Lightning-managed public hosts while rejecting non-Lightning domains.
    return h == "litng.ai" or h.endswith(".litng.ai")


def _validate_lightning_ai_url(url: str) -> str:
    """Validate and normalize a configured backend URL.

    Enforced rules:
    - HTTPS only
    - no embedded credentials
    - hostname must resolve and belong to approved Lightning AI hosts

    Returns the URL without a trailing slash when valid.
    Raises RuntimeError when validation fails.
    """
    normalized = url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme.lower() != "https":
        raise RuntimeError("Backend URL must use HTTPS in production (set OBSERVE_SERVER_URL).")
    if parsed.username or parsed.password:
        raise RuntimeError("Backend URL must not include credentials.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise RuntimeError("Backend URL must include a valid host.")
    if not _is_allowed_lightning_host(host):
        raise RuntimeError("Backend URL must point to approved Lightning AI endpoint.")

    return normalized


def get_backend_url() -> str:
    """
    Resolve the backend URL used by the desktop client.

    Resolution order:
    1) OBSERVE_SERVER_URL  (new canonical env var)
    2) OBSERVE_BACKEND_URL (legacy compatibility)

    Security guarantees:
    - Fail closed when no URL is configured.
    - Require HTTPS URL for transport security.
    - Allow only approved Lightning AI hostnames.
    """
    for key in SERVER_URL_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if value:
            return _validate_lightning_ai_url(value)
    raise RuntimeError("Missing backend URL. Set OBSERVE_SERVER_URL for production startup.")

