"""Pytest configuration and fixtures for ObjectStore integration tests."""

import base64
import json
import os
import time
import logging
from pathlib import Path
from typing import Dict

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore.config import AzureConfig, GcsConfig, S3Config


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", params=("s3", "azure", "gcs"))
def integration_env(request) -> Dict[str, str]:
    """Load and validate integration test environment variables."""

    # Load environment from .env_integration_tests
    env_file = Path(__file__).parent.parent.parent.parent / ".env_integration_tests"

    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded integration environment from {env_file}")
    else:
        logger.warning(f"Integration environment file not found: {env_file}")

    provider = request.param
    required_vars = {
        "s3": [
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST",
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID",
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY",
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET",
        ],
        "azure": [
            "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_CONTAINER_NAME",
            "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_CONTAINER_URI",
            "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_SAS_TOKEN",
        ],
        "gcs": [
            "CLOUD_SDK_CFG_OBJECTSTORE_GCS_BASE64ENCODEDPRIVATEKEYDATA",
            "CLOUD_SDK_CFG_OBJECTSTORE_GCS_PROJECTID",
            "CLOUD_SDK_CFG_OBJECTSTORE_GCS_BUCKET",
        ],
    }[provider]

    env_vars = {"provider": provider}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value:
            env_vars[var] = value
        else:
            missing_vars.append(var)

    if missing_vars:
        pytest.skip(
            f"Missing required {provider.upper()} ObjectStore environment variables: {missing_vars}"
        )

    if provider == "s3":
        # Ensure SSL is enabled for cloud services
        env_vars["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED"] = os.getenv(
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED", "true"
        )

        # Validate that we're not using localhost (cloud-only)
        host = env_vars["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST"]
        if host.startswith("localhost") or host.startswith("127.0.0.1"):
            pytest.skip("Integration tests are cloud-only. Local endpoints not supported.")

    logger.info(f"Integration environment validated for {provider} cloud testing")
    return env_vars


def _config_from_env(integration_env):
    provider = integration_env["provider"]
    if provider == "s3":
        disable_ssl = integration_env.get(
            "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SSL_ENABLED", "true"
        ).lower() in ("false", "0")
        return S3Config(
            host=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_HOST"],
            access_key_id=integration_env[
                "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_ACCESS_KEY_ID"
            ],
            secret_access_key=integration_env[
                "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_SECRET_ACCESS_KEY"
            ],
            bucket=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_BUCKET"],
            disable_ssl=disable_ssl,
        )
    if provider == "azure":
        return AzureConfig(
            container_name=integration_env[
                "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_CONTAINER_NAME"
            ],
            container_uri=integration_env[
                "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_CONTAINER_URI"
            ],
            sas_token=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_AZURE_SAS_TOKEN"],
        )
    return GcsConfig(
        base64_encoded_private_key_data=integration_env[
            "CLOUD_SDK_CFG_OBJECTSTORE_GCS_BASE64ENCODEDPRIVATEKEYDATA"
        ],
        project_id=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_GCS_PROJECTID"],
        bucket=integration_env["CLOUD_SDK_CFG_OBJECTSTORE_GCS_BUCKET"],
    )


@pytest.fixture(scope="session")
def objectstore_client(integration_env):
    """Create an ObjectStore client for cloud testing using explicit configuration."""
    try:
        return create_client(
            integration_env["provider"], config=_config_from_env(integration_env)
        )
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
    provider = integration_env["provider"]
    base_config = _config_from_env(integration_env)

    class FailureSimulator:
        def create_client_with_network_failure(self):
            """Create a client configured with an unreachable endpoint."""
            if provider == "gcs":
                pytest.skip(
                    "GCS does not support overriding the API endpoint through GcsConfig"
                )
            if isinstance(base_config, S3Config):
                cfg = S3Config(
                    host="unreachable-endpoint.invalid:9000",
                    access_key_id=base_config.access_key_id,
                    secret_access_key=base_config.secret_access_key,
                    bucket=base_config.bucket,
                    disable_ssl=base_config.disable_ssl,
                )
            else:
                cfg = AzureConfig(
                    container_name=base_config.container_name,
                    container_uri=f"https://unreachable-endpoint.invalid/{base_config.container_name}",
                    sas_token=base_config.sas_token,
                )
            return create_client(provider, config=cfg)

        def create_client_with_permission_denied(self):
            """Create a client configured with invalid credentials."""
            if isinstance(base_config, S3Config):
                cfg: S3Config | AzureConfig | GcsConfig = S3Config(
                    host=base_config.host,
                    access_key_id="invalid-access-key",
                    secret_access_key="invalid-secret-key",
                    bucket=base_config.bucket,
                    disable_ssl=base_config.disable_ssl,
                )
            elif isinstance(base_config, AzureConfig):
                cfg = AzureConfig(
                    container_name=base_config.container_name,
                    container_uri=base_config.container_uri,
                    sas_token="sv=2023-11-03&sr=c&sig=invalid",
                )
            else:
                service_account = json.loads(
                    base64.b64decode(base_config.base64_encoded_private_key_data)
                )
                service_account["client_email"] = (
                    f"invalid-objectstore-integration@{base_config.project_id}.iam.gserviceaccount.com"
                )
                cfg = GcsConfig(
                    base64_encoded_private_key_data=base64.b64encode(
                        json.dumps(service_account).encode()
                    ).decode(),
                    project_id=base_config.project_id,
                    bucket=base_config.bucket,
                )
            return create_client(provider, config=cfg)

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
