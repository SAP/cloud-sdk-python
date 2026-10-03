"""Pytest fixtures for CBC integration tests.

Tests target a real or mock CBC server. Configuration is read from env vars:

    CLOUD_SDK_CBC_URL              CBC service base URL (required)
    CLOUD_SDK_CBC_APP_TENANT_ID    Application tenant ID (required)
    CLOUD_SDK_CBC_CERT_PATH        Client certificate PEM path (optional, mTLS)
    CLOUD_SDK_CBC_KEY_PATH         Client private key PEM path (optional, mTLS)

When any required variable is missing, integration tests are skipped. The cert
and key paths are optional — supply both to test against an mTLS server; omit
them for a plain-HTTP mock.
"""

from __future__ import annotations

import os
import ssl

import pytest

from sap_cloud_sdk.cbc import CBCClient, create_client

ENV_URL = "CLOUD_SDK_CBC_URL"
ENV_APP_TENANT_ID = "CLOUD_SDK_CBC_APP_TENANT_ID"
ENV_CERT_PATH = "CLOUD_SDK_CBC_CERT_PATH"
ENV_KEY_PATH = "CLOUD_SDK_CBC_KEY_PATH"


def _require_app_tenant_id() -> str:
    app_tid = os.environ.get(ENV_APP_TENANT_ID)
    if not app_tid:
        pytest.skip(f"CBC integration tests skipped — set {ENV_APP_TENANT_ID}.")
    return app_tid


def _build_ssl_context() -> ssl.SSLContext | None:
    """Build an mTLS context from the cert/key path env vars, or None if unset."""
    cert_path = os.environ.get(ENV_CERT_PATH)
    key_path = os.environ.get(ENV_KEY_PATH)
    if not cert_path or not key_path:
        return None
    ctx = ssl.create_default_context()
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    return ctx


@pytest.fixture(scope="session")
def cbc_app_tenant_id() -> str:
    return _require_app_tenant_id()


@pytest.fixture(scope="session")
def cbc_client() -> CBCClient:
    app_tid = _require_app_tenant_id()
    url = os.environ.get(ENV_URL)
    if not url:
        pytest.skip(f"CBC integration tests skipped — set {ENV_URL}.")
    return create_client(
        base_url=lambda: url,
        app_tenant_id=lambda: app_tid,
        ssl_context=_build_ssl_context(),
    )
