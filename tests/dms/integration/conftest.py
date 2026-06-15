from sap_cloud_sdk.dms import create_client
from sap_cloud_sdk.dms.model import InternalRepoRequest
import pytest
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_SDK_TEST_REPO_PREFIX = "sdk-integration-test-"


@pytest.fixture(scope="session")
def dms_client():
    """Create a DMS client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or CLOUD_SDK_CFG
        client = create_client(instance="default")
        return client
    except Exception as e:
        pytest.skip(f"DMS integration tests require credentials: {e}")


@pytest.fixture(scope="session", autouse=True)
def _setup_test_repositories(dms_client):
    """Create test repositories for integration tests and clean up after.

    Always onboards a standard and a version-enabled repository for the test
    session, then deletes them on teardown.
    """
    created_repos = []

    logger.info("Onboarding test repositories")
    repo = dms_client.onboard_repository(
        InternalRepoRequest(
            displayName=f"{_SDK_TEST_REPO_PREFIX}standard",
            description="Auto-created by SDK integration tests",
        )
    )
    created_repos.append(repo.id)

    repo = dms_client.onboard_repository(
        InternalRepoRequest(
            displayName=f"{_SDK_TEST_REPO_PREFIX}versioned",
            description="Auto-created by SDK integration tests (versioning)",
            isVersionEnabled=True,
        )
    )
    created_repos.append(repo.id)

    yield

    # Cleanup: delete repositories we created
    for repo_id in created_repos:
        try:
            dms_client.delete_repository(repo_id)
            logger.info("Cleaned up test repository %s", repo_id)
        except Exception as e:
            logger.warning("Failed to clean up test repository %s: %s", repo_id, e)


def _setup_cloud_mode():
    """Common setup for cloud mode integration tests."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
