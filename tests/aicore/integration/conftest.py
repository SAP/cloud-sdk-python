"""Pytest configuration and fixtures for AI Core integration tests.

Covers both filtering and fallback BDD suites.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.aicore import disable_filtering, set_aicore_config, set_fallbacks


# Filtering integration vars — required for the filtering.feature scenarios.
_FILTERING_VARS = [
    "AICORE_CLIENT_ID",
    "AICORE_CLIENT_SECRET",
    "AICORE_AUTH_URL",
    "AICORE_BASE_URL",
    "AICORE_RESOURCE_GROUP",
    "AICORE_FILTER_TEST_MODEL",
]

# Core credentials shared by both suites.
_CORE_CREDS = _FILTERING_VARS[:-1]

# Fallback integration vars — required only for fallback.feature scenarios.
_FALLBACK_VARS = [
    "AICORE_FALLBACK_TEST_PRIMARY_MODEL",
    "AICORE_FALLBACK_TEST_FALLBACK_MODEL",
]


def _load_env() -> None:
    """Load .env_integration_tests from the repo root if present."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)


@pytest.fixture(scope="session", autouse=True)
def aicore_configured():
    """Load env, configure AI Core, restore unfiltered state on teardown.

    Skips the whole module when AI Core credentials are missing. Fallback-only
    scenarios additionally skip themselves when AICORE_FALLBACK_TEST_* vars
    are missing (see ``fallback_models`` fixture).
    """
    _load_env()
    missing = [k for k in _CORE_CREDS if not os.environ.get(k)]
    if missing:
        pytest.skip(f"Missing core env vars for AI Core integration tests: {missing}")
    set_aicore_config()
    yield
    disable_filtering()
    set_fallbacks(None)


@pytest.fixture(scope="session")
def test_model() -> str:
    """Model name for the filtering integration scenarios."""
    model = os.environ.get("AICORE_FILTER_TEST_MODEL")
    if not model:
        pytest.skip("AICORE_FILTER_TEST_MODEL not set")
    return model


@pytest.fixture(scope="session")
def fallback_models() -> tuple[str, str]:
    """(primary, fallback) model names for the fallback integration scenarios.

    The "primary" should be a model name known to be unsupported in the
    deployed region so that fallback fires; the "fallback" must be supported.
    """
    missing = [k for k in _FALLBACK_VARS if not os.environ.get(k)]
    if missing:
        pytest.skip(f"Missing env vars for fallback integration tests: {missing}")
    return (
        os.environ["AICORE_FALLBACK_TEST_PRIMARY_MODEL"],
        os.environ["AICORE_FALLBACK_TEST_FALLBACK_MODEL"],
    )


@pytest.fixture(autouse=True)
def reset_aicore_state_between_tests():
    """Each scenario opts in/out via its Given step."""
    disable_filtering()
    set_fallbacks(None)
    yield
    disable_filtering()
    set_fallbacks(None)


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
