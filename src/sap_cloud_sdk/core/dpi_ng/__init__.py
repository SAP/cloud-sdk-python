"""DPI Next Gen SDK modules.

Shared building blocks for all DPI NG capabilities:

- :mod:`sap_cloud_sdk.core.dpi_ng.auth`         — AuthProvider ABC + strategies
- :mod:`sap_cloud_sdk.core.dpi_ng.config`        — BaseCapabilityConfig
- :mod:`sap_cloud_sdk.core.dpi_ng.exceptions`    — DPINGError hierarchy
- :mod:`sap_cloud_sdk.core.dpi_ng.odata_client`  — BaseODataClient
"""

from .auth import (
    AuthProvider,
    BearerTokenAuth,
    ClientCertificateAuth,
    ClientCredentialsAuth,
)
from .config import BaseCapabilityConfig
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ClientCreationError,
    ConflictError,
    DPINGError,
    NotFoundError,
    ODataError,
    ValidationError,
)
from .odata_client import BaseODataClient

__all__ = [
    # auth
    "AuthProvider",
    "BearerTokenAuth",
    "ClientCredentialsAuth",
    "ClientCertificateAuth",
    # config
    "BaseCapabilityConfig",
    # exceptions
    "DPINGError",
    "ClientCreationError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ODataError",
    # odata transport
    "BaseODataClient",
]
