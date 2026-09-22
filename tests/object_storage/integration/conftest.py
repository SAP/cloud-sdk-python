"""Fixtures for the multi-provider object storage integration tests.

One ``pytest`` run exercises every scenario against each provider whose
credentials are present in ``.env_integration_tests``; providers without
credentials are skipped per scenario. The failure-simulation fixtures need no
live credentials, so the failure scenarios run for every provider (GCS uses a
throwaway in-process RSA key so its client constructs offline).
"""

import base64
import json
import logging
import os
import uuid
from pathlib import Path

import pytest
import urllib3
from azure.storage.blob import ContainerClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
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
    key = os.getenv(f"{prefix}BASE64_PRIVATE_KEY_DATA")
    project = os.getenv(f"{prefix}PROJECT_ID")
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


def build_live_client(provider: str):
    """Return a live client for ``provider``, or skip if it has no credentials."""
    config = _CONFIG_LOADERS[provider]()
    if config is None:
        pytest.skip(f"no credentials configured for provider '{provider}'")
    return create_client(config=config)


def _dummy_gcs_key() -> str:
    """Base64-encode a service-account JSON with a throwaway RSA private key.

    Lets ``GcsClient`` construct fully offline so GCS can join the network-failure
    matrix without real credentials.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    account = {
        "type": "service_account",
        "project_id": "dummy-project",
        "private_key_id": "dummy",
        "private_key": pem,
        "client_email": "dummy@dummy-project.iam.gserviceaccount.com",
        "client_id": "0",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return base64.b64encode(json.dumps(account).encode()).decode()


def build_unreachable_client(provider: str):
    """Return a client pointed at a dead endpoint, tuned to fail fast.

    The provider SDKs default to multi-second retry budgets, which would make
    these failure scenarios take minutes. The clients expose no retry knobs, so
    the test tunes each transport to zero retries and a short timeout after
    construction. GCS needs no tuning — it fails offline while refreshing the
    throwaway credential.
    """
    if provider == "s3":
        client = create_client(
            config=S3Config(
                access_key_id="ak",
                secret_access_key="sk",
                bucket="bucket",
                host=_DEAD_ENDPOINT,
                disable_ssl=True,
            )
        )
        client._minio_client._http = urllib3.PoolManager(  # ty: ignore[unresolved-attribute]
            retries=False, timeout=urllib3.Timeout(connect=1.0, read=1.0)
        )
        return client
    if provider == "azure":
        client = create_client(
            config=AzureConfig(
                container_name="c",
                container_uri=f"http://{_DEAD_ENDPOINT}/c",
                sas_token="sv=token",
            )
        )
        client._container = ContainerClient.from_container_url(  # ty: ignore[unresolved-attribute]
            f"http://{_DEAD_ENDPOINT}/c",
            credential="sv=token",
            retry_total=0,
            connection_timeout=1,
            read_timeout=1,
        )
        return client
    return create_client(
        config=GcsConfig(
            base64_encoded_private_key_data=_dummy_gcs_key(),
            project_id="dummy-project",
            bucket="nonexistent-bucket",
        )
    )


@pytest.fixture
def object_prefix() -> str:
    return f"sdk-python-integration-tests/{uuid.uuid4()}/"
