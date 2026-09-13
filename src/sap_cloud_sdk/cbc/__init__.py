"""SAP Cloud SDK for Python — CBC (Central Business Configuration) module.

Provides a typed Python client for reading tenant-specific business configuration
from SAP Central Business Configuration (CBC).

CBC is an SAP service that manages tenant-specific business configuration for
SAP cloud applications and AI agents.

Quick start::

    from sap_cloud_sdk.cbc import create_client, TenantContext

    client = create_client()
    config = client.get_configuration(
        TenantContext(cbcTenantId="my-cbc-tenant", appTenantId="my-app-tenant")
    )

    # Access entity data
    payment = config.get_config_object("payment-config")
    if payment:
        for row in payment.get_entity("payment-mode").data.as_list():
            print(row)

Local / mock server — no credentials needed::

    from sap_cloud_sdk.cbc import DefaultClient, TenantContext

    client = DefaultClient(base_url="http://localhost:8001")
    config = client.get_configuration(
        TenantContext(cbcTenantId="t1", appTenantId="app-t1")
    )
"""

from __future__ import annotations

from sap_cloud_sdk.cbc.client import (
    CBCClient,
    DefaultClient,
    create_client,
)
from sap_cloud_sdk.cbc.config import CBCConfig
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
    ConfigData,
    ConfigObject,
    ConsumptionVersion,
    ConsumptionVersions,
    EntityContent,
    EntityData,
    NNV,
    TenantContext,
)


__all__ = [
    # factories
    "create_client",
    # clients
    "CBCClient",
    "DefaultClient",
    # config
    "CBCConfig",
    # exceptions
    "CBCError",
    "CBCClientError",
    "CBCConfigError",
    "CBCHttpError",
    "CBCNetworkError",
    "CBCServerError",
    "HttpContext",
    # models — context
    "TenantContext",
    # models — consumption versions
    "ConsumptionVersion",
    "ConsumptionVersions",
    "NNV",
    # models — entities
    "EntityContent",
    "EntityData",
    "ConfigObject",
    # models — configuration
    "ConfigData",
    # models — api error
    "ApiError",
]
