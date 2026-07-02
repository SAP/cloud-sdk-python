"""Configuration for the Consent SDK client."""

import logging
import re
from dataclasses import dataclass

from .auth import AuthProvider, ClientCertificateAuth

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


@dataclass
class ConsentSDKConfig:
    """Configuration for the Consent SDK client.

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
        service_path: Base path that the DPI external service router uses to identify
                      and forward requests to the consent service. Do not override unless
                      deploying to a non-standard environment.
        tenant_id: Tenant identifier sent as the ``x-tenant-id`` HTTP header.
                   **Required** for ``ClientCertificateAuth`` — mTLS does not carry a
                   tenant claim, so the service router needs it to route requests to the
                   correct tenant. Must not be provided for ``BearerTokenAuth`` or
                   ``ClientCredentialsAuth``, which already embed the tenant identity in
                   the token.
    """

    base_url: str
    auth: AuthProvider
    timeout: float = 30.0
    verify_ssl: bool = True
    service_path: str = "/sap/cp/kernel/dpi/consent/odata/v4"
    tenant_id: str | None = None

    def __post_init__(self) -> None:
        """Validate config after dataclass construction.

        Raises:
            ValueError: If *base_url* is not a valid HTTP(S) URL, *auth* is not an
                ``AuthProvider`` instance, ``ClientCertificateAuth`` is used without
                *tenant_id*, or *tenant_id* is provided with a non-cert auth type.
        """
        logger.info("Invoked ConsentSDKConfig.__post_init__")
        if not _URL_PATTERN.match(self.base_url):
            logger.error("Invalid base_url — value=%r", self.base_url)
            raise ValueError(
                f"base_url must be a valid HTTP(S) URL, got: {self.base_url!r}"
            )
        if not isinstance(self.auth, AuthProvider):
            logger.error(
                "auth is not an AuthProvider instance — type=%s", type(self.auth)
            )
            raise ValueError("auth must be an AuthProvider instance")
        is_cert_auth = isinstance(self.auth, ClientCertificateAuth)
        if is_cert_auth and not self.tenant_id:
            logger.error("tenant_id is required for ClientCertificateAuth")
            raise ValueError(
                "tenant_id is required when using ClientCertificateAuth"
            )
        if not is_cert_auth and self.tenant_id is not None:
            logger.error(
                "tenant_id is not applicable for %s", type(self.auth).__name__
            )
            raise ValueError(
                f"tenant_id must not be set for {type(self.auth).__name__}; "
                "it is only valid for ClientCertificateAuth"
            )
        self.base_url = self.base_url.rstrip("/")
        logger.debug(
            "Config validated — base_url=%s verify_ssl=%s",
            self.base_url,
            self.verify_ssl,
        )
        logger.info("Exiting ConsentSDKConfig.__post_init__")
