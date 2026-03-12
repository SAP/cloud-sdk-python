"""Pytest configuration and fixtures for Destination integration tests."""

import os
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from sap_cloud_sdk.destination import (
    create_client,
    create_fragment_client,
    create_certificate_client,
)
from sap_cloud_sdk.destination.config import DestinationConfig


@pytest.fixture(scope="session")
def destination_client():
    """Create a Destination client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or APPFND_CFG
        client = create_client()
        return client
    except Exception as e:
        pytest.fail(f"Failed to create Destination client for cloud integration tests: {e}")  # ty: ignore[invalid-argument-type]


@pytest.fixture(scope="session")
def fragment_client():
    """Create a Fragment client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically
        client = create_fragment_client()
        return client
    except Exception as e:
        pytest.fail(f"Failed to create Fragment client for cloud integration tests: {e}")  # ty: ignore[invalid-argument-type]


@pytest.fixture(scope="session")
def certificate_client():
    """Create a Certificate client for cloud testing using secret resolver."""
    _setup_cloud_mode()

    try:
        # Secret resolver handles configuration automatically
        client = create_certificate_client()
        return client
    except Exception as e:
        pytest.fail(f"Failed to create Certificate client for cloud integration tests: {e}")  # ty: ignore[invalid-argument-type]


@pytest.fixture
def sample_pem_certificate() -> str:
    """Generate a sample PEM certificate programmatically for testing.
    
    Returns:
        Base64 encoded PEM certificate content as a string (not double-encoded).
    """
    # Generate a private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create a self-signed certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
        x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("test.example.com"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Serialize certificate to PEM format (this is text, not bytes)
    pem_cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    
    # The API expects the PEM certificate content as base64-encoded string
    # We need to encode the PEM text itself (which is already base64-ish but in PEM format)
    # to a single base64 string for transmission
    return base64.b64encode(pem_cert_bytes).decode('utf-8')


@pytest.fixture
def failure_simulation():
    """Utilities for simulating various failure conditions using explicit configuration."""
    
    class FailureSimulator:
        def create_client_with_network_failure(self):
            """Create a client configured with an unreachable endpoint."""
            cfg = DestinationConfig(
                url="https://unreachable-destination.invalid",
                token_url="https://unreachable-oauth.invalid/oauth/token",
                client_id="test-client-id",
                client_secret="test-client-secret",
                identityzone="test-zone",
            )
            return create_client(config=cfg)

        def create_fragment_client_with_network_failure(self):
            """Create a fragment client configured with an unreachable endpoint."""
            cfg = DestinationConfig(
                url="https://unreachable-destination.invalid",
                token_url="https://unreachable-oauth.invalid/oauth/token",
                client_id="test-client-id",
                client_secret="test-client-secret",
                identityzone="test-zone",
            )
            return create_fragment_client(config=cfg)

        def create_certificate_client_with_network_failure(self):
            """Create a certificate client configured with an unreachable endpoint."""
            cfg = DestinationConfig(
                url="https://unreachable-destination.invalid",
                token_url="https://unreachable-oauth.invalid/oauth/token",
                client_id="test-client-id",
                client_secret="test-client-secret",
                identityzone="test-zone",
            )
            return create_certificate_client(config=cfg)

        def create_client_with_auth_failure(self):
            """Create a client configured with invalid credentials."""
            cfg = DestinationConfig(
                url="https://test-destination.example.com",
                token_url="https://test-oauth.example.com/oauth/token",
                client_id="invalid-client-id",
                client_secret="invalid-client-secret",
                identityzone="test-zone",
            )
            return create_client(config=cfg)

    return FailureSimulator()


def _setup_cloud_mode():
    """Common setup for cloud mode integration tests."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
    

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
