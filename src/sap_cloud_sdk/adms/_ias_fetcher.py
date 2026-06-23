"""SAP IAS (Identity Authentication Service) token fetcher for ADMS.

Provides:
- :class:`IasTokenFetcher` — client_credentials + jwt-bearer token acquisition
  against the SAP IAS tenant, with pluggable :class:`~._token_cache.TokenCache`.

Token caching:
    By default tokens are cached in-process via :class:`InMemoryTokenCache`.
    For horizontally scaled deployments (Kyma ``replicas > 1``, Cloud Foundry
    ``instances > 1``) implement a :class:`TokenCache` subclass backed by
    your runtime's shared cache and pass it via the ``cache=`` argument to
    avoid each pod fetching its own independent token.
"""

from __future__ import annotations

from typing import Optional

import requests

from sap_cloud_sdk.adms._token_cache import InMemoryTokenCache, TokenCache
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import AuthError

# Grant types (RFC 6749 / RFC 7523)
_GRANT_CLIENT_CREDENTIALS = "client_credentials"
_GRANT_JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"

# Refresh a token this many seconds before the stated expiry to absorb clock skew.
_EXPIRY_BUFFER_SECONDS = 60

# Fallback TTL when the server omits ``expires_in``.
_DEFAULT_EXPIRES_IN = 3600

# Default cache key for the client_credentials token.
_CC_CACHE_KEY = "cc"

# HTTP timeout (seconds) for IAS token endpoint requests.
_TOKEN_REQUEST_TIMEOUT_SECONDS = 10


class IasTokenFetcher:
    """Fetches and caches OAuth2 access tokens from SAP IAS.

    Supports two grant types:

    * **client_credentials** — service-to-service calls (no user context).
    * **jwt-bearer** (OBO) — preserves user identity so that downstream
      services can enforce per-user permissions.

    Args:
        config: :class:`~sap_cloud_sdk.adms.config.AdmsConfig` with IAS
            credentials (``ias_url``, ``client_id``, ``client_secret``,
            optional ``resource``).
        session: Optional ``requests.Session`` to reuse (useful for testing).
        cache: Pluggable :class:`TokenCache`.  Defaults to
            :class:`InMemoryTokenCache`.  For multi-instance deployments,
            implement a custom :class:`TokenCache` subclass backed by your
            runtime's shared cache.

    Example::

        from sap_cloud_sdk.adms._ias_fetcher import IasTokenFetcher
        from sap_cloud_sdk.adms.config import AdmsConfig

        config = AdmsConfig(
            service_url="https://adm.example.com",
            ias_url="https://tenant.accounts.ondemand.com",
            client_id="my-client",
            client_secret="my-secret",
        )
        fetcher = IasTokenFetcher(config)
        token = fetcher.get_token()
        headers = {"Authorization": f"Bearer {token}"}
    """

    def __init__(
        self,
        config: AdmsConfig,
        session: Optional[requests.Session] = None,
        cache: Optional[TokenCache] = None,
    ) -> None:
        self._ias_url = config.ias_url.rstrip("/")
        self._client_id = config.client_id
        self._client_secret = config.client_secret
        self._session = session or requests.Session()
        self._token_url = self._ias_url + "/oauth2/token"
        self._cache: TokenCache = cache or InMemoryTokenCache()
        self._resource: Optional[str] = config.resource

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_token(self) -> str:
        """Return a valid client_credentials access token (service-to-service).

        The token is re-used until within :data:`_EXPIRY_BUFFER_SECONDS` of
        its stated expiry.

        Returns:
            A non-empty Bearer token string.

        Raises:
            AuthError: If the IAS token endpoint returns an error or the
                response is missing ``access_token``.
        """
        cached = self._cache.get(_CC_CACHE_KEY)
        if cached:
            return cached

        payload = {
            "grant_type": _GRANT_CLIENT_CREDENTIALS,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "token_format": "jwt",
        }
        if self._resource:
            payload["resource"] = self._resource
        access_token, ttl = self._fetch(payload)
        self._cache.set(_CC_CACHE_KEY, access_token, ttl)
        return access_token

    def exchange_token(self, user_jwt: str) -> str:
        """Exchange an incoming user JWT for an IAS-scoped access token (OBO).

        OBO tokens are **not cached** because each user carries a unique JWT.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            A non-empty Bearer token scoped to the target service.

        Raises:
            AuthError: If the token exchange fails.
        """
        payload = {
            "grant_type": _GRANT_JWT_BEARER,
            "assertion": user_jwt,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        access_token, _ = self._fetch(payload)
        return access_token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, payload: dict) -> tuple[str, int]:
        """POST to the IAS token endpoint.

        Returns:
            A ``(access_token, ttl_seconds)`` tuple.
        """
        try:
            resp = self._session.post(
                self._token_url,
                data=payload,
                timeout=_TOKEN_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AuthError(f"IAS token request failed: {exc}") from exc

        if not resp.ok:
            error_msg = (
                resp.json().get("error")
                if resp.headers.get("Content-Type", "").startswith("application/json")
                else "unknown error"
            )
            raise AuthError(
                f"IAS token endpoint returned HTTP {resp.status_code}: {error_msg}"
            )

        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise AuthError("IAS token response is missing 'access_token'")

        raw_expires_in = data.get("expires_in", _DEFAULT_EXPIRES_IN)
        try:
            expires_in = int(raw_expires_in)
        except (TypeError, ValueError) as exc:
            raise AuthError(
                f"IAS returned non-integer 'expires_in': {raw_expires_in!r}"
            ) from exc
        ttl = max(expires_in - _EXPIRY_BUFFER_SECONDS, 0)
        return access_token, ttl
