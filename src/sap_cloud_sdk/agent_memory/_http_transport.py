"""HTTP transport for the Agent Memory service.

Handles OAuth2 ``client_credentials`` token acquisition with lazy,
expiry-aware caching. If ``token_url`` is not configured, requests are
sent unauthenticated — expected for local development environments.
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

    Manages OAuth2 token lifecycle (lazy acquire + expiry-aware caching) and
    attaches the ``Authorization`` header to every request automatically via
    ``OAuth2Session``. In no-auth mode (no ``token_url``), a plain
    ``requests.Session`` is used instead.

    Args:
        config: Service configuration.
    """

    def __init__(self, config: AgentMemoryConfig) -> None:
        self._config = config
        self._oauth: Optional[OAuth2Session] = None
        self._plain_session: Optional[requests.Session] = None
        self._token_expires_at: Optional[datetime] = None

    def close(self) -> None:
        """Close the underlying HTTP session(s) and release resources."""
        if self._oauth is not None:
            self._oauth.close()
            self._oauth = None
        if self._plain_session is not None:
            self._plain_session.close()
            self._plain_session = None

    # ── Public HTTP methods ────────────────────────────────────────────────────

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Perform a GET request.

        Args:
            path: API path (appended to ``base_url``).
            params: Optional query parameters.

        Returns:
            Parsed JSON response body.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request("GET", path, params=params)

    def post(self, path: str, json: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Perform a POST request.

        Args:
            path: API path (appended to ``base_url``).
            json: Optional request body dict (serialised to JSON).

        Returns:
            Parsed JSON response body. Returns an empty dict for 204 responses.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Perform a PATCH request.

        Args:
            path: API path (appended to ``base_url``).
            json: Optional request body dict (serialised to JSON).

        Returns:
            Parsed JSON response body. Returns an empty dict for 204 responses.

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> None:
        """Perform a DELETE request.

        Args:
            path: API path (appended to ``base_url``).

        Raises:
            AgentMemoryHttpError: On HTTP errors or network failures.
            AgentMemoryNotFoundError: If the server returns 404.
        """
        self._request("DELETE", path)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        """Return a session ready to make requests.

        In no-auth mode, returns a plain ``requests.Session`` (created once).
        In OAuth2 mode, returns an ``OAuth2Session`` with a valid token,
        fetching or refreshing the token if needed.
        """
        if not self._config.token_url:
            if self._plain_session is None:
                self._plain_session = requests.Session()
            return self._plain_session

        if (
            self._oauth is not None
            and self._token_expires_at is not None
            and datetime.now() < self._token_expires_at
        ):
            return self._oauth

        self._oauth = self._fetch_token()
        return self._oauth

    def _fetch_token(self) -> OAuth2Session:
        """Acquire a new OAuth2 ``client_credentials`` token.

        Returns:
            An ``OAuth2Session`` with a valid token attached.

        Raises:
            AgentMemoryHttpError: If the token endpoint returns an error or is unreachable.
        """
        try:
            client = BackendApplicationClient(client_id=self._config.client_id)
            oauth = OAuth2Session(client=client)
            token = oauth.fetch_token(
                token_url=self._config.token_url,
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                timeout=self._config.timeout,
            )
        except Exception as exc:
            raise AgentMemoryHttpError(f"Failed to obtain OAuth2 token: {exc}") from exc

        expires_in: int = token.get("expires_in", 3600)
        self._token_expires_at = datetime.now() + timedelta(
            seconds=expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS
        )

        if self._oauth is not None:
            self._oauth.close()

        logger.debug(
            "Obtained new Agent Memory OAuth2 token (expires in %ds)", expires_in
        )
        return oauth

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute an HTTP request using the appropriate session."""
        logger.debug("%s %s", method, path)

        url = f"{self._config.base_url}{path}"
        if "params" in kwargs:
            raw_params: dict[str, Any] = kwargs.pop("params")
            if raw_params:
                url = f"{url}?{urlencode(raw_params, quote_via=quote)}"

        session = self._get_session()
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
