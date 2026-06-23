"""SAP Ariba Output Management Service SDK for Python."""

import logging
import os
from typing import Optional

from .client import OutputManagementClient
from ._service_client import OutputManagementServiceClient
from ._models import (
    OutputRequest,
    OutputRequestBuilder,
    OutputResponse,
    EmailConfiguration,
    AttachmentConfig,
    OutputManagementInfo,
    OutputRequestData,
    DirectShareConfiguration,
    FormConfiguration,
    PreGeneratedAttachment,
)
from .config import DestinationCredentialConfig
from .constants import FileFormat, Channel
from .exceptions import (
    OutputManagementException,
    AuthenticationException,
    ValidationException,
    NetworkException,
    DestinationNotFoundException,
    DestinationAccessException,
)

logger = logging.getLogger(__name__)


def create_client(
    destination_name: Optional[str] = None,
    access_strategy: Optional[str] = None,
    instance: Optional[str] = None,
) -> OutputManagementClient:
    """
    Create an Output Management client with configuration from environment or parameters.

    This is the recommended factory function for creating clients. It follows the SDK's
    standard pattern of reading configuration from environment variables with optional overrides.

    Environment Variables:
        - CLOUD_SDK_OMS_DESTINATION_NAME: Default destination name
        - CLOUD_SDK_OMS_ACCESS_STRATEGY: Default access strategy (PROVIDER_ONLY or SUBSCRIBER_ONLY)
        - CLOUD_SDK_OMS_INSTANCE: Default destination service instance name

    Args:
        destination_name: Name of the destination. If not provided, reads from
            CLOUD_SDK_OMS_DESTINATION_NAME environment variable.
        access_strategy: Destination access strategy. If not provided, reads from
            CLOUD_SDK_OMS_ACCESS_STRATEGY environment variable or defaults to "PROVIDER_ONLY".
        instance: Destination service instance name. If not provided, reads from
            CLOUD_SDK_OMS_INSTANCE environment variable or defaults to "default".

    Returns:
        Configured OutputManagementClient instance

    Raises:
        ValidationException: If destination_name is not provided and not found in environment

    Example:
        ```python
        from sap_cloud_sdk.outputmanagement import create_client

        # Using environment variables
        client = create_client()

        # With explicit parameters
        client = create_client(
            destination_name="MY_OMS_DESTINATION",
            access_strategy="PROVIDER_ONLY",
            instance="default"
        )

        # Use the client's 4 methods
        response = client.send_email(
            notification_template_key="PO_NOTIFICATION",
            to=["user@example.com"],
            business_document={"PurchaseOrder": {"id": "PO-123"}}
        )
        ```
    """
    # Read from environment variables with parameter overrides
    dest_name = destination_name or os.getenv("CLOUD_SDK_OMS_DESTINATION_NAME")
    access_strat = access_strategy or os.getenv(
        "CLOUD_SDK_OMS_ACCESS_STRATEGY", "PROVIDER_ONLY"
    )
    inst = instance or os.getenv("CLOUD_SDK_OMS_INSTANCE", "default")

    if not dest_name:
        raise ValidationException(
            "Destination name must be provided either as parameter or via "
            "CLOUD_SDK_OMS_DESTINATION_NAME environment variable",
            error_code="MISSING_DESTINATION_NAME",
        )

    logger.info(
        f"Creating Output Management client with destination '{dest_name}', "
        f"access_strategy '{access_strat}', instance '{inst}'"
    )

    # Create destination config
    destination_config = DestinationCredentialConfig(
        destination_name=dest_name,
        access_strategy=access_strat,
        instance=inst,
    )

    # Get the destination object
    http_destination = destination_config.get_destination()

    # Get the base URL from destination
    base_url = destination_config.get_base_url()
    logger.info(f"Retrieved destination base URL: {base_url}")

    # Create service client directly
    service_client = OutputManagementServiceClient(
        base_url=base_url,
        destination=http_destination,
        destination_instance=inst,
    )

    # Wrap it in the unified OutputManagementClient
    return OutputManagementClient(service_client)


__all__ = [
    # Main client and factory function
    "OutputManagementClient",
    "create_client",
    # Models
    "OutputRequest",
    "OutputRequestBuilder",
    "OutputResponse",
    "EmailConfiguration",
    "AttachmentConfig",
    "OutputManagementInfo",
    "OutputRequestData",
    "DirectShareConfiguration",
    "FormConfiguration",
    "PreGeneratedAttachment",
    # Configuration
    "DestinationCredentialConfig",
    # Constants/Enums
    "FileFormat",
    "Channel",
    # Exceptions
    "OutputManagementException",
    "AuthenticationException",
    "ValidationException",
    "NetworkException",
    "DestinationNotFoundException",
    "DestinationAccessException",
]
