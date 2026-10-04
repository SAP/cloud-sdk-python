"""SAP Cloud SDK for Python — CBC (Central Business Configuration) module.

Provides a typed Python client for reading tenant-specific business configuration
from SAP Central Business Configuration (CBC).

CBC is an SAP service that manages tenant-specific business configuration for
SAP cloud applications and AI agents.

Quick start::

    from sap_cloud_sdk import cbc

    cbc_client = cbc.create_client(
        base_url=lambda: resolve_cbc_url(),
        app_tenant_id=lambda: resolve_app_tenant_id(),
        ssl_context=lambda: build_ssl_ctx(),
    )
    config = cbc_client.get_configuration()

    # Access entity data
    payment = config.get_config_object("payment-config")
    if payment:
        for row in payment.get_entity("payment-mode").data.as_list():
            print(row)

Apps running on the SAP application platform can use
:func:`~sap_cloud_sdk.cbc.client_adapter.create_agent_client` instead, which supplies the
two resolvers and the mTLS context from the platform's provisioning conventions
— see the CBC user guide.
"""

from __future__ import annotations

from sap_cloud_sdk.cbc.client import (
    CBCClient,
    DefaultClient,
    create_client,
)
from sap_cloud_sdk.cbc.client_adapter import (
    CBC_FRAGMENT_PREFIX,
    app_tenant_id_var,
    create_agent_client,
    load_ssl_context,
    resolve_app_tenant_id,
    resolve_base_url,
    tenant_subdomain_var,
)
from sap_cloud_sdk.cbc.config import (
    CBCDestinationConfig,
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
    ConfigData,
    ConfigObject,
    ConsumptionVersion,
    ConsumptionVersions,
    EntityContent,
    EntityData,
    NNV,
)


__all__ = [
    # factories
    "create_client",
    "create_agent_client",
    # clients
    "CBCClient",
    "DefaultClient",
    # platform adapter
    "app_tenant_id_var",
    "tenant_subdomain_var",
    "CBC_FRAGMENT_PREFIX",
    "CBCDestinationConfig",
    # platform resolvers (compose with create_client to override one axis)
    "resolve_base_url",
    "resolve_app_tenant_id",
    "load_ssl_context",
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
