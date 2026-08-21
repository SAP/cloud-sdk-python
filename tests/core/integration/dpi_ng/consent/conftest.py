"""Pytest configuration and fixtures for consent integration tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.core.dpi_ng.consent import (
    AuthProvider,
    BearerTokenAuth,
    ClientCertificateAuth,
    ClientCredentialsAuth,
    ConsentClient,
    ConsentConfig,
    create_client,
)

# __file__ is at tests/core/integration/dpi_ng/consent/conftest.py — 6 levels up to project root
_ENV_FILE = (
    Path(__file__).parent.parent.parent.parent.parent.parent / ".env_integration_tests"
)


def _resolve_auth() -> AuthProvider | None:
    if token := os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_BEARER_TOKEN"):
        return BearerTokenAuth(token)
    token_url = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_TOKEN_URL")
    client_id = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_CLIENT_ID")
    client_secret = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_CLIENT_SECRET")
    if token_url and client_id and client_secret:
        return ClientCredentialsAuth(
            token_url=token_url, client_id=client_id, client_secret=client_secret
        )
    cert_file = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_CERT_FILE")
    key_file = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_KEY_FILE")
    if cert_file and key_file:
        return ClientCertificateAuth(
            cert_file=cert_file,
            key_file=key_file,
            ca_file=os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_CA_FILE"),
        )
    return None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="module")
def live_client() -> Iterator[ConsentClient]:
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE, override=True)
    base_url = os.getenv("CLOUD_SDK_CFG_DPI_NG_DEFAULT_BASE_URL", "")
    auth = _resolve_auth()
    if not base_url or auth is None:
        pytest.skip(
            "No integration credentials in .env — set CLOUD_SDK_CFG_DPI_NG_DEFAULT_BASE_URL plus one auth flow"
        )
    tenant_id = os.getenv("CLOUD_SDK_CFG_DPI_NG_CONSENT_DEFAULT_TENANT_ID")
    config = ConsentConfig(base_url=base_url, auth=auth, tenant_id=tenant_id)
    with create_client(config=config) as client:
        yield client


@dataclass
class ConsentScenarioContext:
    client: Any = None
    result: Any = None
    last_error: Exception | None = None
    controller_id: str | None = None
    application_id: str | None = None
    jurisdiction_id: str | None = None
    data_subject_type_id: str | None = None
    third_party_id: str | None = None
    purpose_id: str | None = None
    template_id: str | None = None
    consent_ids: list = field(default_factory=list)


@pytest.fixture(scope="module")
def context() -> ConsentScenarioContext:
    return ConsentScenarioContext()
