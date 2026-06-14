"""SAP Ariba Output Management Service SDK for Python."""

from .client import (
    OutputManagementServiceClient,
    OutputManagementServiceDefaultClient,
)
from .client_provider import (
    OutputManagementServiceClientProvider,
    OutputManagementServiceClientProviderBuilder,
)
from .models.output_request import OutputRequest, OutputRequestBuilder
from .models.output_response import (
    OutputResponse,
)
from .models.email_configuration import EmailConfiguration
from .models.attachment_config import AttachmentConfig
from .models.output_management_info import OutputManagementInfo
from .models.output_request_data import OutputRequestData
from .models.direct_share_configuration import DirectShareConfiguration
from .models.form_configuration import FormConfiguration
from .clients.email_client import EmailClient
from .config.destination_credential_config import DestinationCredentialConfig
from .constants import FileFormat, Channel, Status
from .exceptions import (
    OutputManagementException,
    AuthenticationException,
    ValidationException,
    NetworkException,
    DestinationNotFoundException,
    DestinationAccessException,
)

__version__ = "1.0.0"

__all__ = [
    # Client classes
    "OutputManagementServiceClient",
    "OutputManagementServiceDefaultClient",
    "OutputManagementServiceClientProvider",
    "OutputManagementServiceClientProviderBuilder",
    "EmailClient",
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
    # Configuration
    "DestinationCredentialConfig",
    # Constants/Enums
    "FileFormat",
    "Channel",
    "Status",
    # Exceptions
    "OutputManagementException",
    "AuthenticationException",
    "ValidationException",
    "NetworkException",
    "DestinationNotFoundException",
    "DestinationAccessException",
]




