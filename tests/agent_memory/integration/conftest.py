"""Integration test fixtures for the Agent Memory service.

Set the following environment variables before running integration tests:

    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_URL          Base URL of the Agent Memory service
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_AUTH_URL     OAuth2 authorization server base URL
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTID     OAuth2 client ID
    CLOUD_SDK_CFG_AGENT_MEMORY_DEFAULT_CLIENTSECRET OAuth2 client secret
"""

from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.agent_memory import create_client
from sap_cloud_sdk.agent_memory.client import AgentMemoryClient


@pytest.fixture(scope="session")
def agent_memory_client() -> AgentMemoryClient:
    """Create a real AgentMemoryClient from environment variables."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    try:
        return create_client()
    except Exception as e:
        pytest.fail(f"Failed to create Agent Memory client for integration tests: {e}")
