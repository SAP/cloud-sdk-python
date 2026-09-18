"""Configuration and credential resolution for the CBC (Central Business Configuration) module.

Reads mTLS credentials for the CBC service from environment variables.

Environment variables::

    CLOUD_SDK_CBC_URL         CBC service base URL (required)
    CLOUD_SDK_CBC_CERT_PATH   Path to PEM client certificate file
    CLOUD_SDK_CBC_KEY_PATH    Path to PEM private key file
    CLOUD_SDK_CBC_CERT        PEM client certificate value (alternative to CERT_PATH)
    CLOUD_SDK_CBC_KEY         PEM private key value (alternative to KEY_PATH)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sap_cloud_sdk.cbc.exceptions import CBCConfigError

ENV_URL = "CLOUD_SDK_CBC_URL"
ENV_CERT_PATH = "CLOUD_SDK_CBC_CERT_PATH"
ENV_KEY_PATH = "CLOUD_SDK_CBC_KEY_PATH"
ENV_CERT = "CLOUD_SDK_CBC_CERT"
ENV_KEY = "CLOUD_SDK_CBC_KEY"
ENV_REPLACE_SUBDOMAIN = "CLOUD_SDK_CBC_REPLACE_SUBDOMAIN"


@dataclass(frozen=True)
class CBCConfig:
    """Resolved configuration for the CBC service.

    Attributes:
        base_url: CBC service base URL.
        cert_path: Path to the PEM client certificate file, or ``None`` when not using mTLS.
        key_path: Path to the PEM private key file, or ``None`` when not using mTLS.
        cert_pem: PEM client certificate value. Alternative to ``cert_path``.
        key_pem: PEM private key value. Alternative to ``key_path``.
        replace_subdomain: Whether to rewrite the URL subdomain to the CBC tenant ID
            on each request. Defaults to ``True``. Set to ``False`` when pointing
            at a local mock server (e.g. via ``CLOUD_SDK_CBC_REPLACE_SUBDOMAIN=false``).
    """

    base_url: str
    cert_path: Path | None = None
    key_path: Path | None = None
    cert_pem: str | None = None
    key_pem: str | None = None
    replace_subdomain: bool | None = None


def load_from_env() -> CBCConfig:
    """Load CBC configuration from environment variables.

    Resolution order (first match wins):

    1. **Path triplet** — ``CLOUD_SDK_CBC_CERT_PATH``, ``CLOUD_SDK_CBC_KEY_PATH``,
       and ``CLOUD_SDK_CBC_URL`` must all be set. The path vars must point to
       existing PEM files.
    2. **Value triplet** — ``CLOUD_SDK_CBC_CERT``, ``CLOUD_SDK_CBC_KEY``, and
       ``CLOUD_SDK_CBC_URL`` must all be set. PEM values are written to temp
       files deleted after the first connection.
    3. **URL only** — ``CLOUD_SDK_CBC_URL`` is set without credentials. No mTLS.

    Returns:
        A :class:`CBCConfig` ready for use by :func:`~sap_cloud_sdk.cbc.create_client`.

    Raises:
        CBCConfigError: If no configuration is found, or configuration is partially
            set and unusable — e.g. only one of the cert/key env vars is set, or a
            path env var points to a non-existent file.
    """
    url = os.environ.get(ENV_URL)
    replace_subdomain = _read_env_bool(ENV_REPLACE_SUBDOMAIN)

    cert_path = _read_env_path(ENV_CERT_PATH)
    key_path = _read_env_path(ENV_KEY_PATH)
    if cert_path and key_path and url:
        return CBCConfig(
            base_url=url,
            cert_path=cert_path,
            key_path=key_path,
            replace_subdomain=replace_subdomain,
        )
    if cert_path or key_path:
        raise CBCConfigError(
            "CBC env-var credential triplet is incomplete. "
            f"Set all of {ENV_CERT_PATH}, {ENV_KEY_PATH}, and {ENV_URL} — or none."
        )

    cert_pem = os.environ.get(ENV_CERT)
    key_pem = os.environ.get(ENV_KEY)
    if cert_pem and key_pem and url:
        return CBCConfig(
            base_url=url,
            cert_pem=cert_pem,
            key_pem=key_pem,
            replace_subdomain=replace_subdomain,
        )
    if cert_pem or key_pem:
        raise CBCConfigError(
            "CBC env-var credential pair is incomplete. "
            f"Set both {ENV_CERT} and {ENV_KEY} together with {ENV_URL} — or none."
        )

    if url:
        return CBCConfig(base_url=url, replace_subdomain=replace_subdomain)

    raise CBCConfigError(
        f"No CBC configuration found. Set {ENV_URL} at minimum, "
        f"or provide mTLS credentials via {ENV_CERT_PATH} / {ENV_KEY_PATH} "
        f"or {ENV_CERT} / {ENV_KEY}."
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
