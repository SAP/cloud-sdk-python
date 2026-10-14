"""ADMS client module — public sync and async entry points.

The four entity-scoped API classes (`_DocumentApi`, `_DocumentRelationApi`,
`_ConfigurationApi`, `_JobApi` and their async counterparts) live in
sibling modules:

- :mod:`sap_cloud_sdk.adms._document_api`
- :mod:`sap_cloud_sdk.adms._relation_api`
- :mod:`sap_cloud_sdk.adms._configuration_api`
- :mod:`sap_cloud_sdk.adms._job_api`

This module composes them into the high-level :class:`AdmsClient` /
:class:`AsyncAdmsClient` and exposes the :func:`create_client` /
:func:`create_async_client` factories.

Usage::

    from sap_cloud_sdk.adms import (
        create_client,
        create_async_client,
        RelationQueryOptions,
    )

    # Sync (service-to-service)
    client = create_client()
    relations = client.relations.get_all(
        RelationQueryOptions(
            filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
            expand=["Document"],
        )
    )

    # Async (FastAPI / LangGraph)
    async with create_async_client() as client:
        relations = await client.relations.get_all(
            RelationQueryOptions(
                filter="HostBusinessObjectNodeID eq 'PO-4500012345'",
                expand=["Document"],
            )
        )
"""

from __future__ import annotations

import httpx

from sap_cloud_sdk.adms._configuration_api import (
    _AsyncConfigurationApi,
    _ConfigurationApi,
)
from sap_cloud_sdk.adms._document_api import _AsyncDocumentApi, _DocumentApi
from sap_cloud_sdk.adms._http import AdmsHttp, AsyncAdmsHttp
from sap_cloud_sdk.adms._ias_fetcher import IasTokenFetcher
from sap_cloud_sdk.adms._job_api import _AsyncJobApi, _JobApi
from sap_cloud_sdk.adms._relation_api import (
    _AsyncDocumentRelationApi,
    _DocumentRelationApi,
)
from sap_cloud_sdk.adms._token_cache import TokenCache
from sap_cloud_sdk.adms.config import AdmsConfig, load_from_env_or_mount


# ---------------------------------------------------------------------------
# Public client classes
# ---------------------------------------------------------------------------


class AdmsClient:
    """High-level sync client for the SAP Advanced Document Management OData V4 API.

    Exposes four namespaced API objects:
    - :attr:`documents` — document metadata, download URLs, version management
    - :attr:`relations` — document ↔ business-object links, draft lifecycle, upload URLs
    - :attr:`jobs`      — async bulk download (ZIP) and GDPR erasure jobs
    - :attr:`config`    — tenant configuration (allowed domains, document types, BO node types)

    Do **not** instantiate directly — use :func:`create_client`.
    Use :meth:`with_user_jwt` to obtain a user-context client from an existing one.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http
        self.documents = _DocumentApi(http)
        self.relations = _DocumentRelationApi(http)
        self.jobs = _JobApi(http)
        self.config = _ConfigurationApi(http)

    def with_user_jwt(self, user_jwt: str) -> "AdmsClient":
        """Return a new :class:`AdmsClient` with user-context authentication.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            New :class:`AdmsClient` configured for user-context calls.
        """
        return AdmsClient(self._http.with_user_jwt(user_jwt))


class AsyncAdmsClient:
    """Async high-level client for the SAP Advanced Document Management OData V4 API.

    Use as an async context manager to ensure the underlying ``httpx.AsyncClient``
    is closed when done::

        async with create_async_client() as client:
            rel = await client.relations.create(...)

    Do **not** instantiate directly — use :func:`create_async_client`.
    Use :meth:`with_user_jwt` to obtain a user-context client from an existing one.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http
        self.documents = _AsyncDocumentApi(http)
        self.relations = _AsyncDocumentRelationApi(http)
        self.jobs = _AsyncJobApi(http)
        self.config = _AsyncConfigurationApi(http)

    async def __aenter__(self) -> "AsyncAdmsClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    def with_user_jwt(self, user_jwt: str) -> "AsyncAdmsClient":
        """Return a new :class:`AsyncAdmsClient` with user-context authentication.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT.

        Returns:
            New :class:`AsyncAdmsClient` for user-context calls.
        """
        return AsyncAdmsClient(self._http.with_user_jwt(user_jwt))


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_client(
    *,
    instance: str | None = None,
    config: AdmsConfig | None = None,
    user_jwt: str | None = None,
    token_cache: TokenCache | None = None,
) -> AdmsClient:
    """Create an :class:`AdmsClient` from a mounted secret or environment variables.

    Reads the ADM IAS service binding credentials from:
    1. ``/etc/secrets/appfnd/adms/<instance>/`` (Kubernetes / Kyma mount)
    2. ``CLOUD_SDK_CFG_ADMS_<INSTANCE>_*`` environment variables (fallback)

    Args:
        instance: Logical binding instance name.  Defaults to ``"default"``.
        config: Optional explicit :class:`~sap_cloud_sdk.adms.config.AdmsConfig`.
            When provided, ``instance`` is ignored.
        user_jwt: Optional user JWT for AMS per-user permission enforcement.
        token_cache: Optional pluggable token cache.

    Returns:
        Ready-to-use :class:`AdmsClient`.

    Raises:
        ConfigError: If the binding configuration is missing or incomplete.
        ValueError: If ``instance`` is an empty string.
    """
    if instance is not None and instance == "":
        raise ValueError(
            "instance must not be an empty string; omit it to use 'default'"
        )
    binding = config or load_from_env_or_mount(instance)
    token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
    http = AdmsHttp(config=binding, token_fetcher=token_fetcher, user_jwt=user_jwt)
    return AdmsClient(http)


def create_async_client(
    *,
    instance: str | None = None,
    config: AdmsConfig | None = None,
    user_jwt: str | None = None,
    token_cache: TokenCache | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AsyncAdmsClient:
    """Create an :class:`AsyncAdmsClient` from a mounted secret or environment variables.

    Args:
        instance: Logical binding instance name.  Defaults to ``"default"``.
        config: Optional explicit :class:`~sap_cloud_sdk.adms.config.AdmsConfig`.
            When provided, ``instance`` is ignored.
        user_jwt: Optional user JWT for OBO token exchange.
        token_cache: Optional pluggable token cache.
        http_client: Optional ``httpx.AsyncClient`` for testing/customization.

    Returns:
        Ready-to-use :class:`AsyncAdmsClient` (use as async context manager).

    Raises:
        ConfigError: If binding configuration is missing or incomplete.
        ValueError: If ``instance`` is an empty string.
    """
    if instance is not None and instance == "":
        raise ValueError(
            "instance must not be an empty string; omit it to use 'default'"
        )
    binding = config or load_from_env_or_mount(instance)
    token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
    http = AsyncAdmsHttp(
        config=binding,
        token_fetcher=token_fetcher,
        client=http_client,
        user_jwt=user_jwt,
    )
    return AsyncAdmsClient(http)
