"""Consent SDK - Python client for the DPI V2 Consent Repository.

Quickstart::

    from sap_cloud_sdk.core.dpi_ng.consent import create_client, BearerTokenAuth

    with create_client(
        base_url="https://api.service.<region>.ngdpi.dpp.cloud.sap",
        auth=BearerTokenAuth("<xsuaa-bearer-token>"),
    ) as client:
        consents = client.consents.list_consents(filter="lifecycleStatusCode eq '1'")
        client.consents.withdraw_consent(WithdrawConsentRequest(...))

Entity objects returned by service methods are python-odata entity instances.
Access fields as attributes: ``entity.purpose_name``, ``entity.consent_id``, etc.
"""

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

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

    - ``client.consents``       - consent record creation, deletion, withdrawal, termination, existence check, and reads (consentServices)
    - ``client.purposes``       - purpose CRUD and lifecycle (consentPurposeExternalServices)
    - ``client.templates``      - template CRUD and lifecycle (consentTemplateExternalServices)
    - ``client.retention``      - retention rule CRUD and lifecycle (consentRetentionExternalServices)
    - ``client.configuration``  - reference data CRUD (consentConfigurationExternalServices)
    """

    def __init__(
        self,
        config: ConsentSDKConfig,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Initialise all service clients from the given config.

        Args:
            config: Validated ``ConsentSDKConfig`` containing the base URL and auth strategy.
            _telemetry_source: Internal parameter; not for end-user use.
        """
        from .client import _ODataClient

        self._telemetry_source = _telemetry_source
        self._odata = _ODataClient(config)
        self.consents: ConsentService = ConsentService(
            self._odata, _telemetry_source=_telemetry_source
        )
        self.purposes: ConsentPurposeService = ConsentPurposeService(
            self._odata, _telemetry_source=_telemetry_source
        )
        self.templates: ConsentTemplateService = ConsentTemplateService(
            self._odata, _telemetry_source=_telemetry_source
        )
        self.retention: ConsentRetentionService = ConsentRetentionService(
            self._odata, _telemetry_source=_telemetry_source
        )
        self.configuration: ConsentConfigurationService = ConsentConfigurationService(
            self._odata, _telemetry_source=_telemetry_source
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


@record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_CLIENT)
def create_client(
    config: ConsentSDKConfig | None = None,
    *,
    base_url: str | None = None,
    auth: AuthProvider | None = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    _telemetry_source: Module | None = None,
) -> ConsentClient:
    """Create a ConsentClient with explicit configuration or individual keyword arguments.

    Args:
        config: Pre-built ``ConsentSDKConfig``. When provided, all other kwargs
            are ignored.
        base_url: URL of the DPI external service router
            (e.g. ``https://api.service.<region>.ngdpi.dpp.cloud.sap``).
            Found in the credentials of the ``data-privacy-integration`` service instance.
            Required when *config* is not provided.
        auth: Authentication strategy (``BearerTokenAuth``,
            ``ClientCredentialsAuth``, ``ClientCertificateAuth``, etc.).
            Required when *config* is not provided.
        timeout: HTTP request timeout in seconds. Defaults to ``30.0``.
        verify_ssl: Whether to verify TLS certificates. Defaults to ``True``.
        _telemetry_source: Internal parameter; not for end-user use.

    Returns:
        ConsentClient ready for consent management calls.

    Raises:
        ClientCreationError: If required fields are missing or client creation fails.

    Note:
        Telemetry for client creation records only module/operation metadata and
        never includes configuration values or processed user content.
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
        return ConsentClient(config, _telemetry_source=_telemetry_source)
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
