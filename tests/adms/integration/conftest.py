"""
Pytest fixtures for ADMS end-to-end integration tests.

Tests target a real, running ADM instance on BTP. Configuration is read
from the standard secret-mount or env-var pattern used by every SDK module:

    CLOUD_SDK_CFG_ADMS_DEFAULT_URL          (IAS tenant URL)
    CLOUD_SDK_CFG_ADMS_DEFAULT_URI          (ADM service URL)
    CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTID     (IAS client id)
    CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTSECRET (IAS client secret)
    CLOUD_SDK_CFG_ADMS_DEFAULT_RESOURCE     (optional IAS resource)

When any required variable is missing, integration tests are skipped.
"""

from __future__ import annotations

import pytest
import requests as _requests

from sap_cloud_sdk.adms import create_client
from sap_cloud_sdk.adms.client import (
    AdmsClient,
    AsyncAdmsClient,
    create_async_client,
)
from sap_cloud_sdk.adms.config import AdmsConfig, load_from_env_or_mount
from sap_cloud_sdk.adms.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Configuration fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def adms_config() -> AdmsConfig:
    """Resolve AdmsConfig from env/secret-mount.

    Skips the entire integration suite when required credentials are missing.
    """
    try:
        return load_from_env_or_mount("default")
    except ConfigError as exc:
        pytest.skip(f"ADMS integration tests skipped — missing config: {exc}")


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def adms_client(adms_config: AdmsConfig) -> AdmsClient:
    """Sync AdmsClient wired to the real ADM instance."""
    return create_client(config=adms_config)


@pytest.fixture(scope="function")
def async_adms_client(adms_config: AdmsConfig) -> AsyncAdmsClient:
    """Async AdmsClient wired to the real ADM instance."""
    return create_async_client(config=adms_config)


# ---------------------------------------------------------------------------
# Pre-requisite: business object type ID
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def bo_type_id(adms_client: AdmsClient) -> str:
    """Return a BusinessObjectNodeType unique ID for use in tests.

    Reads the first available type from the ConfigurationService; creates
    a test type if none exist.
    """
    base = adms_client._http._config.service_url.rstrip("/")
    bearer = adms_client._http._token_fetcher.get_token()

    resp = _requests.get(
        f"{base}/odata/v4/ConfigurationService/BusinessObjectNodeType",
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("value", [])
    if data:
        return data[0]["BusinessObjectNodeTypeUniqueID"]

    csrf_resp = _requests.get(
        f"{base}/odata/v4/ConfigurationService/",
        headers={
            "Authorization": f"Bearer {bearer}",
            "X-CSRF-Token": "Fetch",
        },
        timeout=15,
    )
    csrf = csrf_resp.headers.get("X-CSRF-Token", "")

    create_resp = _requests.post(
        f"{base}/odata/v4/ConfigurationService/BusinessObjectNodeType",
        json={
            "BusinessObjectNodeTypeUniqueID": "PY_SDK_TEST_BO",
            "Description": "Created by Python SDK integration test",
        },
        headers={
            "Authorization": f"Bearer {bearer}",
            "X-CSRF-Token": csrf,
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    create_resp.raise_for_status()
    return "PY_SDK_TEST_BO"
