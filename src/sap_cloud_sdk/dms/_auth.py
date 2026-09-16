import logging
import time
import requests
from collections import OrderedDict
from requests.exceptions import RequestException
from typing import Callable, Optional, TypedDict
from sap_cloud_sdk.dms.exceptions import (
    DMSError,
    DMSConnectionError,
    DMSPermissionDeniedException,
)
from sap_cloud_sdk.dms.model import DMSCredentials
from sap_cloud_sdk.core._tenant import _validate_tenant_subdomain

logger = logging.getLogger(__name__)


class _TokenResponse(TypedDict):
    access_token: str
    expires_in: int


class _CachedToken:
    def __init__(self, token: str, expires_at: float) -> None:
        self.token = token
        self.expires_at = expires_at

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at - 30


_MAX_CACHE_SIZE = 10


class Auth:
    """Fetches and caches OAuth2 access tokens for DMS service requests.

    Accepts either a fixed :class:`DMSCredentials` or a config factory (any callable
    returning ``DMSCredentials`` with an optional ``has_changed() -> bool`` method).
    When a factory is supplied, credentials are re-read on every token fetch and
    the factory's ``has_changed()`` method is checked before serving a cached token
    so that rotated secrets are picked up proactively.
    """

    def __init__(
        self, credentials: DMSCredentials | Callable[[], DMSCredentials]
    ) -> None:
        if callable(credentials) and not isinstance(credentials, DMSCredentials):
            self._credentials_factory: Callable[[], DMSCredentials] = credentials
            self._credentials = credentials()
        else:
            self._credentials_factory = lambda: credentials  # type: ignore[arg-type]
            self._credentials = credentials  # type: ignore[assignment]
        self._cache: OrderedDict[str, _CachedToken] = OrderedDict()

    def _refresh_if_rotated(self) -> None:
        has_changed = getattr(self._credentials_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            logger.info("DMS credentials updated due to binding rotation")
            self._credentials = self._credentials_factory()
            self._cache.clear()

    def get_token(self, tenant_subdomain: Optional[str] = None) -> str:
        self._refresh_if_rotated()
        cache_key = tenant_subdomain or "technical"

        cached = self._cache.get(cache_key)
        if cached and cached.is_valid():
            self._cache.move_to_end(cache_key)  # Mark as recently used by moving to end
            logger.debug("Using cached token for key '%s'", cache_key)
            return cached.token

        logger.debug("Fetching new token for key '%s'", cache_key)
        token_url = self._resolve_token_url(tenant_subdomain)
        token = self._fetch_token(token_url)

        if len(self._cache) >= _MAX_CACHE_SIZE:
            evicted, _ = self._cache.popitem(last=False)
            logger.debug("Cache full — evicted token for key '%s'", evicted)

        self._cache[cache_key] = _CachedToken(
            token=token["access_token"],
            expires_at=time.monotonic() + token.get("expires_in", 3600),
        )
        logger.debug("Token cached for key '%s'", cache_key)
        return self._cache[cache_key].token

    def _resolve_token_url(self, tenant_subdomain: Optional[str]) -> str:
        if not tenant_subdomain:
            return self._credentials.token_url
        _validate_tenant_subdomain(tenant_subdomain)

        logger.debug("Resolving token URL for tenant '%s'", tenant_subdomain)
        return self._credentials.token_url.replace(
            self._credentials.identityzone,
            tenant_subdomain,
        )

    def _fetch_token(self, token_url: str) -> _TokenResponse:
        try:
            response = requests.post(
                f"{token_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._credentials.client_id,
                    "client_secret": self._credentials.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to connect to token endpoint")
            raise DMSConnectionError(
                "Failed to connect to the authentication server"
            ) from e
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            logger.error("Token request failed with status %s", status)
            if status in (401, 403):
                raise DMSPermissionDeniedException(
                    "Authentication failed — invalid client credentials", status
                ) from e
            raise DMSError("Failed to obtain access token", status) from e
        except RequestException as e:
            logger.error("Unexpected error during token fetch")
            raise DMSConnectionError("Unexpected error during authentication") from e

        payload: _TokenResponse = response.json()
        if not payload.get("access_token"):
            raise DMSError("Token response missing access_token")

        logger.debug("Token fetched successfully")
        return payload
