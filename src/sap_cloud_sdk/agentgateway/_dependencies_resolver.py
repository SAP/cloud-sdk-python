"""Integration dependencies resolution for Agent Gateway.

Provides an abstraction for loading integration dependencies from different sources
(environment variables, files, remote services, etc.).
"""

import json
import logging
import os
from abc import ABC, abstractmethod

from sap_cloud_sdk.agentgateway._models import IntegrationDependency
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError

logger = logging.getLogger(__name__)

# Environment variable for integration dependencies
_INTEGRATION_DEPENDENCIES_ENV = "INTEGRATION_DEPENDENCIES"


class IntegrationDependenciesResolver(ABC):
    """Abstract interface for resolving integration dependencies.

    Integration dependencies define the MCP servers that an agent should
    connect to. This abstraction allows different sources for this configuration.
    """

    @abstractmethod
    def resolve(self) -> list[IntegrationDependency]:
        """Resolve integration dependencies from configured source.

        Returns:
            List of IntegrationDependency objects with ord_id and global_tenant_id.

        Raises:
            AgentGatewaySDKError: If resolution fails or configuration is invalid.
        """
        pass


class EnvironmentDependenciesResolver(IntegrationDependenciesResolver):
    """Resolves integration dependencies from INTEGRATION_DEPENDENCIES environment variable.

    Expected format is a JSON array:
    [
        {
            "ordId": "sap.example:apiResource:demo:v1",
            "globalTenantId": "123456"
        }
    ]
    """

    def resolve(self) -> list[IntegrationDependency]:
        """Load integration dependencies from INTEGRATION_DEPENDENCIES env var.

        Returns:
            List of IntegrationDependency objects.

        Raises:
            AgentGatewaySDKError: If environment variable is missing or invalid.
        """
        raw_value = os.environ.get(_INTEGRATION_DEPENDENCIES_ENV)

        if not raw_value:
            raise AgentGatewaySDKError(
                f"Missing required environment variable: {_INTEGRATION_DEPENDENCIES_ENV}. "
                'Expected format: [{"ordId": "...", "globalTenantId": "..."}]'
            )

        try:
            data = json.loads(raw_value)
        except json.JSONDecodeError as e:
            raise AgentGatewaySDKError(
                f"Failed to parse {_INTEGRATION_DEPENDENCIES_ENV} as JSON: {e}"
            ) from e

        if not isinstance(data, list):
            raise AgentGatewaySDKError(
                f"{_INTEGRATION_DEPENDENCIES_ENV} must be a JSON array, got: {type(data).__name__}"
            )

        try:
            dependencies = [
                IntegrationDependency(
                    ord_id=dep["ordId"],
                    global_tenant_id=dep["globalTenantId"],
                )
                for dep in data
            ]
            logger.debug(
                "Loaded %d integration dependencies from environment",
                len(dependencies),
            )
            return dependencies
        except (KeyError, TypeError) as e:
            raise AgentGatewaySDKError(
                f"Invalid format in {_INTEGRATION_DEPENDENCIES_ENV}: {e}. "
                'Expected format: [{"ordId": "...", "globalTenantId": "..."}]'
            ) from e
