"""Main client classes."""

import logging
import requests
from abc import ABC, abstractmethod
from typing import Optional

from sap_cloud_sdk.destination import Destination
from .clients.output_requests_client import OutputRequestsClient
from .clients.output_requests_client_impl import OutputRequestsClientImpl

logger = logging.getLogger(__name__)


class OutputManagementServiceClient(ABC):
    """Abstract base class for Output Management Service client."""

    @abstractmethod
    def get_output_requests_client(self) -> OutputRequestsClient:
        """Get output requests client.

        Returns:
            Output requests client
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the client and release resources."""
        pass


class OutputManagementServiceDefaultClient(OutputManagementServiceClient):
    """Default implementation of Output Management Service client."""

    def __init__(
        self,
        base_url: str,
        destination: Optional[Destination] = None,
        destination_instance: Optional[str] = None,
    ):
        """Initialize client.

        Args:
            base_url: Base URL of the service
            destination: Optional Cloud SDK destination object for making requests
            destination_instance: Optional Destination Service instance name
        """
        self._base_url = base_url.rstrip("/")
        self._destination = destination
        self._destination_instance = destination_instance

        # Create a simple requests session
        self._session = requests.Session()

        # Initialize output requests client
        self._output_requests_client = OutputRequestsClientImpl(
            self._session,
            self._base_url,
            self._destination,
            self._destination_instance,
        )

        logger.info(f"Initialized Output Management Service client for {base_url}")

    def get_output_requests_client(self) -> OutputRequestsClient:
        """Get output requests client."""
        return self._output_requests_client

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        logger.info("Output Management Service client closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
