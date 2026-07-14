"""Integration test fixtures for the Agent Memory service.

Set the following environment variables before running integration tests:

    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_URL          Base URL of the Agent Memory service
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_AUTH_URL     OAuth2 authorization server base URL
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTID     OAuth2 client ID
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTSECRET OAuth2 client secret

Multitenancy:

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT   Subscriber tenant subdomain
        Required for SUBSCRIBER_ONLY tests. When absent those tests are skipped.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.agent_memory import AccessStrategy, create_client
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError


@pytest.fixture(scope="session")
def agent_memory_client() -> AgentMemoryClient:
    """Create a real AgentMemoryClient from environment variables.

    Uses PROVIDER_ONLY as the default strategy — individual BDD steps override
    this per-call to exercise both PROVIDER_ONLY and SUBSCRIBER_ONLY scenarios.
    """
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    try:
        return create_client(access_strategy=AccessStrategy.PROVIDER_ONLY)
    except AgentMemoryConfigError as e:
        pytest.skip(f"Agent Memory credentials not configured — skipping integration tests: {e}")
    except Exception as e:
        pytest.fail(f"Failed to create Agent Memory client for integration tests: {e}")


@pytest.fixture(scope="session")
def subscriber_tenant() -> str:
    """Return the subscriber tenant subdomain, or skip if not configured."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    tenant = os.environ.get("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT", "")
    if not tenant:
        pytest.skip(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT not set — "
            "skipping subscriber tenant tests"
        )
    return tenant
