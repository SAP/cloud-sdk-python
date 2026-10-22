"""SAP Cloud SDK for Python — CBC (Central Business Configuration) module.

Provides a typed Python client for reading tenant-specific business configuration
from SAP Central Business Configuration (CBC).

CBC is an SAP service that manages tenant-specific business configuration for
SAP cloud applications and AI agents.

Quick start::

    from sap_cloud_sdk import cbc

    # Infers everything from provisioning: the app tenant id and subdomain come
    # from the SDK runtime context (wire bootstrap(app) once at startup), the CBC
    # URL from the tenant-mapping Destination Fragment, and the mTLS certificate
    # from the Destination Service.
    cbc_client = cbc.create_client()
    config = cbc_client.get_configuration()

    # Access entity data
    payment = config.get_configuration_object("payment-config")
    if payment:
        for row in payment.get_entity_data("payment-mode").as_list():
            print(row)

To override any individual piece (e.g. for local development or tests), pass a
:class:`~sap_cloud_sdk.cbc.config.CBCConfig` — see the CBC user guide.
"""

from __future__ import annotations

from sap_cloud_sdk.cbc.client import (
    CBCClient,
    create_client,
)
from sap_cloud_sdk.cbc.config import (
    CBCConfig,
)
from sap_cloud_sdk.cbc.exceptions import (
    CBCError,
    CBCClientError,
    CBCConfigError,
    CBCHttpError,
    CBCNetworkError,
    CBCServerError,
    HttpContext,
)
from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigurationData,
    ConfigurationEntity,
    ConfigurationObject,
    ConsumptionVersion,
    ConsumptionVersions,
    EntityData,
    FeatureStatus,
    FeatureStatuses,
)


__all__ = [
    # factory
    "create_client",
    # client
    "CBCClient",
    # configuration
    "CBCConfig",
    # exceptions
    "CBCError",
    "CBCClientError",
    "CBCConfigError",
    "CBCHttpError",
    "CBCNetworkError",
    "CBCServerError",
    "HttpContext",
    # models — consumption versions
    "ConsumptionVersion",
    "ConsumptionVersions",
    # models — feature status
    "FeatureStatus",
    "FeatureStatuses",
    # models — entities
    "EntityData",
    "ConfigurationEntity",
    "ConfigurationObject",
    # models — configuration
    "ConfigurationData",
    # models — api error
    "ApiError",
]
