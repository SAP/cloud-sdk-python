"""Configuration and credential resolution for the CBC (Central Business Configuration) module.

Reads mTLS credentials for the CBC service from environment variables.

Environment variables::

    CLOUD_SDK_CBC_URL         CBC service base URL (required)
    CLOUD_SDK_CBC_CERT_PATH   Path to PEM client certificate file
    CLOUD_SDK_CBC_KEY_PATH    Path to PEM private key file
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sap_cloud_sdk.cbc.exceptions import CBCConfigError

ENV_URL = "CLOUD_SDK_CBC_URL"
ENV_CERT_PATH = "CLOUD_SDK_CBC_CERT_PATH"
ENV_KEY_PATH = "CLOUD_SDK_CBC_KEY_PATH"
ENV_REPLACE_SUBDOMAIN = "CLOUD_SDK_CBC_REPLACE_SUBDOMAIN"


@dataclass(frozen=True)
class CBCConfig:
    """Resolved configuration for the CBC service.

    Attributes:
        base_url: CBC service base URL.
        cert_path: Path to the PEM client certificate file, or ``None`` for local/mock mode.
        key_path: Path to the PEM private key file, or ``None`` for local/mock mode.
        replace_subdomain: Whether to rewrite the URL subdomain to the CBC tenant ID
            on each request. ``None`` (default) auto-detects: loopback URLs disable it,
            all others enable it. Set explicitly to ``False`` for HTTPS mock servers.
    """

    base_url: str
    cert_path: Path | None = None
    key_path: Path | None = None
    replace_subdomain: bool | None = None


def load_from_env() -> CBCConfig:
    """Load CBC configuration from environment variables.

    Resolution order (first match wins):

    1. **Credential triplet** — ``CLOUD_SDK_CBC_CERT_PATH``,
       ``CLOUD_SDK_CBC_KEY_PATH``, and ``CLOUD_SDK_CBC_URL`` must all be set.
       The path vars must point to existing PEM files.
    2. **URL only** — loopback addresses (``http://localhost``,
       ``http://127.0.0.1``) trigger local/mock mode (no mTLS, no subdomain
       replacement). Non-loopback URLs produce a client without mTLS.

    Returns:
        A :class:`CBCConfig` ready for use by :func:`~sap_cloud_sdk.cbc.create_client`.

    Raises:
        CBCConfigError: If no configuration is found, or configuration is partially
            set and unusable — e.g. only one of the cert/key env vars is set, or a
            path env var points to a non-existent file.
    """
    url = os.environ.get(ENV_URL)

    cert = _read_env_path(ENV_CERT_PATH)
    key = _read_env_path(ENV_KEY_PATH)
    if cert and key and url:
        return CBCConfig(
            base_url=url,
            cert_path=cert,
            key_path=key,
            replace_subdomain=_read_env_bool(ENV_REPLACE_SUBDOMAIN),
        )
    if cert or key:
        raise CBCConfigError(
            "CBC env-var credential triplet is incomplete. "
            f"Set all of {ENV_CERT_PATH}, {ENV_KEY_PATH}, and {ENV_URL} — or none."
        )

    if url:
        return CBCConfig(base_url=url, replace_subdomain=_read_env_bool(ENV_REPLACE_SUBDOMAIN))

    raise CBCConfigError(
        f"No CBC configuration found. Set {ENV_URL} at minimum, "
        f"or provide mTLS credentials via {ENV_CERT_PATH} / {ENV_KEY_PATH}."
    )


def _read_env_bool(name: str) -> bool | None:
    """Return True/False from env var ``name``, or ``None`` when unset."""
    raw = os.environ.get(name)
    if not raw:
        return None
    return raw.strip().lower() in ("1", "true", "yes")


def _read_env_path(name: str) -> Path | None:
    """Return the path named by env var ``name``, or ``None`` when unset.

    Raises:
        CBCConfigError: If the env var is set but the path does not exist.
    """
    raw = os.environ.get(name)
    if not raw or not raw.strip():
        return None
    p = Path(raw).expanduser()
    if not p.exists():
        raise CBCConfigError(
            f"Env var {name}={raw!r} points to a path that does not exist."
        )
    return p
