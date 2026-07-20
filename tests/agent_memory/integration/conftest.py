"""Integration test fixtures for the Agent Memory service.

Set the following environment variables before running integration tests:

Provider (default) binding:

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA

Subscriber binding (one set per tenant, keyed by subdomain in upper-snake-case):

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_UAA

    e.g. for tenant "acme-corp":
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_UAA

Subscriber tenant name:

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT   Subscriber tenant subdomain
        Required for SUBSCRIBER tests. When absent those tests are skipped.
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

    Uses PROVIDER as the default strategy — individual BDD steps override
    this per-call to exercise both PROVIDER and SUBSCRIBER scenarios.
    """
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    try:
        return create_client(access_strategy=AccessStrategy.PROVIDER)
    except AgentMemoryConfigError as e:
        pytest.skip(f"Agent Memory credentials not configured — skipping integration tests: {e}")
    except Exception as e:
        pytest.fail(f"Failed to create Agent Memory client for integration tests: {e}")


@pytest.fixture(scope="session")
def subscriber_tenant() -> str:
    """Return the subscriber tenant subdomain, or skip if not configured.

    On this branch, a separate binding must exist for the tenant subdomain:
        /etc/secrets/appfnd/hana-agent-memory/<tenant>/
    or environment variables:
        CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_APPLICATION_URL
        CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_UAA
    """
    from sap_cloud_sdk.agent_memory.config import _load_config_for_instance

    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    tenant = os.environ.get("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT", "")
    if not tenant:
        pytest.skip(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT not set — "
            "skipping subscriber tenant tests"
        )

    try:
        _load_config_for_instance(tenant)
    except AgentMemoryConfigError:
        pytest.skip(
            f"Subscriber binding for tenant '{tenant}' not configured — "
            f"skipping subscriber tenant tests"
        )

    return tenant
