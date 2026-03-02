"""Simplified HTTP and OAuth utilities for Destination Service.

Initial version: no retries and no explicit timeouts.
- TokenProvider: OAuth2 client-credentials (no caching).
- DestinationHttp: Single-shot HTTP requests, adds Authorization header.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from enum import Enum

import requests
from requests import Response
from requests.exceptions import RequestException
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from cloud_sdk_python.destination.config import DestinationConfig
from cloud_sdk_python.destination.exceptions import HttpError

# API version constants
API_V1 = "v1"
API_V2 = "v2"


class HttpMethod(Enum):
    """HTTP method enumeration for request verb selection."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class TokenProvider:
    """Provides OAuth2 access tokens with in-memory caching and proactive refresh."""

    def __init__(self, config: DestinationConfig) -> None:
        self._config = config

        client = BackendApplicationClient(client_id=config.client_id)
        self._session = OAuth2Session(client=client)



    def get_token(self, tenant_subdomain: Optional[str] = None) -> str:
        """Return a valid bearer token for the Destination Service.

        If tenant_subdomain is provided,
        a subscriber token URL is derived by replacing the provider identity zone segment
        in the base token URL with the tenant_subdomain. Otherwise the provider token URL is used.

        Args:
            tenant_subdomain: Optional subscriber tenant subdomain. When provided, the token URL is adapted
                for subscriber context.

        Returns:
            A non-empty OAuth2 access token string.

        Raises:
            HttpError: If the token response is missing an access_token or the underlying token
                acquisition fails.
        """
        token_url = self._config.token_url
        identityzone = self._config.identityzone

        if tenant_subdomain:
            try:
                token_url = token_url.replace(str(identityzone), tenant_subdomain)
            except Exception:
                # Fallback to base token_url if replacement fails
                token_url = self._config.token_url

        token: Dict[str, Any] = self._session.fetch_token(
            token_url=token_url,
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            include_client_id=True,
        )
        access_token = token.get("access_token")
        if not access_token:
            raise HttpError("token response missing access_token")
        return str(access_token)


class DestinationHttp:
    """HTTP client wrapper for Destination Service (single-shot, no retries/timeout)."""

    def __init__(
        self,
        config: DestinationConfig,
        token_provider: TokenProvider,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialize DestinationHttp.

        Args:
            config: Destination configuration with base URL for the service.
            token_provider: Provider that supplies OAuth2 access tokens.
            session: Optional requests.Session to reuse; if None, a new session is created.
        """
        self._config = config
        self._token_provider = token_provider
        self._session = session or requests.Session()

        # Construct base URL: <config.url>/destination-configuration
        base = self._config.url.rstrip("/")
        self._base_url = f"{base}/destination-configuration"

    @property
    def base_url(self) -> str:
        return self._base_url

    def _auth_headers(self, tenant_subdomain: Optional[str] = None) -> Dict[str, str]:
        token = self._token_provider.get_token(tenant_subdomain)
        return {"Authorization": f"Bearer {token}"}

    def _request(
        self,
        method: HttpMethod | str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> Response:
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        headers.update(self._auth_headers(tenant_subdomain))
        if extra_headers:
            headers.update(extra_headers)

        # Normalize method to string
        method_str = method.value if isinstance(method, HttpMethod) else str(method).upper()

        try:
            resp = self._session.request(
                method=method_str,
                url=url,
                headers=headers,
                params=params,
                json=json,
            )
        except RequestException as e:
            raise HttpError(f"request failed: {e}")

        if 200 <= resp.status_code < 300:
            return resp

        text: str = ""
        try:
            text = resp.text
        except Exception:
            text = "<failed to read response body>"

        raise HttpError(
            f"HTTP {resp.status_code} for {method_str} {url}",
            status_code=resp.status_code,
            response_text=text,
        )

    # Public helpers for REST verbs

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, tenant_subdomain: Optional[str] = None) -> Response:
        """Send a GET request.

        Args:
            path: Relative API path under destination-configuration/v1.
            params: Optional query parameters.
            headers: Optional additional request headers.
            tenant_subdomain: Optional subscriber tenant subdomain for token acquisition.

        Returns:
            requests.Response if the status code is 2xx.

        Raises:
            HttpError: If the request fails or returns a non-2xx status.
        """
        return self._request(HttpMethod.GET, path, params=params, extra_headers=headers, tenant_subdomain=tenant_subdomain)

    def post(self, path: str, *, body: Any, headers: Optional[Dict[str, str]] = None, tenant_subdomain: Optional[str] = None) -> Response:
        """Send a POST request.

        Args:
            path: Relative API path under destination-configuration/v1.
            body: JSON-serializable request body.
            headers: Optional additional request headers.
            tenant_subdomain: Optional subscriber tenant subdomain for token acquisition.

        Returns:
            requests.Response if the status code is 2xx.

        Raises:
            HttpError: If the request fails or returns a non-2xx status.
        """
        return self._request(HttpMethod.POST, path, json=body, extra_headers=headers, tenant_subdomain=tenant_subdomain)

    def put(self, path: str, *, body: Any, headers: Optional[Dict[str, str]] = None, tenant_subdomain: Optional[str] = None) -> Response:
        """Send a PUT request.

        Args:
            path: Relative API path under destination-configuration/v1.
            body: JSON-serializable request body.
            headers: Optional additional request headers.
            tenant_subdomain: Optional subscriber tenant subdomain for token acquisition.

        Returns:
            requests.Response if the status code is 2xx.

        Raises:
            HttpError: If the request fails or returns a non-2xx status.
        """
        return self._request(HttpMethod.PUT, path, json=body, extra_headers=headers, tenant_subdomain=tenant_subdomain)

    def delete(self, path: str, *, headers: Optional[Dict[str, str]] = None, tenant_subdomain: Optional[str] = None) -> Response:
        """Send a DELETE request.

        Args:
            path: Relative API path under destination-configuration/v1.
            headers: Optional additional request headers.
            tenant_subdomain: Optional subscriber tenant subdomain for token acquisition.

        Returns:
            requests.Response if the status code is 2xx.

        Raises:
            HttpError: If the request fails or returns a non-2xx status.
        """
        return self._request(HttpMethod.DELETE, path, extra_headers=headers, tenant_subdomain=tenant_subdomain)
