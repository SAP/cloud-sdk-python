"""Client provider and builder."""

import logging

from .client import (
    OutputManagementServiceClient,
    OutputManagementServiceDefaultClient,
)
from .config.destination_credential_config import DestinationCredentialConfig
from .exceptions import ValidationException

logger = logging.getLogger(__name__)


class OutputManagementServiceClientProvider:
    """Provider for Output Management Service client."""

    def __init__(self, client: OutputManagementServiceClient):
        """Initialize provider.

        Args:
            client: Output Management Service client
        """
        self._client = client

    def get_client(self) -> OutputManagementServiceClient:
        """Get the client instance.

        Returns:
            Output Management Service client
        """
        return self._client


class OutputManagementServiceClientProviderBuilder:
    """Builder for Output Management Service client provider."""

    def __init__(self):
        """Initialize builder."""
        self._destination_credential_config: DestinationCredentialConfig = None

    def with_destination_credentials(
        self, config: DestinationCredentialConfig
    ) -> "OutputManagementServiceClientProviderBuilder":
        """Configure with destination credentials.

        Args:
            config: Destination credential configuration

        Returns:
            Builder instance
        """
        self._destination_credential_config = config
        return self

    def build(self) -> OutputManagementServiceClientProvider:
        """Build the client provider.

        Returns:
            Client provider

        Raises:
            ValidationException: If configuration is invalid
        """
        if not self._destination_credential_config:
            raise ValidationException(
                "Destination credentials must be configured",
                error_code="MISSING_CONFIGURATION",
            )

        # For destination credentials, use SAP Cloud SDK
        logger.info("Using destination credential configuration")
        
        # Get the destination object - it handles authentication automatically
        http_destination = self._destination_credential_config.get_destination()
        
        # Get the base URL from destinatiozxn
        base_url = self._destination_credential_config.get_base_url()
        logger.info(f"Retrieved destination base URL: {base_url}")
        
        # Build client with destination object
        # The destination object handles auth automatically
        client = OutputManagementServiceDefaultClient(
            base_url=base_url,
            destination=http_destination,
        )

        logger.info("Built Output Management Service client provider")

        return OutputManagementServiceClientProvider(client)


