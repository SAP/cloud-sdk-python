"""Pytest configuration and fixtures for Agent Gateway integration tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.agentgateway import create_client, AgentGatewayClient
from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError


def _setup_cloud_mode():
    """Load environment variables from .env_integration_tests if present."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)


@pytest.fixture(scope="session")
def agw_client() -> AgentGatewayClient:
    """Create an AgentGatewayClient from environment variables."""
    _setup_cloud_mode()

    tenant_subdomain = os.environ.get("CLOUD_SDK_CFG_AGW_DEFAULT_TENANT_SUBDOMAIN")
    if not tenant_subdomain:
        pytest.skip("CLOUD_SDK_CFG_AGW_DEFAULT_TENANT_SUBDOMAIN is not set — skipping AGW integration tests")

    landscape = os.environ.get("CLOUD_SDK_CFG_AGW_DEFAULT_LANDSCAPE")
    if landscape:
        os.environ.setdefault("APPFND_CONHOS_LANDSCAPE", landscape)

    try:
        return create_client(tenant_subdomain=tenant_subdomain)
    except MCPServerNotFoundError as e:
        pytest.skip(f"AGW not subscribed for this tenant — skipping AGW integration tests: {e}")
    except Exception as e:
        pytest.fail(f"Failed to create Agent Gateway client for integration tests: {e}")


# Configure pytest markers for integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


def pytest_runtest_call(item):
    """Skip AGW tests that fail due to missing subscription."""
    try:
        item.runtest()
    except MCPServerNotFoundError as e:
        pytest.skip(f"AGW not subscribed for this tenant — skipping: {e}")
