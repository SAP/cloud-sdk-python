"""Fixtures for the multi-provider object storage integration tests.

One ``pytest`` run exercises every live scenario against each provider whose
credentials are present in ``.env_integration_tests``; providers without
credentials are skipped per scenario. The S3 and Azure network-failure
scenarios use dummy credentials and a dead local endpoint, so they always run.
"""

import logging
import os
import uuid
from pathlib import Path

import pytest
import urllib3
from azure.storage.blob import ContainerClient
from dotenv import load_dotenv

from sap_cloud_sdk.object_storage import create_client
from sap_cloud_sdk.object_storage.config import AzureConfig, GcsConfig, S3Config

logger = logging.getLogger(__name__)

PROVIDERS = ("s3", "azure", "gcs")
# A closed local port: connection is refused immediately (no DNS, no long wait).
_DEAD_ENDPOINT = "127.0.0.1:1"


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session", autouse=True)
def _load_integration_env():
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info("Loaded integration environment from %s", env_file)


def _s3_config_from_env() -> S3Config | None:
    prefix = "CLOUD_SDK_CFG_OBJECTSTORE_DEFAULT_"
    host = os.getenv(f"{prefix}HOST")
    access = os.getenv(f"{prefix}ACCESS_KEY_ID")
    secret = os.getenv(f"{prefix}SECRET_ACCESS_KEY")
    bucket = os.getenv(f"{prefix}BUCKET")
    if not all([host, access, secret, bucket]):
        return None
    disable_ssl = os.getenv(f"{prefix}SSL_ENABLED", "true").lower() in ("false", "0")
    return S3Config(
        access_key_id=access,  # ty: ignore[invalid-argument-type]
        secret_access_key=secret,  # ty: ignore[invalid-argument-type]
        bucket=bucket,  # ty: ignore[invalid-argument-type]
        host=host,  # ty: ignore[invalid-argument-type]
        disable_ssl=disable_ssl,
    )


def _azure_config_from_env() -> AzureConfig | None:
    prefix = "CLOUD_SDK_CFG_OBJECTSTORE_AZURE_"
    name = os.getenv(f"{prefix}CONTAINER_NAME")
    uri = os.getenv(f"{prefix}CONTAINER_URI")
    token = os.getenv(f"{prefix}SAS_TOKEN")
    if not all([name, uri, token]):
        return None
    return AzureConfig(
        container_name=name,  # ty: ignore[invalid-argument-type]
        container_uri=uri,  # ty: ignore[invalid-argument-type]
        sas_token=token,  # ty: ignore[invalid-argument-type]
    )


def _gcs_config_from_env() -> GcsConfig | None:
    prefix = "CLOUD_SDK_CFG_OBJECTSTORE_GCS_"
    key = os.getenv(f"{prefix}BASE64ENCODEDPRIVATEKEYDATA")
    project = os.getenv(f"{prefix}PROJECTID")
    bucket = os.getenv(f"{prefix}BUCKET")
    if not all([key, project, bucket]):
        return None
    return GcsConfig(
        base64_encoded_private_key_data=key,  # ty: ignore[invalid-argument-type]
        project_id=project,  # ty: ignore[invalid-argument-type]
        bucket=bucket,  # ty: ignore[invalid-argument-type]
    )


_CONFIG_LOADERS = {
    "s3": _s3_config_from_env,
    "azure": _azure_config_from_env,
    "gcs": _gcs_config_from_env,
}


def _require(provider: str):
    """Load a provider's live config, skipping the scenario if it is absent."""
    config = _CONFIG_LOADERS[provider]()
    if config is None:
        pytest.skip(f"no credentials configured for provider '{provider}'")
    return config


def build_live_client(provider: str):
    """Return a live client for ``provider``, or skip if it has no credentials."""
    return create_client(config=_require(provider))


def build_unreachable_client(provider: str):
    """Return a credential-free client aimed at a dead local endpoint."""
    if provider == "s3":
        client = create_client(
            config=S3Config(
                access_key_id="dummy-access-key",
                secret_access_key="dummy-secret-key",
                bucket="dummy-bucket",
                host=_DEAD_ENDPOINT,
                disable_ssl=True,
            )
        )
        client._minio_client._http = urllib3.PoolManager(  # ty: ignore[unresolved-attribute]
            retries=False, timeout=urllib3.Timeout(connect=1.0, read=1.0)
        )
        return client
    if provider == "azure":
        dead_uri = f"http://{_DEAD_ENDPOINT}/dummy-container"
        client = create_client(
            config=AzureConfig(
                container_name="dummy-container",
                container_uri=dead_uri,
                sas_token="sv=dummy-token",
            )
        )
        client._container = ContainerClient.from_container_url(  # ty: ignore[unresolved-attribute]
            dead_uri,
            credential="sv=dummy-token",
            retry_total=0,
            connection_timeout=1,
            read_timeout=1,
        )
        return client
    raise ValueError(f"unsupported network-failure provider: {provider}")


@pytest.fixture
def object_prefix() -> str:
    return f"sdk-python-integration-tests/{uuid.uuid4()}/"
