"""Pytest configuration and fixtures for AuditLog integration tests."""

from pathlib import Path

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.core.auditlog import create_client
from sap_cloud_sdk.core.auditlog import AuditLogConfig

@pytest.fixture(scope="session")
def auditlog_client():
    """Create an AuditLog client for cloud testing using secret resolver."""
    # Load environment from .env_integration_tests (but don't parse - let secret resolver handle it)
    # __file__ is at tests/core/integration/auditlog/conftest.py
    # We need to go up 4 levels to get to project root
    env_file = Path(__file__).parent.parent.parent.parent.parent / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or CLOUD_SDK_CFG
        client = create_client()
        return client
    except Exception as e:
        pytest.fail(f"Failed to create AuditLog client for cloud integration tests: {e}")  # ty: ignore[invalid-argument-type]


@pytest.fixture
def failure_simulation():
    """Utilities for simulating various failure conditions using explicit configuration."""
    
    class FailureSimulator:
        def create_client_with_network_failure(self):
            """Create a client configured with an unreachable endpoint."""
            cfg = AuditLogConfig(
                client_id="test-client-id",
                client_secret="test-client-secret",
                oauth_url="https://unreachable-oauth.invalid/oauth/token",
                service_url="https://unreachable-service.invalid/audit-log/v2",
            )
            return create_client(config=cfg)

        def create_client_with_auth_failure(self):
            """Create a client configured with invalid credentials."""
            cfg = AuditLogConfig(
                client_id="invalid-client-id",
                client_secret="invalid-client-secret",
                oauth_url="https://test-oauth.example.com/oauth/token",
                service_url="https://test-service.example.com/audit-log/v2",
            )
            return create_client(config=cfg)

        def create_client_with_service_unavailable(self):
            """Create a client with valid auth but unavailable service endpoint."""
            cfg = AuditLogConfig(
                client_id="test-client-id",
                client_secret="test-client-secret",
                oauth_url="https://test-oauth.example.com/oauth/token",
                service_url="https://unavailable-service.invalid/audit-log/v2",
            )
            return create_client(config=cfg)

        def setup_intermittent_failure(self):
            """Set up deterministic intermittent failure pattern for testing."""
            # Pattern: [Fail, Fail, Success, Fail, Success] - 3 failures, 2 successes out of 5
            self.intermittent_failure_pattern = [True, True, False, True, False]
            self.intermittent_failure_counter = 0
            
        def get_intermittent_client(self):
            if not hasattr(self, 'intermittent_failure_pattern'):
                self.setup_intermittent_failure()
                
            should_fail = self.intermittent_failure_pattern[
                self.intermittent_failure_counter % len(self.intermittent_failure_pattern)
            ]
            self.intermittent_failure_counter += 1
            
            if should_fail:
                return self.create_client_with_network_failure()
            else:
                return create_client()

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
