"""Shared fixtures for agent_memory unit tests."""

from unittest.mock import patch

import pytest

_NO_CREDENTIALS = "sap_cloud_sdk.agent_memory.config._load_config_from_env"


@pytest.fixture(autouse=True)
def clean_runtime_context():
    """Give every unit test a clean, empty RuntimeContext.

    Unit tests must not depend on ambient process-global context. In a combined
    run (e.g. ``pytest tests/agent_memory/``) the session-scoped integration
    fixture sets an IAS token in the global ContextVar for the whole session,
    which would otherwise leak into unit tests — breaking those that assert the
    IAS guard raises when no token is present. Wrapping each test in an empty
    ``sdk_context`` isolates it from any such leak, from any source.
    """
    from sap_cloud_sdk.core.runtime_context import RuntimeContext
    from sap_cloud_sdk.core.runtime_context._context import sdk_context

    with sdk_context(RuntimeContext({})):
        yield


@pytest.fixture(autouse=True)
def no_credentials(request):
    """Default: simulate no Agent Memory credentials so tests use in-memory path.

    Tests that need the credentials path must opt out via the
    'no_autouse_credentials' marker.
    """
    if request.node.get_closest_marker("no_autouse_credentials"):
        yield
        return
    with patch(_NO_CREDENTIALS, return_value=None):
        yield
