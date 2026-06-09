"""Pytest configuration and fixtures for ObjectStore integration tests."""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def integration_env() -> Dict[str, str]:
    """Load and validate integration test environment variables."""

    # Load environment from .env_integration_tests
    env_file = Path(__file__).parent.parent.parent.parent / ".env_integration_tests"

    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded integration environment from {env_file}")
    else:
        logger.warning(f"Integration environment file not found: {env_file}")

    # Required environment variables for cloud-only integration tests
    required_vars = [
        "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST",
        "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID",
        "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY",
        "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET",
    ]

    env_vars = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value:
            env_vars[var] = value
        else:
            missing_vars.append(var)

    if missing_vars:
        pytest.skip(f"Missing required environment variables for cloud integration tests: {missing_vars}")

    # Ensure SSL is enabled for cloud services
    env_vars["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED"] = os.getenv(
        "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED", "true"
    )

    # Validate that we're not using localhost (cloud-only)
    host = env_vars["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST"]
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        pytest.skip("Integration tests are cloud-only. Local endpoints not supported.")

    logger.info(f"Integration environment validated for cloud testing: {host}")
    return env_vars


@pytest.fixture(scope="session")
def objectstore_client(integration_env):
    """Create an ObjectStore client for cloud testing using explicit configuration."""
    try:
        config = ObjectStoreBindingData(
            host=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST"],
            access_key_id=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID"],
            secret_access_key=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY"],
            bucket=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET"],
        )
        disable_ssl = integration_env.get("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED", "true").lower() in ("false", "0")
        client = create_client("default", config=config, disable_ssl=disable_ssl)
        return client
    except Exception as e:
        pytest.fail(f"Failed to create ObjectStore client for cloud integration tests: {e}")


@pytest.fixture
def test_prefix() -> str:
    """Generate a unique test prefix for object names under sdk-python-integration-tests subdirectory."""
    return f"sdk-python-integration-tests/test-{int(time.time() * 1000)}-"


# ===== CLEANUP INFRASTRUCTURE =====

def cleanup_by_prefix(client, prefix: str, timeout: float = 10.0) -> bool:
    """Timeout-controlled cleanup with eventual consistency handling."""
    start_time = time.time()

    try:
        objects = client.list_objects(prefix)
        cleaned_count = 0

        for obj in objects:
            client.delete_object(obj.key)
            cleaned_count += 1

            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Cleanup timeout reached after {timeout}s, cleaned {cleaned_count} objects")
                break

        if cleaned_count > 0:
            # Eventual consistency delay
            time.sleep(0.1)
            logger.debug(f"Cleaned up {cleaned_count} objects with prefix: {prefix}")

        return True
    except Exception as e:
        logger.error(f"Cleanup failed for prefix {prefix}: {e}")
        return False


@pytest.fixture(scope="session", autouse=True)
def integration_test_session_cleanup(objectstore_client):
    """Session-level cleanup of all integration test objects."""

    def cleanup_all_test_objects():
        """Clean up all objects under sdk-python-integration-tests/"""
        try:
            objects = objectstore_client.list_objects("sdk-python-integration-tests/")
            if objects:
                logger.info(f"Found {len(objects)} leftover integration test objects, cleaning up...")
                cleanup_by_prefix(objectstore_client, "sdk-python-integration-tests/", timeout=30.0)
                logger.info("Session cleanup completed")
        except Exception as e:
            logger.warning(f"Session cleanup failed: {e}")

    # Cleanup before tests start
    cleanup_all_test_objects()

    yield

    # Cleanup after all tests complete
    cleanup_all_test_objects()


@pytest.fixture
def cleanup_objects(objectstore_client, test_prefix):
    """Enhanced fixture for automatic cleanup with timeout and eventual consistency."""
    created_objects = []

    def register_object(object_name: str):
        """Register an object for cleanup."""
        created_objects.append(object_name)

    # Provide the register function to tests
    yield register_object

    # Enhanced cleanup after test with timeout
    if created_objects:
        start_time = time.time()
        cleaned_count = 0

        for object_name in created_objects:
            try:
                objectstore_client.delete_object(object_name)
                cleaned_count += 1
                logger.debug(f"Cleaned up object: {object_name}")

                # Respect timeout
                if time.time() - start_time > 10.0:
                    logger.warning(f"Object cleanup timeout reached, cleaned {cleaned_count}/{len(created_objects)} objects")
                    break

            except Exception as e:
                logger.warning(f"Failed to cleanup object {object_name}: {e}")

        if cleaned_count > 0:
            # Eventual consistency delay
            time.sleep(0.1)


@pytest.fixture
def failure_simulation(integration_env):
    """Utilities for simulating various failure conditions using explicit configuration."""
    base_config = ObjectStoreBindingData(
        host=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST"],
        access_key_id=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID"],
        secret_access_key=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY"],
        bucket=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET"],
    )
    disable_ssl = integration_env.get("CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED", "true").lower() in ("false", "0")

    class FailureSimulator:
        def create_client_with_network_failure(self):
            """Create a client configured with an unreachable endpoint."""
            cfg = ObjectStoreBindingData(
                host="unreachable-endpoint.invalid:9000",
                access_key_id=base_config.access_key_id,
                secret_access_key=base_config.secret_access_key,
                bucket=base_config.bucket,
            )
            return create_client("default", config=cfg, disable_ssl=disable_ssl)

        def create_client_with_permission_denied(self):
            """Create a client configured with invalid credentials."""
            cfg = ObjectStoreBindingData(
                host=base_config.host,
                access_key_id="invalid-access-key",
                secret_access_key="invalid-secret-key",
                bucket=base_config.bucket,
            )
            return create_client("default", config=cfg, disable_ssl=disable_ssl)

        def setup_intermittent_failure(self):
            """Placeholder for intermittent failure setup."""
            pass

    return FailureSimulator()


# Configure pytest markers for integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
