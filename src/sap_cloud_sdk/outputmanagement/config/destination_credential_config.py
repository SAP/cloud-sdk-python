"""Destination credential configuration for Output Management Service."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import logging
logger = logging.getLogger(__name__)
class DestinationCredentialConfig(BaseModel):
    """Configuration for accessing Output Management Service via SAP BTP Destination.
    This class provides a simple configuration wrapper for destination-based access.
    Uses relative imports since this module is part of sap_cloud_sdk.
    Attributes:
        destination_name: Name of the destination in SAP BTP Destination Service
        access_strategy: Optional access strategy - "PROVIDER_ONLY" or "SUBSCRIBER_ONLY"
    Example:
        ```python
        from sap_cloud_sdk.outputmanagement import OutputManagementServiceClientProvider
        from sap_cloud_sdk.outputmanagement.config import DestinationCredentialConfig
        # Create config
        config = DestinationCredentialConfig(
            destination_name="OUTPUT_MANAGEMENT_DEST",
            access_strategy="PROVIDER_ONLY"
        )
        # Create client using destination
        client = OutputManagementServiceClientProvider.create_from_destination(config)
        ```
    """
    destination_name: str = Field(
        ..., 
        description="Name of the destination in SAP BTP Destination Service"
    )
    access_strategy: Optional[str] = Field(
        default=None,
        description="Access strategy: 'PROVIDER_ONLY' or 'SUBSCRIBER_ONLY' (optional)"
    )
    instance: Optional[str] = Field(
        default=None,
        description="Destination service instance name (defaults to 'default' if not provided)"
    )
    @field_validator("destination_name")
    @classmethod
    def validate_destination_name(cls, v: str) -> str:
        """Validate destination name is not empty."""
        if not v or not v.strip():
            raise ValueError("Destination name cannot be empty")
        return v.strip()
    @field_validator("access_strategy")
    @classmethod
    def validate_access_strategy(cls, v: Optional[str]) -> Optional[str]:
        """Validate access strategy if provided."""
        if v is not None:
            v = v.strip().upper()
            if v not in ["PROVIDER_ONLY", "SUBSCRIBER_ONLY"]:
                raise ValueError(
                    f"Invalid access_strategy: {v}. "
                    "Must be 'PROVIDER_ONLY' or 'SUBSCRIBER_ONLY'"
                )
        return v
    class Config:
        """Pydantic configuration."""
        frozen = True
        str_strip_whitespace = True
    def get_destination(self):
        """Retrieve the destination from SAP BTP Destination Service.
        Uses relative import to access sap_cloud_sdk.destination module.
        Returns:
            Destination object with URL, authentication, and properties
        Raises:
            ValueError: If destination is not found
            Exception: If destination retrieval fails
        """
        from ...destination import create_client, AccessStrategy
        
        # Resolve instance name: use provided value or default to "default"
        inst = self.instance or "default"
        logger.info(f"Retrieving destination '{self.destination_name}' from instance '{inst}'")
        
        try:
            client = create_client(instance=inst)
        except Exception as e:
            logger.error(f"Failed to create destination client for instance '{inst}': {e}")
            raise ValueError(
                f"Failed to create destination client for instance '{inst}'. "
                f"Ensure the Destination Service is properly bound and configured."
            ) from e
        if self.access_strategy:
            if self.access_strategy == "PROVIDER_ONLY":
                strategy = AccessStrategy.PROVIDER_ONLY
            else:
                strategy = AccessStrategy.SUBSCRIBER_ONLY
            destination = client.get_subaccount_destination(
                name=self.destination_name,
                access_strategy=strategy
            )
            if destination is None:
                raise ValueError(
                    f"Destination '{self.destination_name}' not found "
                    f"with access strategy '{self.access_strategy}'"
                )
            logger.info(f"Retrieved destination with {self.access_strategy} strategy")
        else:
            destination = client.get_instance_destination(name=self.destination_name)
            if destination is None:
                destination = client.get_subaccount_destination(name=self.destination_name)
            if destination is None:
                raise ValueError(f"Destination '{self.destination_name}' not found")
            logger.info(f"Retrieved destination '{self.destination_name}'")
        return destination
    def get_base_url(self) -> str:
        """Get the base URL from the destination."""
        destination = self.get_destination()
        if hasattr(destination, 'url'):
            url = destination.url
        elif hasattr(destination, 'get_url'):
            url = destination.get_url()
        elif hasattr(destination, 'get_uri'):
            url = destination.get_uri()
        else:
            raise ValueError(f"Cannot extract URL from destination '{self.destination_name}'")
        if not url:
            raise ValueError(f"Destination '{self.destination_name}' does not have a URL")
        return url.rstrip('/')
