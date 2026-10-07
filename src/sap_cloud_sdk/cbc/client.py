"""CBC client implementations for reading business configuration from CBC.

This module provides:

- :class:`CBCClient` — Protocol defining the client interface; use for type
  annotations and test doubles.
- :class:`DefaultClient` — Production client using mTLS against the CBC service.
- :func:`create_client` — Thin factory over :class:`DefaultClient`.

``base_url`` and ``app_tenant_id`` are supplied as callables, invoked on every
request. In a multi-tenant agent the CBC URL and the application tenant id both
vary per request (resolved from request-scoped context), so the client never
binds them at construction time.

Quick start::

    from sap_cloud_sdk import cbc

    cbc_client = cbc.create_client(
        base_url=lambda: resolve_cbc_url(),
        app_tenant_id=lambda: resolve_app_tenant_id(),
        ssl_context=lambda: build_ssl_ctx(),
    )
    config = cbc_client.get_configuration()
"""

from __future__ import annotations

import logging
import ssl
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigData,
    ConfigEntity,
    ConfigObject,
    ConfigObjectList,
    ConsumptionVersions,
    EntityData,
)
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCNetworkError,
    CBCServerError,
    HttpContext,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


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
# Public Protocol (interface for type annotations and test doubles)
# ---------------------------------------------------------------------------


class CBCClient(Protocol):
    """Interface for reading business configuration from CBC.

    Implement this Protocol to substitute :class:`DefaultClient` with a test
    double, offline stub, or alternative production client.
    """

    def get_consumption_versions(self) -> ConsumptionVersions:
        """Return the available consumption versions for the configured tenant.

        A consumption version represents a snapshot of the business configuration
        for an app tenant at a point in time. Use this to discover the active
        version ID when you don't already have it.
        """
        ...

    def get_configuration(
        self,
        consumption_version: str | None = None,
    ) -> ConfigData:
        """Return the business configuration for all entities in one call.

        When ``consumption_version`` is omitted, the latest version is resolved
        automatically via :meth:`get_consumption_versions`.
        """
        ...

    def get_entity_data(
        self,
        config_object_id: str,
        entity_id: str,
        consumption_version: str | None = None,
    ) -> EntityData:
        """Return the data for a single entity without fetching all configuration.

        When ``consumption_version`` is omitted, the latest version is resolved
        automatically via :meth:`get_consumption_versions`.
        """
        ...


# ---------------------------------------------------------------------------
# Internal config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ApiPaths:
    """API path configuration for a :class:`DefaultClient` instance."""

    configurations_path: str


# ---------------------------------------------------------------------------
# DefaultClient
# ---------------------------------------------------------------------------


class DefaultClient:
    """CBC client implementation.

    Prefer :func:`create_client` over direct instantiation::

        cbc_client = cbc.create_client(
            base_url=lambda: resolve_cbc_url(),
            app_tenant_id=lambda: resolve_app_tenant_id(),
            ssl_context=lambda: build_ssl_ctx(),
        )

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

    def __enter__(self) -> "DefaultClient":
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
    ) -> ConfigObjectList:
        """Return the config objects (with their entities) for the given version.

        The API returns config objects already grouped with their child entities,
        so no client-side grouping is needed.

        Args:
            base_url: Resolved CBC service base URL for this operation.
            app_tenant_id: Application tenant identifier.
            consumption_version: Consumption version ID.

        Returns:
            :class:`ConfigObjectList` containing config objects and their entities.

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
        return ConfigObjectList.model_validate(self._request("GET", url).json())

    @record_metrics(Module.CBC, Operation.CBC_GET_CONFIGURATION)
    def get_configuration(
        self,
        consumption_version: str | None = None,
    ) -> ConfigData:
        """Return the full business configuration for the configured tenant.

        Fetches the config objects and the data for every entity they contain, for
        the specified consumption version. When ``consumption_version`` is omitted,
        the latest version is resolved automatically via
        :meth:`get_consumption_versions`.

        Args:
            consumption_version: Consumption version ID. When ``None``, the
                latest version is resolved via :meth:`get_consumption_versions`.

        Returns:
            :class:`ConfigData` containing all entity data for the version.

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
        config_objects = [
            ConfigObject(
                config_object_id=entry.config_object_id,
                entities=[
                    self._fetch_entity_data(
                        base_url,
                        app_tenant_id,
                        consumption_version,
                        entry.config_object_id,
                        entity.entity_id,
                    )
                    for entity in entry.entities
                ],
            )
            for entry in co_list.items
        ]
        return ConfigData(
            consumption_version=consumption_version,
            app_tenant_id=app_tenant_id,
            config_objects=config_objects,
        )

    @record_metrics(Module.CBC, Operation.CBC_GET_ENTITY_DATA)
    def get_entity_data(
        self,
        config_object_id: str,
        entity_id: str,
        consumption_version: str | None = None,
    ) -> EntityData:
        """Return the data for a single entity without fetching all configuration.

        Makes a targeted HTTP call for the one entity, avoiding the per-entity
        calls that :meth:`get_configuration` makes for every entity in every
        config object.

        Args:
            config_object_id: Authored config object identifier (e.g. ``"payment-config"``).
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
            base_url, app_tenant_id, consumption_version, config_object_id, entity_id
        ).data

    def _fetch_entity_data(
        self,
        base_url: str,
        app_tenant_id: str,
        consumption_version: str,
        config_object_id: str,
        entity_id: str,
    ) -> ConfigEntity:
        url = self._configurations_url(
            base_url,
            f"/consumptionVersions/{consumption_version}/configurationObjects"
            f"/{config_object_id}/entities/{entity_id}/data"
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

        return ConfigEntity(entity_id=entity_id, data=EntityData(raw_data))

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
# Factory function
# ---------------------------------------------------------------------------


def create_client(
    *,
    base_url: Callable[[], str],
    app_tenant_id: Callable[[], str],
    ssl_context: Callable[[], ssl.SSLContext] | None = None,
) -> CBCClient:
    """Create a :class:`DefaultClient`.

    Args:
        base_url: Callable returning the CBC service base URL, invoked per request.
        app_tenant_id: Callable returning the application tenant id, invoked per
            request and sent as the ``appTenantId`` query parameter.
        ssl_context: Optional callable returning a freshly-built
            :class:`ssl.SSLContext` with mTLS loaded. Resolved once at
            construction, then re-invoked only on a TLS handshake failure to
            reload a rotated certificate.

    Returns:
        A configured :class:`DefaultClient`.
    """
    return DefaultClient(
        base_url=base_url,
        app_tenant_id=app_tenant_id,
        ssl_context=ssl_context,
    )
