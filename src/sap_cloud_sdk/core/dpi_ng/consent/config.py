"""Configuration for the Consent SDK client."""

import logging
from dataclasses import dataclass

from sap_cloud_sdk.core.dpi_ng.config import BaseCapabilityConfig

logger = logging.getLogger(__name__)


@dataclass
class ConsentConfig(BaseCapabilityConfig):
    """Configuration for the Consent SDK client.

    Extends :class:`BaseCapabilityConfig` with consent-specific fields.

    Args:
        base_url: URL of the DPI external service router
                  (e.g. ``https://api.service.<region>.ngdpi.dpp.cloud.sap``).
                  This URL can be found in the credentials of the ``data-privacy-integration``
                  service instance.
        auth: Authentication strategy - one of BearerTokenAuth, ClientCredentialsAuth,
              or ClientCertificateAuth.
        timeout: HTTP request timeout in seconds (default 30).
        verify_ssl: Verify TLS certificates - set False only in local dev.
                    Overridden by ``ClientCertificateAuth`` when a custom ``ca_file`` is provided.
        tenant_id: Tenant identifier sent as the ``x-tenant-id`` HTTP header.
                   **Required** for ``ClientCertificateAuth`` — mTLS does not carry a
                   tenant claim, so the service router needs it to route requests to the
                   correct tenant. Must not be provided for ``BearerTokenAuth`` or
                   ``ClientCredentialsAuth``, which already embed the tenant identity in
                   the token.
        service_path: Base path that the DPI external service router uses to identify
                      and forward requests to the consent service. Do not override unless
                      deploying to a non-standard environment.
    """

    service_path: str = "/sap/cp/kernel/dpi/consent/odata/v4"
