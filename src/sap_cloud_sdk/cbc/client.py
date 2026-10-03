"""CBC client implementations for reading business configuration from CBC.

This module provides:

- :class:`CBCClient` — Protocol defining the client interface; use for type
  annotations and test doubles.
- :class:`DefaultClient` — Production client using mTLS against the CBC service.
- :func:`create_client` — Thin factory over :class:`DefaultClient`.

``base_url`` and ``app_tenant_id`` are supplied as callables, invoked on every
request.  In a multi-tenant agent the CBC URL and the application tenant id both
vary per request (resolved from request-scoped context), so the client never
binds them at construction time.

Quick start::

    from sap_cloud_sdk import cbc

    cbc_client = cbc.create_client(
        base_url=lambda: resolve_cbc_url(),
        app_tenant_id=lambda: resolve_app_tenant_id(),
        ssl_context=ssl_ctx,
    )
    config = cbc_client.get_configuration()
"""

from __future__ import annotations

import logging
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigData,
    ConfigObject,
    ConfigObjectList,
    ConsumptionVersions,
    EntityContent,
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
        for an app tenant at a point in time.  Use this to discover the active
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


# ---------------------------------------------------------------------------
# Internal config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ClientConfig:
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
            ssl_context=ssl_ctx,
        )

    Direct instantiation is supported for testing (inject a mock ``http_client``).

    Args:
        base_url: Callable returning the CBC service base URL.  Invoked on every
            request — in a multi-tenant agent the URL comes from a request-scoped
            Destination Fragment, so it is resolved per call.
        app_tenant_id: Callable returning the application tenant identifier.
            Invoked on every request and sent as the ``appTenantId`` query
            parameter.
        http_client: Optional pre-configured ``httpx.Client`` — takes full
            precedence over ``ssl_context``.  Use for testing.
        ssl_context: Optional pre-built :class:`ssl.SSLContext` with mTLS loaded.
    """

    def __init__(
        self,
        base_url: Callable[[], str],
        app_tenant_id: Callable[[], str],
        http_client: httpx.Client | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._base_url = base_url
        self._app_tenant_id = app_tenant_id
        self._config = _ClientConfig(
            configurations_path="/configuration/v1",
        )
        self._client = http_client or httpx.Client(verify=ssl_context or True)

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()

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
        app_tenant_id = self._resolve_app_tenant_id()
        url = self._configurations_url(
            f"/consumptionVersions?appTenantId={app_tenant_id}",
        )
        return ConsumptionVersions.model_validate(self._request("GET", url).json())

    def _get_configuration_objects(
        self, app_tenant_id: str, consumption_version: str
    ) -> ConfigObjectList:
        """Return the config objects (with their entities) for the given version.

        The API returns config objects already grouped with their child entities,
        so no client-side grouping is needed.

        Args:
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
        the specified consumption version.  When ``consumption_version`` is omitted,
        the latest version is resolved automatically via
        :meth:`get_consumption_versions`.

        Args:
            consumption_version: Consumption version ID.  When ``None``, the
                latest version is resolved via :meth:`get_consumption_versions`.

        Returns:
            :class:`ConfigData` containing all entity data for the version.

        Raises:
            CBCClientError: On 4xx responses, or when no consumption version exists
                for the tenant and ``consumption_version`` was not provided.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        app_tenant_id = self._resolve_app_tenant_id()
        if consumption_version is None:
            versions = self.get_consumption_versions()
            latest = versions.latest()
            if latest is None:
                raise CBCClientError(
                    f"CBC returned no consumption version for tenant={app_tenant_id!r}."
                )
            consumption_version = latest.version

        co_list = self._get_configuration_objects(app_tenant_id, consumption_version)
        config_objects = [
            ConfigObject(
                config_object_id=entry.config_object_id,
                entities=[
                    self._fetch_entity_data(
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_entity_data(
        self,
        app_tenant_id: str,
        consumption_version: str,
        config_object_id: str,
        entity_id: str,
    ) -> EntityData:
        url = self._configurations_url(
            f"/consumptionVersions/{consumption_version}/configurationObjects"
            f"/{config_object_id}/entities/{entity_id}/data"
            f"?appTenantId={app_tenant_id}",
        )
        body = self._request("GET", url).json()

        api_meta = body.get("metadata", {}) if isinstance(body, dict) else {}
        content = body.get("content", {}) if isinstance(body, dict) else {}
        shape = body.get("contentShape") if isinstance(body, dict) else None
        if shape == "OBJECT":
            raw_data: list[dict[str, Any]] | dict[str, Any] = content.get("item", {})
        else:
            # ARRAY / UNSPECIFIED / absent — items may be absent or empty.
            raw_data = content.get("items", [])

        resolved_id = api_meta.get("entityName") or entity_id
        return EntityData(entity_id=resolved_id, data=EntityContent(raw_data))

    def _configurations_url(self, path: str = "") -> str:
        base = self._base_url().rstrip("/")
        return f"{base}{self._config.configurations_path}{path}"

    def _request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        logger.debug("CBC %s %s", method, url)
        try:
            response = self._client.request(
                method=method,
                url=url,
                headers={},
                json=body,
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            raise CBCNetworkError(
                f"Network error calling CBC: {exc}",
                http_context=HttpContext(
                    status_code=-1, request_method=method, request_url=url
                ),
            ) from exc

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


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_client(
    *,
    base_url: Callable[[], str],
    app_tenant_id: Callable[[], str],
    ssl_context: ssl.SSLContext | None = None,
) -> CBCClient:
    """Create a :class:`DefaultClient`.

    Args:
        base_url: Callable returning the CBC service base URL, invoked per request.
        app_tenant_id: Callable returning the application tenant id, invoked per
            request and sent as the ``appTenantId`` query parameter.
        ssl_context: Optional pre-built :class:`ssl.SSLContext` with mTLS loaded.

    Returns:
        A configured :class:`DefaultClient`.
    """
    return DefaultClient(
        base_url=base_url,
        app_tenant_id=app_tenant_id,
        ssl_context=ssl_context,
    )
