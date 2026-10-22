"""CBC client for reading business configuration from CBC.

This module provides:

- :class:`CBCClient` — the CBC client; reads tenant-specific business
  configuration from the CBC service over mTLS.
- :func:`create_client` — the factory. Call it with no arguments to infer
  everything from the application-platform provisioning conventions, or pass a
  :class:`~sap_cloud_sdk.cbc.config.CBCConfig` to override individual pieces.

By default the client derives, per request, the CBC URL and the application
tenant id from the SDK-wide runtime context
(:mod:`sap_cloud_sdk.core.runtime_context`, populated once at startup by
``bootstrap(app)``), and loads the app's provider-level mTLS certificate from
the Destination Service. The certificate is reloaded automatically on a TLS
handshake failure, so a long-lived client recovers from certificate rotation
without being recreated.

Quick start::

    from sap_cloud_sdk import cbc

    cbc_client = cbc.create_client()   # infer everything from provisioning
    config = cbc_client.get_configuration()
"""

from __future__ import annotations

import logging
import os
import ssl
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigurationData,
    ConfigurationEntity,
    ConfigurationObject,
    ConfigurationObjectList,
    ConsumptionVersions,
    EntityData,
    FeatureStatus,
    FeatureStatuses,
)
from sap_cloud_sdk.cbc.config import CBCConfig
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCConfigError,
    CBCNetworkError,
    CBCServerError,
    HttpContext,
)
from sap_cloud_sdk.core.runtime_context import (
    APP_TENANT_ID,
    DWC_SUBDOMAIN,
    get_context,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Platform provisioning conventions
# ---------------------------------------------------------------------------
# The fragment prefix and certificate name below follow the application-platform
# convention; they are not arbitrary. Override via CBCConfig / env vars if your
# setup differs.

#: Prefix of the Destination Fragment that maps a subdomain to its CBC tenant
#: (platform convention).
CBC_FRAGMENT_PREFIX = "CBC_TenantMapping_"

#: Template for the app's own provider-level mTLS certificate name
#: (platform convention).
_CERT_NAME_TEMPLATE = "sap-managed-runtime-ias-{landscape}.pem"

# Env overrides — the defaults cover the common case; set these only to override.

#: The ``instance`` passed to the destination ``create_fragment_client`` /
#: ``create_certificate_client`` (used for secret resolution in cloud mode,
#: defaults to "default"); it is not the individual destination / cert /
#: fragment, which are selected by name.
ENV_DESTINATION_INSTANCE = "CLOUD_SDK_CBC_DESTINATION_INSTANCE"

#: Explicit certificate name, overriding the landscape-derived default.
ENV_CERT_NAME = "CLOUD_SDK_CBC_CERTIFICATE_NAME"

#: Password for the certificate keystore, if encrypted (default: none).
ENV_P12_PASSWORD = "CLOUD_SDK_CBC_P12_PASSWORD"

#: Platform landscape, used to derive the default certificate name.
ENV_LANDSCAPE = "APPFND_CONHOS_LANDSCAPE"


def _is_tls_failure(exc: BaseException) -> bool:
    """Return ``True`` if an :class:`ssl.SSLError` appears in the cause chain.

    An expired or rotated mTLS client certificate is rejected by the server at
    the TLS handshake, which httpx surfaces as a transport error (e.g.
    ``httpx.ReadError``) wrapping ``httpcore.ReadError`` wrapping
    ``ssl.SSLError``. The ``ssl.SSLError`` is not the top-level type, so walk
    the ``__cause__`` / ``__context__`` chain instead of checking ``isinstance``
    on ``exc`` directly. ``seen`` guards against a cyclic chain.
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, ssl.SSLError):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


# ---------------------------------------------------------------------------
# Internal config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ApiPaths:
    """API path configuration for a :class:`CBCClient` instance."""

    configurations_path: str
    features_path: str


# ---------------------------------------------------------------------------
# CBCClient
# ---------------------------------------------------------------------------


class CBCClient:
    """Client for reading business configuration from CBC.

    Prefer :func:`create_client` over direct instantiation::

        cbc_client = cbc.create_client()

    Direct instantiation is supported for testing (inject a mock ``http_client``).

    **Blocking I/O.** All public methods make synchronous HTTP calls via
    ``httpx.Client``. In an async context, wrap calls with
    ``asyncio.to_thread(client.get_configuration)`` to avoid blocking the event
    loop.

    **Thread safety.** Safe to share a single instance across threads and async
    tasks. The internal ``httpx.Client`` is thread-safe. The only mutable state
    is the cached ``ssl.SSLContext`` — the app's own provider-level mTLS
    certificate, which is deployment/landscape-specific and shared across all
    tenants. It is rebuilt under a lock on TLS handshake failure — concurrent
    rebuilds are safe and at most one rebuild runs at a time.

    Args:
        base_url: Callable returning the CBC service base URL. Invoked on every
            request — in a multi-tenant agent the URL comes from a request-scoped
            Destination Fragment, so it is resolved per call.
        app_tenant_id: Callable returning the application tenant identifier.
            Invoked on every request and sent as the ``appTenantId`` query
            parameter.
        http_client: Optional pre-configured ``httpx.Client`` — takes full
            precedence over ``ssl_context``. Use for testing.
        ssl_context: Optional callable returning a freshly-built
            :class:`ssl.SSLContext` with mTLS loaded. Resolved **once** at
            construction, then re-invoked **only** on a TLS handshake failure to
            pick up a rotated certificate (not per request). ``None`` for the
            plain-HTTP / local-mock path.
    """

    def __init__(
        self,
        base_url: Callable[[], str],
        app_tenant_id: Callable[[], str],
        http_client: httpx.Client | None = None,
        ssl_context: Callable[[], ssl.SSLContext] | None = None,
    ) -> None:
        self._base_url = base_url
        self._app_tenant_id = app_tenant_id
        self._config = _ApiPaths(
            configurations_path="/configuration/v1",
            features_path="/feature/v1",
        )
        self._ssl_factory = ssl_context
        self._lock = threading.Lock()
        self._http_client = http_client or self._build_http_client()

    def _build_http_client(self) -> httpx.Client:
        """Build an ``httpx.Client``, resolving the SSL context from the factory.

        ``verify`` is either the resolved mTLS :class:`ssl.SSLContext` or ``True``
        (httpx's default CA bundle) — never ``False``, so TLS verification is
        always on.
        """
        ctx = self._ssl_factory() if self._ssl_factory else None
        return httpx.Client(verify=ctx if ctx is not None else True)

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._http_client.close()

    def __enter__(self) -> "CBCClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _resolve_app_tenant_id(self) -> str:
        return self._app_tenant_id()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    @record_metrics(Module.CBC, Operation.CBC_GET_CONSUMPTION_VERSIONS)
    def get_consumption_versions(self) -> ConsumptionVersions:
        """Return available consumption versions for the configured tenant.

        A consumption version represents a snapshot of the business configuration
        for an app tenant at a point in time. Use this to discover the active
        version ID when you don't already have it.

        Returns:
            :class:`ConsumptionVersions` with all versions for the tenant.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        return self._get_consumption_versions(
            self._base_url(), self._resolve_app_tenant_id()
        )

    def _get_consumption_versions(
        self, base_url: str, app_tenant_id: str
    ) -> ConsumptionVersions:
        """Return the consumption versions, using already-resolved request values.

        Takes ``base_url`` / ``app_tenant_id`` as arguments so a caller that has
        already resolved them (e.g. :meth:`get_configuration`) does not resolve
        them a second time — resolution can hit the Destination Service, and a
        second resolve could also disagree with the first if the request context
        changed in between.

        Args:
            base_url: Resolved CBC service base URL for this operation.
            app_tenant_id: Application tenant identifier.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        url = self._configurations_url(
            base_url,
            f"/consumptionVersions?appTenantId={app_tenant_id}",
        )
        return ConsumptionVersions.model_validate(self._request("GET", url).json())

    def _get_configuration_objects(
        self, base_url: str, app_tenant_id: str, consumption_version: str
    ) -> ConfigurationObjectList:
        """Return the config objects (with their entities) for the given version.

        The API returns config objects already grouped with their child entities,
        so no client-side grouping is needed.

        Args:
            base_url: Resolved CBC service base URL for this operation.
            app_tenant_id: Application tenant identifier.
            consumption_version: Consumption version ID.

        Returns:
            :class:`ConfigurationObjectList` containing config objects and their entities.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        url = self._configurations_url(
            base_url,
            f"/consumptionVersions/{consumption_version}/configurationObjects"
            f"?appTenantId={app_tenant_id}",
        )
        return ConfigurationObjectList.model_validate(self._request("GET", url).json())

    @record_metrics(Module.CBC, Operation.CBC_GET_CONFIGURATION)
    def get_configuration(
        self,
        consumption_version: str | None = None,
    ) -> ConfigurationData:
        """Return the full business configuration for the configured tenant.

        Fetches the config objects and the data for every entity they contain, for
        the specified consumption version. When ``consumption_version`` is omitted,
        the latest version is resolved automatically via
        :meth:`get_consumption_versions`.

        Args:
            consumption_version: Consumption version ID. When ``None``, the
                latest version is resolved via :meth:`get_consumption_versions`.

        Returns:
            :class:`ConfigurationData` containing all entity data for the version.

        Raises:
            CBCClientError: On 4xx responses, or when no consumption version exists
                for the tenant and ``consumption_version`` was not provided.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        base_url = self._base_url()
        app_tenant_id = self._resolve_app_tenant_id()
        if consumption_version is None:
            versions = self._get_consumption_versions(base_url, app_tenant_id)
            latest = versions.latest()
            if latest is None:
                raise CBCClientError(
                    f"CBC returned no consumption version for tenant={app_tenant_id!r}."
                )
            consumption_version = latest.version

        co_list = self._get_configuration_objects(
            base_url, app_tenant_id, consumption_version
        )
        configuration_objects = [
            ConfigurationObject(
                configuration_object_id=entry.configuration_object_id,
                entities=[
                    self._fetch_entity_data(
                        base_url,
                        app_tenant_id,
                        consumption_version,
                        entry.configuration_object_id,
                        entity.entity_id,
                    )
                    for entity in entry.entities
                ],
            )
            for entry in co_list.items
        ]
        return ConfigurationData(
            consumption_version=consumption_version,
            app_tenant_id=app_tenant_id,
            configuration_objects=configuration_objects,
        )

    @record_metrics(Module.CBC, Operation.CBC_GET_ENTITY_DATA)
    def get_entity_data(
        self,
        configuration_object_id: str,
        entity_id: str,
        consumption_version: str | None = None,
    ) -> EntityData:
        """Return the data for a single entity without fetching all configuration.

        Makes a targeted HTTP call for the one entity, avoiding the per-entity
        calls that :meth:`get_configuration` makes for every entity in every
        config object.

        Args:
            configuration_object_id: Authored config object identifier (e.g. ``"payment-config"``).
            entity_id: Authored entity identifier (e.g. ``"payment-mode"``).
            consumption_version: Consumption version ID. When ``None``, the
                latest version is resolved via :meth:`get_consumption_versions`.

        Returns:
            :class:`EntityData` for the entity.

        Raises:
            CBCClientError: On 4xx responses, or when no consumption version exists
                for the tenant and ``consumption_version`` was not provided.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        base_url = self._base_url()
        app_tenant_id = self._resolve_app_tenant_id()
        if consumption_version is None:
            versions = self._get_consumption_versions(base_url, app_tenant_id)
            latest = versions.latest()
            if latest is None:
                raise CBCClientError(
                    f"CBC returned no consumption version for tenant={app_tenant_id!r}."
                )
            consumption_version = latest.version
        return self._fetch_entity_data(
            base_url,
            app_tenant_id,
            consumption_version,
            configuration_object_id,
            entity_id,
        ).data

    @record_metrics(Module.CBC, Operation.CBC_GET_FEATURE_STATUSES)
    def get_feature_statuses(self) -> FeatureStatuses:
        """Return the activation status of every AI feature for the configured tenant.

        Returns:
            :class:`FeatureStatuses` with one :class:`FeatureStatus` per feature.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        base_url = self._base_url()
        app_tenant_id = self._resolve_app_tenant_id()
        url = self._features_url(base_url, f"/features?appTenantId={app_tenant_id}")
        return FeatureStatuses.model_validate(self._request("GET", url).json())

    @record_metrics(Module.CBC, Operation.CBC_GET_FEATURE_STATUS)
    def get_feature_status(self, feature_id: str) -> FeatureStatus | None:
        """Return the activation status of a single AI feature for the configured tenant.

        Queries the feature endpoint filtered to both the tenant and the feature,
        so the server returns only the matching entry.

        Args:
            feature_id: Feature identifier (e.g. ``"ai_assisted_supplier_bid_analysis"``).

        Returns:
            The matching :class:`FeatureStatus`, or ``None`` if the feature is not
            found for the tenant.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        base_url = self._base_url()
        app_tenant_id = self._resolve_app_tenant_id()
        url = self._features_url(
            base_url,
            f"/features?appTenantId={app_tenant_id}&featureId={feature_id}",
        )
        statuses = FeatureStatuses.model_validate(self._request("GET", url).json())
        return statuses.get(feature_id)

    def _features_url(self, base_url: str, path: str = "") -> str:
        base = base_url.rstrip("/")
        return f"{base}{self._config.features_path}{path}"

    def _fetch_entity_data(
        self,
        base_url: str,
        app_tenant_id: str,
        consumption_version: str,
        configuration_object_id: str,
        entity_id: str,
    ) -> ConfigurationEntity:
        url = self._configurations_url(
            base_url,
            f"/consumptionVersions/{consumption_version}/configurationObjects"
            f"/{configuration_object_id}/entities/{entity_id}/data"
            f"?appTenantId={app_tenant_id}",
        )
        body = self._request("GET", url).json()

        content = body.get("content", {}) if isinstance(body, dict) else {}
        shape = body.get("contentShape") if isinstance(body, dict) else None
        if shape == "OBJECT":
            raw_data: list[dict[str, Any]] | dict[str, Any] = content.get("item", {})
        else:
            # ARRAY / UNSPECIFIED / absent — items may be absent or empty.
            raw_data = content.get("items", [])

        return ConfigurationEntity(entity_id=entity_id, data=EntityData(raw_data))

    def _configurations_url(self, base_url: str, path: str = "") -> str:
        base = base_url.rstrip("/")
        return f"{base}{self._config.configurations_path}{path}"

    def _request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        logger.debug("CBC %s %s", method, url)
        try:
            response = self._send(method, url, body)
        except httpx.TransportError as exc:
            # A TLS handshake failure (e.g. an expired/rotated client cert) is
            # recoverable: rebuild the client from a fresh SSL context once and
            # retry this one request. Non-TLS transport errors and all other
            # request errors fall through to the terminal handler below.
            if self._ssl_factory is not None and _is_tls_failure(exc):
                logger.info("CBC TLS failure; reloading certificate and retrying")
                self._rebuild_http_client()
                try:
                    response = self._send(method, url, body)
                except httpx.RequestError as retry_exc:
                    raise self._network_error(method, url, retry_exc) from retry_exc
            else:
                raise self._network_error(method, url, exc) from exc
        except httpx.RequestError as exc:
            raise self._network_error(method, url, exc) from exc

        if response.status_code >= 400:
            ctx = HttpContext(
                status_code=response.status_code,
                request_method=method,
                request_url=url,
            )
            error = ApiError.from_response(response.content)
            exc_class = (
                CBCServerError if response.status_code >= 500 else CBCClientError
            )
            raise exc_class(error.message, code=error.code, http_context=ctx)

        return response

    def _send(
        self, method: str, url: str, body: dict[str, Any] | None
    ) -> httpx.Response:
        """Perform one HTTP request via the underlying client.

        A thin wrapper over ``self._http_client.request`` with no error translation —
        callers map failures to CBC exceptions and own any retry logic.
        """
        return self._http_client.request(
            method=method,
            url=url,
            headers={},
            json=body,
            timeout=30.0,
        )

    def _rebuild_http_client(self) -> None:
        """Rebuild the HTTP client from a fresh SSL context, under a lock.

        Called on a TLS failure to pick up a rotated certificate. Guards against
        a thundering herd — if another thread already rebuilt while this one
        waited on the lock, reuse that client instead of rebuilding again.

        The new client is built into a local before it replaces ``self._http_client``,
        so a failing factory (which raises :class:`CBCConfigError` — the cert
        loader wraps every load-time failure) leaves ``self._http_client`` on the prior
        working context and the error propagates to the caller.
        """
        with self._lock:
            previous = self._http_client
            new_client = self._build_http_client()
            self._http_client = new_client
            previous.close()

    def _network_error(self, method: str, url: str, exc: Exception) -> CBCNetworkError:
        return CBCNetworkError(
            f"Network error calling CBC: {exc}",
            http_context=HttpContext(
                status_code=-1, request_method=method, request_url=url
            ),
        )


# ---------------------------------------------------------------------------
# Default platform resolvers
# ---------------------------------------------------------------------------
# These encode the SAP application-platform provisioning convention: the app
# tenant id and subdomain come from the SDK-wide runtime context (populated at
# startup by bootstrap(app)); the CBC URL comes from the tenant-mapping Fragment
# written during provisioning; the mTLS certificate comes from the Destination
# Service. create_client wires these in whenever CBCConfig leaves the matching
# field unset.


def _resolve_app_tenant_id() -> str:
    """Return the application tenant id from the SDK runtime context.

    Reads :data:`~sap_cloud_sdk.core.runtime_context.APP_TENANT_ID` (the IAS
    ``app_tid`` claim, populated by ``bootstrap(app)``). The application tenant
    id identifies the subscriber tenant to CBC and is sent as the ``appTenantId``
    query parameter.

    Raises:
        CBCConfigError: If no app tenant id is present in the runtime context.
    """
    app_tid = get_context().get(APP_TENANT_ID)
    if not app_tid:
        raise CBCConfigError(
            "No app tenant id in the runtime context — ensure bootstrap(app) is "
            "wired so the IAS app_tid claim is populated, or override app_tenant_id "
            "on CBCConfig."
        )
    return app_tid


def _resolve_base_url(destination_instance: str) -> str:
    """Return the CBC base URL for the current tenant.

    Reads the subscriber subdomain from the SDK runtime context
    (:data:`~sap_cloud_sdk.core.runtime_context.DWC_SUBDOMAIN`), fetches the
    tenant-mapping Fragment for that subdomain directly by name
    (``CBC_TenantMapping_<subdomain>``), and returns its ``cbcUrl`` property
    verbatim.

    Args:
        destination_instance: The ``instance`` passed to the destination
            ``create_fragment_client`` (selects which Destination Service binding
            to read, used for secret resolution in cloud mode).

    Raises:
        CBCConfigError: If the subdomain is absent from the runtime context, no
            matching fragment is found, or the matched fragment has no ``cbcUrl``
            property.
    """
    from sap_cloud_sdk.destination import AccessStrategy, create_fragment_client
    from sap_cloud_sdk.destination.exceptions import DestinationError

    subdomain = get_context().get(DWC_SUBDOMAIN)
    if not subdomain:
        raise CBCConfigError(
            "No subdomain in the runtime context — ensure bootstrap(app) is wired "
            "so the dwc-subdomain is populated, or override base_url on CBCConfig."
        )

    fragment_name = f"{CBC_FRAGMENT_PREFIX}{subdomain}"
    try:
        client = create_fragment_client(instance=destination_instance)
        fragment = client.get_subaccount_fragment(
            fragment_name,
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
            tenant=subdomain,
        )
    except DestinationError as exc:
        raise CBCConfigError(
            f"Could not resolve the CBC URL: fetching tenant-mapping fragment "
            f"{fragment_name!r} failed for subdomain={subdomain!r}: {exc}"
        ) from exc
    if fragment is None:
        raise CBCConfigError(
            f"No CBC mapping fragment for subdomain={subdomain!r}: "
            f"{fragment_name!r} not found."
        )
    cbc_url = fragment.properties.get("cbcUrl")
    if not cbc_url:
        raise CBCConfigError(
            f"CBC mapping fragment {fragment.name!r} has no 'cbcUrl' property."
        )
    return cbc_url


def _load_ssl_context(
    destination_instance: str, cert_name: str, p12_password: bytes | None
) -> ssl.SSLContext:
    """Fetch the provider certificate and load it into an :class:`ssl.SSLContext`.

    Args:
        destination_instance: The ``instance`` passed to the destination
            ``create_certificate_client`` (selects which Destination Service
            binding to read, used for secret resolution in cloud mode).
        cert_name: Name of the subaccount certificate to fetch.
        p12_password: Certificate keystore password, or ``None`` if unencrypted.

    Raises:
        CBCConfigError: If the certificate cannot be fetched or is not found.
    """
    from sap_cloud_sdk.destination import AccessStrategy, create_certificate_client
    from sap_cloud_sdk.destination._cert_loader import _load_pem
    from sap_cloud_sdk.destination.exceptions import DestinationError

    try:
        cert = create_certificate_client(
            instance=destination_instance
        ).get_subaccount_certificate(
            cert_name, access_strategy=AccessStrategy.PROVIDER_ONLY
        )
    except DestinationError as exc:
        raise CBCConfigError(
            f"Could not fetch the mTLS certificate {cert_name!r} from Destination "
            f"Service instance {destination_instance!r}: {exc}"
        ) from exc
    if cert is None:
        raise CBCConfigError(
            f"Subaccount certificate {cert_name!r} not found in Destination "
            f"Service instance {destination_instance!r}."
        )
    return _load_pem(cert.content, p12_password, cert.name)


def _default_cert_name() -> str:
    """Return the name of the app's provider-level mTLS certificate.

    This is the certificate the app presents to CBC for the mTLS handshake; its
    name follows the platform convention :data:`_CERT_NAME_TEMPLATE`, with the
    landscape filled in from :data:`ENV_LANDSCAPE`.

    Raises:
        CBCConfigError: If :data:`ENV_LANDSCAPE` is not set, so the name cannot
            be derived.
    """
    landscape = os.environ.get(ENV_LANDSCAPE)
    if not landscape:
        raise CBCConfigError(
            f"Cannot derive the CBC certificate name: {ENV_LANDSCAPE} is not set. "
            f"Set it, or pass cbc_cert_name on CBCConfig."
        )
    return _CERT_NAME_TEMPLATE.format(landscape=landscape)


def _cert_password_from_env() -> bytes | None:
    """Return the cert keystore password from :data:`ENV_P12_PASSWORD`, or ``None``."""
    raw = os.environ.get(ENV_P12_PASSWORD)
    return raw.encode() if raw else None


def _as_callable(value: str | Callable[[], str]) -> Callable[[], str]:
    """Return ``value`` as a callable — wrap a plain string in a lambda."""
    if isinstance(value, str):
        return lambda: value
    return value


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_client(config: CBCConfig | None = None) -> CBCClient:
    """Create a CBC client.

    Called with no arguments, the client infers everything from the SAP
    application-platform provisioning conventions:

    - ``app_tenant_id`` and the subscriber subdomain come from the SDK-wide
      runtime context (populated once at startup by ``bootstrap(app)``);
    - the CBC URL comes from the tenant-mapping Destination Fragment written
      during provisioning;
    - the mTLS certificate comes from the Destination Service, reloaded
      automatically on a TLS handshake failure (certificate rotation).

    Pass a :class:`~sap_cloud_sdk.cbc.config.CBCConfig` to override any individual
    piece. Each override wins over its ``CLOUD_SDK_CBC_*`` env var, which in turn
    falls back to the platform default. Note that the mTLS certificate loader is
    the default **only** in pure provisioning mode: once ``base_url`` or
    ``app_tenant_id`` is overridden (e.g. pointing at a local mock), an unset
    ``ssl_context`` means plain HTTPS — set ``ssl_context`` explicitly if you still
    need a client certificate.

    Args:
        config: Optional overrides. Leave ``None`` to infer everything from
            provisioning. Set ``base_url`` / ``app_tenant_id`` / ``ssl_context``
            to bypass the corresponding default resolver; set
            ``destination_instance`` / ``cbc_cert_name`` / ``p12_password`` to
            steer the default certificate / fragment lookup. See
            :class:`~sap_cloud_sdk.cbc.config.CBCConfig`.

    Returns:
        A configured :class:`CBCClient`.

    Raises:
        CBCConfigError: If the certificate name cannot be resolved, or — when a
            request is made — if the certificate cannot be fetched, the runtime
            context is missing the tenant id / subdomain, or the tenant-mapping
            fragment is missing.
    """
    if config is None:
        config = CBCConfig()

    destination_instance = config.destination_instance
    if destination_instance is None:
        destination_instance = os.environ.get(ENV_DESTINATION_INSTANCE, "default")

    # app_tenant_id — explicit override else the runtime-context resolver.
    if config.app_tenant_id is not None:
        app_tenant_id = _as_callable(config.app_tenant_id)
    else:
        app_tenant_id = _resolve_app_tenant_id

    # base_url — explicit override else the tenant-mapping fragment resolver.
    if config.base_url is not None:
        base_url = _as_callable(config.base_url)
    else:
        base_url = lambda: _resolve_base_url(destination_instance)  # noqa: E731

    # ssl_context — explicit override else the Destination-Service cert loader.
    # The mTLS loader is the default only in pure provisioning mode (neither
    # base_url nor app_tenant_id overridden). Once a caller supplies either axis
    # — e.g. pointing at a local mock — an unset ssl_context means plain HTTPS
    # (public CA bundle, no client cert), so they are not forced to also set the
    # platform landscape env or carry a certificate. The default loader resolves
    # the certificate name/password lazily, inside the factory, consistent with
    # the other default resolvers that only touch provisioning when invoked.
    if config.ssl_context is not None:
        ssl_context: Callable[[], ssl.SSLContext] | None = config.ssl_context
    elif config.base_url is not None or config.app_tenant_id is not None:
        ssl_context = None
    else:
        cfg_cert_name = config.cbc_cert_name
        cfg_password = config.p12_password

        def ssl_context() -> ssl.SSLContext:
            cert_name = (
                cfg_cert_name or os.environ.get(ENV_CERT_NAME) or _default_cert_name()
            )
            password = (
                cfg_password if cfg_password is not None else _cert_password_from_env()
            )
            return _load_ssl_context(destination_instance, cert_name, password)

    return CBCClient(
        base_url=base_url,
        app_tenant_id=app_tenant_id,
        ssl_context=ssl_context,
    )
