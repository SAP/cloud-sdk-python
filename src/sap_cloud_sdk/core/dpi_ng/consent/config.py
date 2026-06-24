"""Configuration for the Consent SDK client."""

import logging
import re
from dataclasses import dataclass

from .auth import AuthProvider

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


@dataclass
class ConsentSDKConfig:
    """Configuration for the Consent SDK client.

    Args:
        base_url: Root URL of the consent service (e.g. https://consent.cfapps.eu10.hana.ondemand.com).
        auth: Authentication strategy - one of BearerTokenAuth, ClientCredentialsAuth,
              ClientCertificateAuth, or a custom AuthProvider subclass.
        timeout: HTTP request timeout in seconds (default 30).
        verify_ssl: Verify TLS certificates - set False only in local dev.
                    Ignored when ClientCertificateAuth provides its own ca_file.
        service_path: OData service base path prefix - do not override unless
                      deploying to a non-standard environment.
    """

    base_url: str
    auth: AuthProvider
    timeout: float = 30.0
    verify_ssl: bool = True
    service_path: str = "/sap/cp/kernel/dpi/consent/odata/v4"

    def __post_init__(self) -> None:
        """Validate base_url format and auth type after dataclass construction."""
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
        self.base_url = self.base_url.rstrip("/")
        logger.debug(
            "Config validated — base_url=%s verify_ssl=%s",
            self.base_url,
            self.verify_ssl,
        )
        logger.info("Exiting ConsentSDKConfig.__post_init__")
