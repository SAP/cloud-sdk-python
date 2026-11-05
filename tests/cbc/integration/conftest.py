"""Pytest fixtures for CBC integration tests.

Tests exercise the real default provisioning path: ``cbc.create_client()`` with
no overrides, resolving the CBC URL from the tenant-mapping Destination Fragment
and the mTLS certificate from the Destination Service — the same way the
agentgateway integration tests drive ``create_client``.

Configuration is read from the environment (optionally from a
``.env_integration_tests`` file at the repo root, loaded automatically):

    # Destination Service binding (standard SDK convention, instance "default")
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTSECRET
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URL
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_URI
    CLOUD_SDK_CFG_DESTINATION_DEFAULT_IDENTITYZONE

    # CBC tenant to target (the client reads these from the runtime context)
    CLOUD_SDK_CFG_CBC_DEFAULT_APP_TENANT_ID    IAS app_tid of the subscriber tenant
    CLOUD_SDK_CFG_CBC_DEFAULT_TENANT_SUBDOMAIN subscriber subdomain (selects the fragment)

    # landscape, used to derive the mTLS certificate name
    CLOUD_SDK_CFG_CBC_DEFAULT_LANDSCAPE        -> APPFND_CONHOS_LANDSCAPE

When the binding or the tenant values are missing, integration tests skip.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.cbc import CBCClient, create_client
from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, DWC_SUBDOMAIN
from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, set_context

ENV_APP_TENANT_ID = "CLOUD_SDK_CFG_CBC_DEFAULT_APP_TENANT_ID"
ENV_TENANT_SUBDOMAIN = "CLOUD_SDK_CFG_CBC_DEFAULT_TENANT_SUBDOMAIN"
ENV_LANDSCAPE = "CLOUD_SDK_CFG_CBC_DEFAULT_LANDSCAPE"
ENV_DESTINATION_CLIENT_ID = "CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID"


def _setup_cloud_mode() -> None:
    """Load environment variables from .env_integration_tests if present."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)


def _require_app_tenant_id() -> str:
    app_tid = os.environ.get(ENV_APP_TENANT_ID)
    if not app_tid:
        pytest.skip(f"CBC integration tests skipped — set {ENV_APP_TENANT_ID}.")
    return app_tid


@pytest.fixture(scope="session")
def cbc_app_tenant_id() -> str:
    _setup_cloud_mode()
    return _require_app_tenant_id()


@pytest.fixture
def cbc_client() -> CBCClient:
    """Build the client via the default provisioning path (no overrides).

    Seeds the SDK runtime context with the subscriber tenant id and subdomain —
    what ``bootstrap(app)`` would populate from an incoming request — then lets
    ``create_client()`` resolve the URL and mTLS certificate from the Destination
    Service, exactly as it does in production.
    """
    _setup_cloud_mode()

    if not os.environ.get(ENV_DESTINATION_CLIENT_ID):
        pytest.skip(
            f"CBC integration tests skipped — set the Destination binding "
            f"({ENV_DESTINATION_CLIENT_ID} and friends)."
        )
    app_tid = _require_app_tenant_id()
    subdomain = os.environ.get(ENV_TENANT_SUBDOMAIN)
    if not subdomain:
        pytest.skip(f"CBC integration tests skipped — set {ENV_TENANT_SUBDOMAIN}.")

    landscape = os.environ.get(ENV_LANDSCAPE)
    if landscape:
        os.environ.setdefault("APPFND_CONHOS_LANDSCAPE", landscape)

    set_context(RuntimeContext({APP_TENANT_ID: app_tid, DWC_SUBDOMAIN: subdomain}))
    return create_client()
