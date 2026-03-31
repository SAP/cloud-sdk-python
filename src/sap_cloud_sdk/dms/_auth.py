import logging
import time
import requests
from requests.exceptions import RequestException
from typing import Optional, TypedDict
from sap_cloud_sdk.dms.exceptions import DMSError, DMSConnectionError, DMSPermissionDeniedException
from sap_cloud_sdk.dms.model import DMSCredentials

logger = logging.getLogger(__name__)


class _TokenResponse(TypedDict):
    access_token: str
    expires_in: int

# TODO: limit number of access tokens in cache to 10
class _CachedToken:
    def __init__(self, token: str, expires_at: float) -> None:
        self.token = token
        self.expires_at = expires_at

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at - 30


# TODO: limit number of access tokens in cache to 10
class Auth:
    """Fetches and caches OAuth2 access tokens for DMS service requests."""

    def __init__(self, credentials: DMSCredentials) -> None:
        self._credentials = credentials
        self._cache: dict[str, _CachedToken] = {}

    def get_token(self, tenant_subdomain: Optional[str] = None) -> str:
        cache_key = tenant_subdomain or "technical"

        cached = self._cache.get(cache_key)
        if cached and cached.is_valid():
            logger.debug("Using cached token for key '%s'", cache_key)
            return cached.token

        logger.debug("Fetching new token for key '%s'", cache_key)
        token_url = self._resolve_token_url(tenant_subdomain)
        token = self._fetch_token(token_url)

        self._cache[cache_key] = _CachedToken(
            token=token["access_token"],
            expires_at=time.monotonic() + token.get("expires_in", 3600),
        )
        logger.debug("Token cached for key '%s'", cache_key)
        return self._cache[cache_key].token

    def _resolve_token_url(self, tenant_subdomain: Optional[str]) -> str:
        if not tenant_subdomain:
            return self._credentials.token_url
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
            raise DMSConnectionError("Failed to connect to the authentication server") from e
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            logger.error("Token request failed with status %s", status)
            if status in (401, 403):
                raise DMSPermissionDeniedException("Authentication failed — invalid client credentials", status) from e
            raise DMSError("Failed to obtain access token", status) from e
        except RequestException as e:
            logger.error("Unexpected error during token fetch")
            raise DMSConnectionError("Unexpected error during authentication") from e

        payload: _TokenResponse = response.json()
        if not payload.get("access_token"):
            raise DMSError("Token response missing access_token")

        logger.debug("Token fetched successfully")
        return payload
