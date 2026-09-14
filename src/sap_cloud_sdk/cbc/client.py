"""CBC client implementations for reading business configuration from CBC.

This module provides:

- :class:`CBCClient` — Protocol defining the client interface; use for type
  annotations and test doubles.
- :class:`DefaultClient` — Production client.  Handles both production (mTLS +
  envoy subdomain routing) and local/mock mode (detected automatically from the URL).
- :func:`create_client` — Factory that resolves the right client from environment
  variables via :func:`~sap_cloud_sdk.cbc.config.load_from_env`.

Quick start::

    from sap_cloud_sdk.cbc import create_client, TenantContext

    client = create_client()
    config = client.get_configuration(
        TenantContext(cbcTenantId="my-cbc-tenant", appTenantId="my-app-tenant")
    )
"""

from __future__ import annotations

import logging
import re
import ssl
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import httpx

if TYPE_CHECKING:
    from sap_cloud_sdk.cbc.config import CBCConfig

from sap_cloud_sdk.cbc._http import _LazyCertTransport, _is_local_url
from sap_cloud_sdk.cbc._models import (
    ApiError,
    ConfigData,
    ConfigObject,
    ConsumptionVersions,
    Entities,
    Entity,
    EntityContent,
    EntityData,
    TenantContext,
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

    def get_consumption_versions(
        self, tenant_context: TenantContext
    ) -> ConsumptionVersions:
        """Return the available consumption versions for the given tenant.

        A consumption version represents a snapshot of the business configuration
        for an app tenant at a point in time.  Use this to discover the active
        version ID when you don't already have it.
        """
        ...

    def get_configuration(
        self,
        tenant_context: TenantContext,
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
    """API path and routing configuration for a :class:`DefaultClient` instance."""

    configurations_path: str
    replace_subdomain: bool


# ---------------------------------------------------------------------------
# DefaultClient
# ---------------------------------------------------------------------------


class DefaultClient:
    """CBC client for both production (mTLS + envoy) and local/mock environments.

    **Production** (any ``https://`` or non-loopback URL): subdomain-per-tenant
    routing rewrites the URL subdomain to the ``cbc_tenant_id`` for each request;
    mTLS credentials must be provided via ``cert_path``/``key_path``,
    ``cert_pem``/``key_pem``, or ``ssl_context``.

    **Local / mock** (``http://localhost``, ``http://127.0.0.1``, ``http://[::1]``):
    no subdomain replacement, no mTLS — detected automatically from the URL.
    Point it at the CBC mock server and it works without any extra arguments.

    Do **not** instantiate directly — use :func:`create_client` in production
    code, which resolves credentials from the environment automatically.

    Example (local mock)::

        client = DefaultClient(base_url="http://localhost:8001")
        config = client.get_configuration(
            TenantContext(cbcTenantId="t1", appTenantId="app-t1")
        )

    Example (production)::

        client = DefaultClient(
            base_url="https://cbc.example.ondemand.com",
            cert_path=Path("/run/secrets/tls.crt"),
            key_path=Path("/run/secrets/tls.key"),
        )

    Args:
        base_url: Base URL of the CBC service.  Loopback addresses trigger
            local mode automatically.
        http_client: Optional pre-configured ``httpx.Client`` — takes full
            precedence over all mTLS arguments.  Use for testing.
        ssl_context: Optional pre-built :class:`ssl.SSLContext` with mTLS loaded.
        cert_path: Path to the PEM client certificate file.  Requires ``key_path``.
        key_path: Path to the PEM private key file.  Requires ``cert_path``.
        cert_pem: Raw PEM string for the client certificate.  Requires ``key_pem``.
            Written to a temp file deleted after the first connection.
        key_pem: Raw PEM string for the private key.  Requires ``cert_pem``.
    """

    def __init__(
        self,
        base_url: str,
        http_client: httpx.Client | None = None,
        ssl_context: ssl.SSLContext | None = None,
        cert_path: Path | None = None,
        key_path: Path | None = None,
        cert_pem: str | None = None,
        key_pem: str | None = None,
        replace_subdomain: bool | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        resolved_replace = (
            replace_subdomain
            if replace_subdomain is not None
            else not _is_local_url(base_url)
        )
        self._config = _ClientConfig(
            configurations_path="/configuration/v1",
            replace_subdomain=resolved_replace,
        )

        if http_client is None and ssl_context is None:
            if cert_path is not None and key_path is not None:
                transport = _LazyCertTransport(str(cert_path), str(key_path))
                http_client = httpx.Client(transport=transport)
            elif cert_pem is not None and key_pem is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as cf:
                    cf.write(cert_pem.encode())
                    cert_file = cf.name
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as kf:
                    kf.write(key_pem.encode())
                    key_file = kf.name
                transport = _LazyCertTransport(
                    cert_file, key_file, delete_after_load=True
                )
                http_client = httpx.Client(transport=transport)

        self._client = http_client or httpx.Client(verify=ssl_context or True)

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()

    def __enter__(self) -> "DefaultClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    @record_metrics(Module.CBC, Operation.CBC_GET_CONSUMPTION_VERSIONS)
    def get_consumption_versions(
        self, tenant_context: TenantContext
    ) -> ConsumptionVersions:
        """Return available consumption versions for the given tenant.

        Args:
            tenant_context: Tenant identification.

        Returns:
            :class:`ConsumptionVersions` with all versions for the tenant.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        url = self._configurations_url(
            tenant_context,
            f"/consumptionVersions?appTenantId={tenant_context.app_tenant_id}",
        )
        return ConsumptionVersions.model_validate(self._request("GET", url).json())

    def _get_entities(
        self, tenant_context: TenantContext, consumption_version: str
    ) -> Entities:
        """Return the entities for the given tenant and consumption version.

        Args:
            tenant_context: Tenant identification.
            consumption_version: Consumption version ID.

        Returns:
            :class:`Entities` containing entity metadata.

        Raises:
            CBCClientError: On 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        url = self._configurations_url(
            tenant_context,
            f"/consumptionVersions/{consumption_version}/entities"
            f"?appTenantId={tenant_context.app_tenant_id}",
        )
        return Entities.model_validate(self._request("GET", url).json())

    def _get_entity_data(
        self,
        tenant_context: TenantContext,
        consumption_version: str,
        entity_id: str,
    ) -> EntityData:
        """Return configuration rows for the given entity.

        Args:
            tenant_context: Tenant identification.
            consumption_version: Consumption version ID.
            entity_id: Entity identifier.

        Returns:
            :class:`EntityData` with metadata and configuration rows.

        Raises:
            CBCClientError: If the entity is not found, or on other 4xx responses.
            CBCServerError: On 5xx responses.
            CBCNetworkError: On connection failures.
        """
        return self._fetch_entity_data(
            tenant_context, consumption_version, Entity(entityId=entity_id)
        )

    @record_metrics(Module.CBC, Operation.CBC_GET_CONFIGURATION)
    def get_configuration(
        self,
        tenant_context: TenantContext,
        consumption_version: str | None = None,
    ) -> ConfigData:
        """Return the full business configuration for the given tenant.

        Fetches all entities and their data for the specified consumption version.
        When ``consumption_version`` is omitted, the latest version is resolved
        automatically via :meth:`get_consumption_versions`.

        Args:
            tenant_context: Tenant identification.
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
        if consumption_version is None:
            versions = self.get_consumption_versions(tenant_context)
            latest = versions.latest()
            if latest is None:
                raise CBCClientError(
                    f"CBC returned no consumption version for "
                    f"tenant={tenant_context.app_tenant_id!r}."
                )
            consumption_version = latest.version

        entities = self._get_entities(tenant_context, consumption_version)
        if not entities.items:
            return ConfigData(
                consumption_version=consumption_version,
                tenant_context=tenant_context,
                config_objects=[],
            )

        entity_data_list = [
            self._fetch_entity_data(tenant_context, consumption_version, entity)
            for entity in entities.items
        ]

        grouped: dict[str, list[EntityData]] = {}
        for ed, entity in zip(entity_data_list, entities.items):
            key = entity.config_object_id or ""
            grouped.setdefault(key, []).append(ed)

        config_objects = [
            ConfigObject(config_object_id=co_id, entities=eds)
            for co_id, eds in grouped.items()
        ]
        return ConfigData(
            consumption_version=consumption_version,
            tenant_context=tenant_context,
            config_objects=config_objects,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_entity_data(
        self,
        tenant_context: TenantContext,
        consumption_version: str,
        entity: Entity,
    ) -> EntityData:
        url = self._configurations_url(
            tenant_context,
            f"/consumptionVersions/{consumption_version}/entities"
            f"/{entity.internal_id}/data"
            f"?appTenantId={tenant_context.app_tenant_id}",
        )
        response_data = self._request("GET", url).json()

        api_meta = (
            response_data.get("metadata", {}) if isinstance(response_data, dict) else {}
        )
        raw_data = (
            response_data["items"]
            if isinstance(response_data, dict) and "items" in response_data
            else response_data
        )
        entity_id = entity.entity_id or api_meta.get("entityName") or entity.internal_id
        return EntityData(entity_id=entity_id, data=EntityContent(raw_data))

    def _configurations_url(self, tenant_context: TenantContext, path: str = "") -> str:
        base = self._base_url
        if self._config.replace_subdomain:
            base = re.sub(
                r"^(https?://)[^.]+\.",
                rf"\g<1>{tenant_context.cbc_tenant_id}.",
                base,
            )
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


def create_client(*, config: CBCConfig | None = None) -> CBCClient:
    """Create a :class:`DefaultClient` from environment variables or an explicit config.

    When ``config`` is omitted, credentials are resolved via
    :func:`~sap_cloud_sdk.cbc.config.load_from_env` (reads
    ``CLOUD_SDK_CBC_URL``, ``CLOUD_SDK_CBC_CERT_PATH``, ``CLOUD_SDK_CBC_KEY_PATH``).

    Args:
        config: Optional explicit :class:`~sap_cloud_sdk.cbc.config.CBCConfig`.
            When provided, env resolution is skipped entirely.

    Returns:
        A configured :class:`DefaultClient`.

    Raises:
        CBCConfigError: If no configuration is provided and none can be resolved
            from the environment.
    """
    from sap_cloud_sdk.cbc.config import load_from_env

    resolved: CBCConfig = config if config is not None else load_from_env()
    return DefaultClient(
        base_url=resolved.base_url,
        cert_path=resolved.cert_path,
        key_path=resolved.key_path,
        cert_pem=resolved.cert_pem,
        key_pem=resolved.key_pem,
        replace_subdomain=resolved.replace_subdomain,
    )
