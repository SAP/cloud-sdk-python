"""HTTP transport for the Agent Memory service.

Handles OAuth2 ``client_credentials`` token acquisition with lazy,
expiry-aware caching per tenant subdomain. If ``token_url`` is not configured,
requests are sent unauthenticated — expected for local development environments.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import quote, urlencode

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests.exceptions import RequestException, Timeout
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
)

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 60


class HttpTransport:
    """Internal HTTP transport for the Agent Memory service.

    Manages OAuth2 token lifecycle (lazy acquire + expiry-aware caching) per
    tenant subdomain and attaches the ``Authorization`` header automatically.
    In no-auth mode (no ``token_url``), a plain ``requests.Session`` is used.

    Args:
        config: Service configuration.
    """

    def __init__(self, config: AgentMemoryConfig) -> None:
        self._config = config
        # Keyed by tenant_subdomain (None = provider token)
        self._oauth_cache: dict[Optional[str], tuple[OAuth2Session, datetime]] = {}
        self._plain_session: Optional[requests.Session] = None

    def close(self) -> None:
        """Close all underlying HTTP sessions and release resources."""
        for oauth, _ in self._oauth_cache.values():
            oauth.close()
        self._oauth_cache.clear()
        if self._plain_session is not None:
            self._plain_session.close()
            self._plain_session = None

    # ── Public HTTP methods ────────────────────────────────────────────────────

    def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> dict[str, Any]:
        """Perform a GET request.

        Args:
            path: API path (appended to ``base_url``).
            params: Optional query parameters.
            tenant_subdomain: Subscriber tenant subdomain for token derivation.

        Returns:
            Parsed JSON response body.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request(
            "GET", path, params=params, tenant_subdomain=tenant_subdomain
        )

    def post(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> dict[str, Any]:
        """Perform a POST request.

        Args:
            path: API path (appended to ``base_url``).
            json: Optional request body dict (serialised to JSON).
            tenant_subdomain: Subscriber tenant subdomain for token derivation.

        Returns:
            Parsed JSON response body. Returns an empty dict for 204 responses.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request("POST", path, json=json, tenant_subdomain=tenant_subdomain)

    def patch(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> dict[str, Any]:
        """Perform a PATCH request.

        Args:
            path: API path (appended to ``base_url``).
            json: Optional request body dict (serialised to JSON).
            tenant_subdomain: Subscriber tenant subdomain for token derivation.

        Returns:
            Parsed JSON response body. Returns an empty dict for 204 responses.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request(
            "PATCH", path, json=json, tenant_subdomain=tenant_subdomain
        )

    def delete(self, path: str, *, tenant_subdomain: Optional[str] = None) -> None:
        """Perform a DELETE request.

        Args:
            path: API path (appended to ``base_url``).
            tenant_subdomain: Subscriber tenant subdomain for token derivation.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        self._request("DELETE", path, tenant_subdomain=tenant_subdomain)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_session(self, tenant_subdomain: Optional[str]) -> requests.Session:
        """Return a session ready to make requests for the given tenant.

        In no-auth mode, returns a plain ``requests.Session`` (created once).
        In OAuth2 mode, returns an ``OAuth2Session`` with a valid token,
        fetching or refreshing per-tenant as needed.
        """
        if not self._config.token_url:
            if self._plain_session is None:
                self._plain_session = requests.Session()
            return self._plain_session

        cached = self._oauth_cache.get(tenant_subdomain)
        if cached is not None:
            oauth, expires_at = cached
            if datetime.now() < expires_at:
                return oauth

        return self._fetch_token(tenant_subdomain)

    def _fetch_token(self, tenant_subdomain: Optional[str]) -> OAuth2Session:
        """Acquire a new OAuth2 ``client_credentials`` token for the given tenant.

        When ``tenant_subdomain`` is provided and ``config.identityzone`` is set,
        derives the subscriber token URL by replacing the provider identityzone
        in ``token_url`` with ``tenant_subdomain``.

        Returns:
            An ``OAuth2Session`` with a valid token attached.

        Raises:
            AgentMemoryHttpError: If the token endpoint returns an error or is unreachable.
        """
        token_url = self._config.token_url
        if (
            tenant_subdomain is not None
            and self._config.identityzone is not None
            and token_url is not None
        ):
            token_url = token_url.replace(self._config.identityzone, tenant_subdomain)

        try:
            client = BackendApplicationClient(client_id=self._config.client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(
                token_url=token_url,
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                timeout=self._config.timeout,
            )
        except Exception as exc:
            raise AgentMemoryHttpError(f"Failed to obtain OAuth2 token: {exc}") from exc

        expires_in: int = token.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(
            seconds=expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS
        )

        existing = self._oauth_cache.get(tenant_subdomain)
        if existing is not None:
            existing[0].close()

        self._oauth_cache[tenant_subdomain] = (oauth, expires_at)

        logger.debug(
            "Obtained new Agent Memory OAuth2 token for tenant=%r (expires in %ds)",
            tenant_subdomain,
            expires_in,
        )
        return oauth

    def _request(
        self,
        method: str,
        path: str,
        tenant_subdomain: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an HTTP request using the appropriate session."""
        logger.debug("%s %s (tenant=%r)", method, path, tenant_subdomain)

        url = f"{self._config.base_url}{path}"
        if "params" in kwargs:
            raw_params: dict[str, Any] = kwargs.pop("params")
            if raw_params:
                url = f"{url}?{urlencode(raw_params, quote_via=quote)}"

        session = self._get_session(tenant_subdomain)
        headers = {"Content-Type": "application/json"}

        try:
            response = session.request(
                method, url, headers=headers, timeout=self._config.timeout, **kwargs
            )
        except Timeout as exc:
            raise AgentMemoryHttpError(f"Request timed out: {method} {path}") from exc
        except RequestException as exc:
            raise AgentMemoryHttpError(
                f"Request failed: {method} {path} — {exc}"
            ) from exc

        if response.status_code == 204 or not response.content:
            return {}

        if response.status_code == 404:
            raise AgentMemoryNotFoundError(
                f"Resource not found: {method} {path}",
                status_code=404,
                response_text=response.text,
            )

        if not response.ok:
            raise AgentMemoryHttpError(
                f"Agent Memory service request failed. "
                f"Method: {method}, Path: {path}, "
                f"Status: {response.status_code}, Response: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )

        return response.json()
