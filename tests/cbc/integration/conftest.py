"""Pytest fixtures for CBC integration tests.

Tests target a real or mock CBC server. Configuration is read from env vars:

    CLOUD_SDK_CBC_URL              CBC service base URL (required)
    CLOUD_SDK_CBC_CBC_TENANT_ID    CBC tenant ID for subdomain routing (required)
    CLOUD_SDK_CBC_APP_TENANT_ID    Application tenant ID (required)
    CLOUD_SDK_CBC_CERT_PATH        Path to mTLS client certificate (optional)
    CLOUD_SDK_CBC_KEY_PATH         Path to mTLS private key (optional)
    CLOUD_SDK_CBC_REPLACE_SUBDOMAIN  Override subdomain replacement (optional)

When any required variable is missing, integration tests are skipped.
"""

from __future__ import annotations

import os

import pytest

from sap_cloud_sdk.cbc import DefaultClient, TenantContext, create_client
from sap_cloud_sdk.cbc.exceptions import CBCConfigError

ENV_CBC_TENANT_ID = "CLOUD_SDK_CBC_CBC_TENANT_ID"
ENV_APP_TENANT_ID = "CLOUD_SDK_CBC_APP_TENANT_ID"


@pytest.fixture(scope="session")
def cbc_tenant() -> TenantContext:
    cbc_tid = os.environ.get(ENV_CBC_TENANT_ID)
    app_tid = os.environ.get(ENV_APP_TENANT_ID)
    if not cbc_tid or not app_tid:
        pytest.skip(
            f"CBC integration tests skipped — set {ENV_CBC_TENANT_ID} and {ENV_APP_TENANT_ID}."
        )
    return TenantContext(cbcTenantId=cbc_tid, appTenantId=app_tid)


@pytest.fixture(scope="session")
def cbc_client() -> DefaultClient:
    try:
        return create_client()
    except CBCConfigError as exc:
        pytest.skip(f"CBC integration tests skipped — missing config: {exc}")
