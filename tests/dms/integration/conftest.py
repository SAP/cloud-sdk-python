from sap_cloud_sdk.dms import create_client
from tests.destination.integration.conftest import _setup_cloud_mode
import pytest
from pathlib import Path
from dotenv import load_dotenv



@pytest.fixture(scope="session")
def dms_client():
    """Create a DMS client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or CLOUD_SDK_CFG
        client = create_client()
        return client
    except Exception as e:
        pytest.fail(f"Failed to create DMS client for cloud integration tests: {e}")  # ty: ignore[invalid-argument-type]



def _setup_cloud_mode():
    """Common setup for cloud mode integration tests."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
    