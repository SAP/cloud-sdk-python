"""Unit tests for integration dependencies resolver."""

import json
import os
import pytest
from unittest.mock import patch

from sap_cloud_sdk.agentgateway._dependencies_resolver import (
    EnvironmentDependenciesResolver,
    IntegrationDependenciesResolver,
    _INTEGRATION_DEPENDENCIES_ENV,
)
from sap_cloud_sdk.agentgateway._models import IntegrationDependency
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError


class TestEnvironmentDependenciesResolver:
    """Tests for EnvironmentDependenciesResolver."""

    def test_resolves_valid_dependencies(self):
        """Resolve dependencies from valid JSON in environment variable."""
        deps_json = json.dumps(
            [
                {
                    "ordId": "sap.example:apiResource:demo:v1",
                    "globalTenantId": "123456",
                },
                {
                    "ordId": "sap.flights:mcpServer:v1",
                    "globalTenantId": "789012",
                },
            ]
        )

        with patch.dict(os.environ, {_INTEGRATION_DEPENDENCIES_ENV: deps_json}):
            resolver = EnvironmentDependenciesResolver()
            result = resolver.resolve()

            assert len(result) == 2
            assert result[0].ord_id == "sap.example:apiResource:demo:v1"
            assert result[0].global_tenant_id == "123456"
            assert result[1].ord_id == "sap.flights:mcpServer:v1"
            assert result[1].global_tenant_id == "789012"

    def test_raises_when_env_var_missing(self):
        """Raise error when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_INTEGRATION_DEPENDENCIES_ENV, None)

            resolver = EnvironmentDependenciesResolver()
            with pytest.raises(
                AgentGatewaySDKError, match="Missing required environment variable"
            ):
                resolver.resolve()

    def test_raises_on_invalid_json(self):
        """Raise error when environment variable contains invalid JSON."""
        with patch.dict(
            os.environ, {_INTEGRATION_DEPENDENCIES_ENV: "not valid json"}
        ):
            resolver = EnvironmentDependenciesResolver()
            with pytest.raises(AgentGatewaySDKError, match="Failed to parse.*as JSON"):
                resolver.resolve()

    def test_raises_when_not_array(self):
        """Raise error when JSON is not an array."""
        with patch.dict(
            os.environ, {_INTEGRATION_DEPENDENCIES_ENV: json.dumps({"key": "value"})}
        ):
            resolver = EnvironmentDependenciesResolver()
            with pytest.raises(
                AgentGatewaySDKError, match="must be a JSON array"
            ):
                resolver.resolve()

    def test_raises_on_missing_ord_id(self):
        """Raise error when dependency is missing ordId field."""
        deps_json = json.dumps(
            [
                {
                    "globalTenantId": "123456",
                    # Missing ordId
                },
            ]
        )

        with patch.dict(os.environ, {_INTEGRATION_DEPENDENCIES_ENV: deps_json}):
            resolver = EnvironmentDependenciesResolver()
            with pytest.raises(AgentGatewaySDKError, match="Invalid format"):
                resolver.resolve()

    def test_raises_on_missing_global_tenant_id(self):
        """Raise error when dependency is missing globalTenantId."""
        deps_json = json.dumps(
            [
                {
                    "ordId": "sap.example:apiResource:demo:v1",
                    # Missing globalTenantId
                },
            ]
        )

        with patch.dict(os.environ, {_INTEGRATION_DEPENDENCIES_ENV: deps_json}):
            resolver = EnvironmentDependenciesResolver()
            with pytest.raises(AgentGatewaySDKError, match="Invalid format"):
                resolver.resolve()

    def test_handles_empty_array(self):
        """Handle empty array of dependencies."""
        with patch.dict(os.environ, {_INTEGRATION_DEPENDENCIES_ENV: "[]"}):
            resolver = EnvironmentDependenciesResolver()
            result = resolver.resolve()

            assert result == []


class TestIntegrationDependenciesResolverInterface:
    """Tests for IntegrationDependenciesResolver abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Cannot instantiate abstract base class directly."""
        with pytest.raises(TypeError):
            IntegrationDependenciesResolver()

    def test_custom_resolver_implementation(self):
        """Can create custom resolver implementation."""

        class CustomResolver(IntegrationDependenciesResolver):
            def resolve(self) -> list[IntegrationDependency]:
                return [
                    IntegrationDependency(
                        ord_id="custom.ord:id:v1",
                        global_tenant_id="999",
                    )
                ]

        resolver = CustomResolver()
        result = resolver.resolve()

        assert len(result) == 1
        assert result[0].ord_id == "custom.ord:id:v1"
        assert result[0].global_tenant_id == "999"
