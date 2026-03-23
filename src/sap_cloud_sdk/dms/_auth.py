import time
import requests
from typing import Optional, TypedDict
from sap_cloud_sdk.dms.exceptions import HttpError
from sap_cloud_sdk.dms.model.model import DMSCredentials


class _TokenResponse(TypedDict):
    access_token: str
    expires_in: int


class _CachedToken:
    def __init__(self, token: str, expires_at: float) -> None:
        self.token = token
        self.expires_at = expires_at

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at - 30


class Auth:
    """Fetches and caches OAuth2 access tokens for DMS service requests."""

    def __init__(self, credentials: DMSCredentials) -> None:
        self._credentials = credentials
        self._cache: dict[str, _CachedToken] = {}

    def get_token(self, tenant_subdomain: Optional[str] = None) -> str:
        cache_key = tenant_subdomain or "techinical"

        cached = self._cache.get(cache_key)
        if cached and cached.is_valid():
            return cached.token

        token_url = self._resolve_token_url(tenant_subdomain)
        token = self._fetch_token(token_url)

        self._cache[cache_key] = _CachedToken(
            token=token["access_token"],
            expires_at=time.monotonic() + token.get("expires_in", 3600),
        )
        return self._cache[cache_key].token

    def _resolve_token_url(self, tenant_subdomain: Optional[str]) -> str:
        if not tenant_subdomain:
            return self._credentials.token_url
        return self._credentials.token_url.replace(
            self._credentials.identityzone,
            tenant_subdomain,
        )

    def _fetch_token(self, token_url: str) -> _TokenResponse:
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
        payload: _TokenResponse = response.json()

        if not payload.get("access_token"):
            raise HttpError("token response missing access_token")

        return payload