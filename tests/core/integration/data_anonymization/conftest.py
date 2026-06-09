"""Pytest configuration and fixtures for data anonymization integration tests."""

import os
from pathlib import Path
from typing import Dict, Iterator, NoReturn

import pytest
from _pytest.outcomes import Skipped
from dotenv import load_dotenv

from sap_cloud_sdk.core.data_anonymization import (
    DataAnonymizationConfig,
    create_client,
)


def _skip_test(reason: str) -> NoReturn:
    raise Skipped(reason)


@pytest.fixture(scope="session")
def integration_env() -> Dict[str, str]:
    """Load and validate integration test environment variables."""
    env_file = Path(__file__).parent.parent.parent.parent.parent / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    env_vars = {
        "url": os.getenv("CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_URL", "").strip(),
        "cert": os.getenv(
            "CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_CERT", ""
        ).strip(),
        "key": os.getenv(
            "CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_KEY", ""
        ).strip(),
        "cert_path": os.getenv(
            "CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_CERT_PATH", ""
        ).strip(),
        "key_path": os.getenv(
            "CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_KEY_PATH", ""
        ).strip(),
        "destination_name": os.getenv(
            "CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_DESTINATION_NAME", ""
        ).strip(),
    }

    if not env_vars["url"]:
        _skip_test(
            "Missing CLOUD_SDK_CFG_DATA_ANONYMIZATION_DEFAULT_URL for integration tests."
        )

    if env_vars["destination_name"]:
        return env_vars

    if env_vars["cert"] and env_vars["key"]:
        return env_vars

    if not env_vars["cert_path"] or not env_vars["key_path"]:
        _skip_test(
            "Missing Data Anonymization mTLS configuration. Set either cert/key values, cert/key paths, or destination name."
        )

    if not Path(env_vars["cert_path"]).exists():
        _skip_test(
            f"Data Anonymization certificate file not found: {env_vars['cert_path']}"
        )

    if not Path(env_vars["key_path"]).exists():
        _skip_test(f"Data Anonymization key file not found: {env_vars['key_path']}")

    return env_vars


@pytest.fixture(scope="session")
def data_anonymization_client(integration_env) -> Iterator[object]:
    """Create a real client for the Data Anonymization service."""
    config = DataAnonymizationConfig(
        service_url=integration_env["url"],
        cert=integration_env["cert"] or None,
        key=integration_env["key"] or None,
        cert_path=integration_env["cert_path"] or None,
        key_path=integration_env["key_path"] or None,
        destination_name=integration_env["destination_name"] or None,
    )
    try:
        client = create_client(config=config)
        yield client
    finally:
        try:
            client.close()
        except Exception:
            pass


@pytest.fixture
def failure_simulation(integration_env):
    """Utilities for simulating failure conditions with explicit configuration."""

    class FailureSimulator:
        def create_client_with_network_failure(self):
            cfg = DataAnonymizationConfig(
                service_url="https://unreachable-data-anonymization.invalid",
                cert=integration_env["cert"] or None,
                key=integration_env["key"] or None,
                cert_path=integration_env["cert_path"] or None,
                key_path=integration_env["key_path"] or None,
                destination_name=integration_env["destination_name"] or None,
            )
            return create_client(config=cfg)

    return FailureSimulator()


def pytest_configure(config) -> None:
    """Register integration markers for BDD tests."""
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items) -> None:
    """Automatically mark integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
