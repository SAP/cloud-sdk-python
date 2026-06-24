"""Consent SDK - Python client for the DPI V2 Consent Repository.

Quickstart::

    from sap_cloud_sdk.core.dpi_ng.consent import create_client, BearerTokenAuth

    with create_client(
        base_url="https://consent.cfapps.eu10.hana.ondemand.com",
        auth=BearerTokenAuth("<xsuaa-bearer-token>"),
    ) as client:
        consents = client.consents.list_consents(filter="lifecycleStatusCode eq '1'")
        client.consents.withdraw_consent(WithdrawConsentRequest(...))

Entity objects returned by service methods are python-odata entity instances.
Access fields as attributes: ``entity.purpose_name``, ``entity.consent_id``, etc.
"""

from .auth import (
    AuthProvider,
    BearerTokenAuth,
    ClientCertificateAuth,
    ClientCredentialsAuth,
)
from .services import (
    ConsentConfigurationService,
    ConsentPurposeService,
    ConsentRetentionService,
    ConsentService,
    ConsentTemplateService,
)
from .config import ConsentSDKConfig
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ClientCreationError,
    ConflictError,
    ConsentSDKError,
    NotFoundError,
    ODataError,
    ValidationError,
)
from .dtos import (
    CheckConsentExistsResult,
    CreateConsentRequest,
    WithdrawConsentRequest,
)


class ConsentClient:
    """Top-level SDK client providing access to all Consent Service endpoints.

    Access each OData service through its typed attribute:

    - ``client.consents``       - consent creation, withdrawal, and reads (consentServices)
    - ``client.purposes``       - purpose CRUD and lifecycle (consentPurposeExternalServices)
    - ``client.templates``      - template CRUD and lifecycle (consentTemplateExternalServices)
    - ``client.retention``      - retention rule CRUD and lifecycle (consentRetentionExternalServices)
    - ``client.configuration``  - reference data CRUD (consentConfigurationExternalServices)
    """

    def __init__(self, config: ConsentSDKConfig) -> None:
        """Initialise all service clients from the given config."""
        from .client import _ODataClient

        self._odata = _ODataClient(config)
        self.consents: ConsentService = ConsentService(self._odata)
        self.purposes: ConsentPurposeService = ConsentPurposeService(self._odata)
        self.templates: ConsentTemplateService = ConsentTemplateService(self._odata)
        self.retention: ConsentRetentionService = ConsentRetentionService(self._odata)
        self.configuration: ConsentConfigurationService = ConsentConfigurationService(
            self._odata
        )

    def close(self) -> None:
        """Close the underlying OData HTTP session."""
        self._odata.close()

    def __enter__(self) -> "ConsentClient":
        """Support use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the session on context manager exit."""
        self.close()


def create_client(
    config: ConsentSDKConfig | None = None,
    *,
    base_url: str | None = None,
    auth: AuthProvider | None = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
) -> ConsentClient:
    """Instantiate a ConsentClient from a config object or individual keyword arguments.

    Args:
        config: Pre-built ConsentSDKConfig. When provided, all other kwargs are ignored.
        base_url: Host-only root URL of the consent service (no path).
        auth: Authentication strategy (BearerTokenAuth, ClientCredentialsAuth, etc.).
        timeout: HTTP request timeout in seconds.
        verify_ssl: Verify TLS certificates.

    Raises:
        ClientCreationError: If required fields are missing or invalid.
    """
    try:
        if config is None:
            if not base_url or not auth:
                raise ValueError(
                    "base_url and auth are required when config is not provided"
                )
            config = ConsentSDKConfig(
                base_url=base_url,
                auth=auth,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )
        return ConsentClient(config)
    except (ValueError, TypeError) as exc:
        raise ClientCreationError(str(exc)) from exc


__all__ = [
    # factory + top-level client
    "create_client",
    "ConsentClient",
    "ConsentSDKConfig",
    # auth strategies
    "AuthProvider",
    "BearerTokenAuth",
    "ClientCredentialsAuth",
    "ClientCertificateAuth",
    # exceptions
    "ConsentSDKError",
    "ClientCreationError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ODataError",
    # request / response DTOs
    "CreateConsentRequest",
    "WithdrawConsentRequest",
    "CheckConsentExistsResult",
]
