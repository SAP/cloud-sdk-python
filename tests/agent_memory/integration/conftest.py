"""Integration test fixtures for the Agent Memory service.

Set the following environment variables before running integration tests:

    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_URL          Base URL of the Agent Memory service
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_AUTH_URL     OAuth2 authorization server base URL
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTID     OAuth2 client ID
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTSECRET OAuth2 client secret

Multitenancy:

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT   Subscriber tenant subdomain
        Required for SUBSCRIBER tests. When absent those tests are skipped.
"""

from collections.abc import Generator
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.agent_memory import AccessStrategy, create_client
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError
from sap_cloud_sdk.agent_memory.thread_registry import SAPAgentMemoryThreadRegistry


def _load_env() -> None:
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)


@pytest.fixture(scope="session", autouse=True)
def _ias_context() -> Generator[None, None, None]:
    """Inject IAS_TOKEN into RuntimeContext when running in IAS mode.

    When IAS_TOKEN is set in the environment, all SDK calls made during the
    test session will carry it automatically — no per-test wrapping needed.
    Has no effect in XSUAA mode (IAS_TOKEN absent).

    Uses a yield fixture so the ContextVar is reset on session teardown —
    prevents the IAS token leaking into unit tests when both suites share a
    session (e.g. ``pytest tests/agent_memory/``).
    """
    _load_env()
    ias_token = os.environ.get("IAS_TOKEN")
    if not ias_token:
        yield
        return

    from sap_cloud_sdk.core.runtime_context import IAS_TOKEN, RuntimeContext
    from sap_cloud_sdk.core.runtime_context._context import _context_var

    token = _context_var.set(RuntimeContext({IAS_TOKEN: ias_token}))
    try:
        yield
    finally:
        _context_var.reset(token)


@pytest.fixture(scope="session")
def agent_memory_client() -> AgentMemoryClient:
    """Create a real AgentMemoryClient from environment variables.

    Uses PROVIDER as the default strategy — individual BDD steps override
    this per-call to exercise both PROVIDER and SUBSCRIBER scenarios.
    """
    _load_env()

    try:
        return create_client(access_strategy=AccessStrategy.PROVIDER)
    except AgentMemoryConfigError as e:
        pytest.skip(
            f"Agent Memory credentials not configured — skipping integration tests: {e}"
        )
    except Exception as e:
        pytest.fail(f"Failed to create Agent Memory client for integration tests: {e}")


@pytest.fixture(scope="session")
def subscriber_tenant() -> str:
    """Return the subscriber tenant subdomain, or skip if not configured."""
    _load_env()

    tenant = os.environ.get(
        "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT", ""
    )
    if not tenant:
        pytest.skip(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_SUBSCRIBER_TENANT not set — "
            "skipping subscriber tenant tests"
        )
    return tenant


def _delete_all_memories(client: AgentMemoryClient, agent_id: str) -> None:
    offset = 0
    limit = 50
    while True:
        memories = client.list_memories(agent_id=agent_id, limit=limit, offset=offset)
        for memory in memories:
            client.delete_memory(memory.id)
        if len(memories) < limit:
            break
        offset += limit


@pytest.fixture(scope="session")
def run_agent_id(agent_memory_client: AgentMemoryClient) -> Generator[str, None, None]:
    """Return a unique agent ID for this test run and clean up all its data afterwards."""
    agent_id = f"test-agent-{uuid.uuid4().hex[:8]}"
    yield agent_id
    _delete_all_memories(agent_memory_client, agent_id)


# ── Thread registry fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="session")
def thread_registry() -> SAPAgentMemoryThreadRegistry:
    """Create a real SAPAgentMemoryThreadRegistry from environment variables.

    Skips the test session if credentials are not configured.
    """
    _load_env()

    try:
        from sap_cloud_sdk.agent_memory.config import _load_config_from_env

        config = _load_config_from_env()
        if config is None:
            pytest.skip(
                "Agent Memory credentials not configured — skipping thread registry integration tests"
            )
    except AgentMemoryConfigError as e:
        pytest.skip(
            f"Agent Memory credentials not configured — skipping thread registry integration tests: {e}"
        )

    return SAPAgentMemoryThreadRegistry(config)


@pytest.fixture(scope="session")
def run_thread_agent_id(
    thread_registry: SAPAgentMemoryThreadRegistry,
) -> Generator[str, None, None]:
    """Return a unique agent ID for thread registry tests and clean up all its threads afterwards."""
    agent_id = f"test-agent-{uuid.uuid4().hex[:8]}"
    yield agent_id
    page = thread_registry.list_threads(agent_id=agent_id)
    for entry in page["entries"]:
        try:
            thread_registry.delete_thread(entry["threadId"])
        except Exception:
            pass
