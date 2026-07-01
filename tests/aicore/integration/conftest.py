"""Pytest configuration and fixtures for AI Core filtering integration tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.aicore import disable_filtering, set_aicore_config


_REQUIRED_VARS = [
    "AICORE_CLIENT_ID",
    "AICORE_CLIENT_SECRET",
    "AICORE_AUTH_URL",
    "AICORE_BASE_URL",
    "AICORE_RESOURCE_GROUP",
    "AICORE_FILTER_TEST_MODEL",
]


def _load_env() -> None:
    """Load .env_integration_tests from the repo root if present."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)


@pytest.fixture(scope="session", autouse=True)
def aicore_configured():
    """Load env, configure AI Core, restore unfiltered state on teardown."""
    _load_env()
    missing = [k for k in _REQUIRED_VARS if not os.environ.get(k)]
    if missing:
        pytest.skip(f"Missing env vars for filtering integration tests: {missing}")
    set_aicore_config()
    yield
    disable_filtering()


@pytest.fixture(scope="session")
def test_model() -> str:
    """Model name to use in live completion calls."""
    return os.environ["AICORE_FILTER_TEST_MODEL"]


@pytest.fixture(autouse=True)
def reset_filtering_between_tests():
    """Each scenario opts in/out via its Given step."""
    disable_filtering()
    yield
    disable_filtering()


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
