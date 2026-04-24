"""Integration tests for the Temporal module.

Requires a running Temporal server and environment variables:
    TEMPORAL_CALL_URL or APPFND_LOCALDEV_TEMPORAL=true
    TEMPORAL_NAMESPACE
"""

import pytest
from temporalio import workflow, activity
from datetime import timedelta

from sap_cloud_sdk.temporal import create_client, create_worker


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "temporal/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def temporal_client_fixture(request):
    import asyncio
    import os

    if not os.getenv("APPFND_LOCALDEV_TEMPORAL") and not os.getenv("TEMPORAL_CALL_URL"):
        pytest.skip("No Temporal server configured. Set APPFND_LOCALDEV_TEMPORAL=true or TEMPORAL_CALL_URL.")

    loop = asyncio.new_event_loop()
    client = loop.run_until_complete(create_client())
    yield client
    loop.close()
