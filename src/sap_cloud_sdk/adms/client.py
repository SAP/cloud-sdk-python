"""ADMS client module — public sync and async entry points."""

from __future__ import annotations

from typing import Callable

import httpx
import requests

from sap_cloud_sdk.adms._configuration_api import (
    _AsyncConfigurationApi,
    _ConfigurationApi,
)
from sap_cloud_sdk.adms._document_api import _AsyncDocumentApi, _DocumentApi
from sap_cloud_sdk.adms._ias_fetcher import IasTokenFetcher
from sap_cloud_sdk.adms._job_api import _AsyncJobApi, _JobApi
from sap_cloud_sdk.adms._relation_api import (
    _AsyncDocumentRelationApi,
    _DocumentRelationApi,
)
from sap_cloud_sdk.adms._token_cache import TokenCache
from sap_cloud_sdk.adms.config import (
    AdmsConfig,
    _ADMIN_SERVICE_PATH,
    _CONFIG_SERVICE_PATH,
    _SERVICE_PATH,
    load_from_env_or_mount,
)
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport


def _sync_transport(config: AdmsConfig, session: requests.Session, get_token: Callable[[], str], path: str) -> ODataHttpTransport:
    return ODataHttpTransport(base_url=config.service_url.rstrip("/") + path, session=session, get_token=get_token)


def _async_transport(config: AdmsConfig, client: httpx.AsyncClient, get_token: Callable[[], str], path: str) -> AsyncODataHttpTransport:
    return AsyncODataHttpTransport(base_url=config.service_url.rstrip("/") + path, client=client, get_token=get_token)


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

    def __init__(
        self,
        http: ODataHttpTransport,
        admin_http: ODataHttpTransport,
        config_http: ODataHttpTransport,
        *,
        _config: AdmsConfig,
        _session: requests.Session,
        _token_fetcher: IasTokenFetcher,
    ) -> None:
        self._config = _config
        self._session = _session
        self._token_fetcher = _token_fetcher
        self.documents = _DocumentApi(http)
        self.relations = _DocumentRelationApi(http)
        self.jobs = _JobApi(http, admin_http)
        self.config = _ConfigurationApi(config_http)

    def with_user_jwt(self, user_jwt: str) -> "AdmsClient":
        """Return a new :class:`AdmsClient` with user-context authentication.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            New :class:`AdmsClient` configured for user-context calls.
        """
        get_token: Callable[[], str] = lambda: self._token_fetcher.exchange_token(user_jwt)
        return AdmsClient(
            _sync_transport(self._config, self._session, get_token, _SERVICE_PATH),
            _sync_transport(self._config, self._session, get_token, _ADMIN_SERVICE_PATH),
            _sync_transport(self._config, self._session, get_token, _CONFIG_SERVICE_PATH),
            _config=self._config,
            _session=self._session,
            _token_fetcher=self._token_fetcher,
        )


class AsyncAdmsClient:
    """Async high-level client for the SAP Advanced Document Management OData V4 API.

    Use as an async context manager to ensure the underlying ``httpx.AsyncClient``
    is closed when done::

        async with create_async_client() as client:
            rel = await client.relations.create(...)

    Do **not** instantiate directly — use :func:`create_async_client`.
    Use :meth:`with_user_jwt` to obtain a user-context client from an existing one.
    """

    def __init__(
        self,
        http: AsyncODataHttpTransport,
        admin_http: AsyncODataHttpTransport,
        config_http: AsyncODataHttpTransport,
        *,
        _config: AdmsConfig,
        _httpx_client: httpx.AsyncClient,
        _token_fetcher: IasTokenFetcher,
        _owns_client: bool = True,
    ) -> None:
        self._config = _config
        self._httpx_client = _httpx_client
        self._token_fetcher = _token_fetcher
        self._owns_client = _owns_client
        self.documents = _AsyncDocumentApi(http)
        self.relations = _AsyncDocumentRelationApi(http)
        self.jobs = _AsyncJobApi(http, admin_http)
        self.config = _AsyncConfigurationApi(config_http)

    async def __aenter__(self) -> "AsyncAdmsClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_client:
            await self._httpx_client.aclose()

    async def aclose(self) -> None:
        """Close the underlying httpx client if this instance owns it."""
        if self._owns_client:
            await self._httpx_client.aclose()

    def with_user_jwt(self, user_jwt: str) -> "AsyncAdmsClient":
        """Return a new :class:`AsyncAdmsClient` with user-context authentication.

        The new instance shares the parent's ``httpx.AsyncClient`` (and its
        connection pool) and will not close it on exit.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT.

        Returns:
            New :class:`AsyncAdmsClient` for user-context calls.
        """
        get_token: Callable[[], str] = lambda: self._token_fetcher.exchange_token(user_jwt)
        return AsyncAdmsClient(
            _async_transport(self._config, self._httpx_client, get_token, _SERVICE_PATH),
            _async_transport(self._config, self._httpx_client, get_token, _ADMIN_SERVICE_PATH),
            _async_transport(self._config, self._httpx_client, get_token, _CONFIG_SERVICE_PATH),
            _config=self._config,
            _httpx_client=self._httpx_client,
            _token_fetcher=self._token_fetcher,
            _owns_client=False,
        )


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
        raise ValueError("instance must not be an empty string; omit it to use 'default'")
    binding = config or load_from_env_or_mount(instance)
    token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
    session = requests.Session()
    get_token: Callable[[], str] = (
        (lambda: token_fetcher.exchange_token(user_jwt)) if user_jwt else token_fetcher.get_token
    )
    return AdmsClient(
        _sync_transport(binding, session, get_token, _SERVICE_PATH),
        _sync_transport(binding, session, get_token, _ADMIN_SERVICE_PATH),
        _sync_transport(binding, session, get_token, _CONFIG_SERVICE_PATH),
        _config=binding,
        _session=session,
        _token_fetcher=token_fetcher,
    )


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
        raise ValueError("instance must not be an empty string; omit it to use 'default'")
    binding = config or load_from_env_or_mount(instance)
    token_fetcher = IasTokenFetcher(config=binding, cache=token_cache)
    httpx_client = http_client or httpx.AsyncClient()
    get_token: Callable[[], str] = (
        (lambda: token_fetcher.exchange_token(user_jwt)) if user_jwt else token_fetcher.get_token
    )
    return AsyncAdmsClient(
        _async_transport(binding, httpx_client, get_token, _SERVICE_PATH),
        _async_transport(binding, httpx_client, get_token, _ADMIN_SERVICE_PATH),
        _async_transport(binding, httpx_client, get_token, _CONFIG_SERVICE_PATH),
        _config=binding,
        _httpx_client=httpx_client,
        _token_fetcher=token_fetcher,
        _owns_client=http_client is None,
    )
