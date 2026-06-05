"""HTTP transport and OAuth utilities for SAP Print Service."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Optional, Protocol

import requests
from requests import Response
from requests.exceptions import RequestException
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.print.config import PrintConfig
from sap_cloud_sdk.print.exceptions import HttpError

logger = logging.getLogger(__name__)


class AbstractTokenProvider(Protocol):
    """Protocol for token providers — allows injection of mock providers in tests."""

    def get_token(self) -> str: ...
    def resolve_username(self) -> str: ...


class TokenProvider:
    """Provides OAuth2 access tokens via client credentials flow."""

    def __init__(self, config: PrintConfig) -> None:
        self._config = config
        client = BackendApplicationClient(client_id=config.client_id)
        self._session = OAuth2Session(client=client)
        self._cached_token: Optional[str] = None

    def get_token(self) -> str:
        """Return a valid bearer token for the Print Service.

        Returns:
            A non-empty OAuth2 access token string.

        Raises:
            HttpError: If the token response is missing an access_token or
                token acquisition fails.
        """

        try:
            token: Dict[str, Any] = self._session.fetch_token(
                token_url=self._config.token_url,
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                include_client_id=True,
            )
        except Exception as e:
            logger.error("failed to acquire token: %s", e)
            raise HttpError(f"failed to acquire token: {e}") from e
        access_token = token.get("access_token")
        if not access_token:
            raise HttpError("token response missing access_token")
        self._cached_token = str(access_token)
        return self._cached_token

    def resolve_username(self) -> str:
        """Resolve a username from the current access token claims.

        Returns the ``user_name`` JWT claim when present (interactive user
        flows), otherwise falls back to ``client_id`` (client-credentials /
        technical-user flows).
        """
        token = self._cached_token or self.get_token()
        try:
            payload_b64 = token.split(".")[1]
            # JWT base64 uses URL-safe alphabet without padding
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            return str(
                claims.get("user_name")
                or claims.get("client_id")
                or self._config.client_id
            )
        except Exception:
            logger.debug("could not decode JWT claims, falling back to client_id")
            return self._config.client_id


class PrintHttp:
    """HTTP client for SAP Print Service."""

    def __init__(
        self,
        config: PrintConfig,
        token_provider: AbstractTokenProvider,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._config = config
        self._token_provider = token_provider
        self._session = session or requests.Session()
        self._base_url = config.url.rstrip("/")

    def get_username(self) -> str:
        """Resolve the username from the current OAuth token (or fall back to client_id)."""
        return self._token_provider.resolve_username()

    def _auth_headers(self) -> Dict[str, str]:
        token = self._token_provider.get_token()
        return {"Authorization": f"Bearer {token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = self._auth_headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                files=files,
            )
        except RequestException as e:
            logger.error("request failed [%s %s]: %s", method, url, e)
            raise HttpError(f"request failed: {e}") from e

        if 200 <= resp.status_code < 300:
            return resp

        text: str = ""
        try:
            text = resp.text
        except Exception:
            text = "<failed to read response body>"

        raise HttpError(
            f"HTTP {resp.status_code} for {method} {url}",
            status_code=resp.status_code,
            response_text=text,
        )

    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        return self._request("GET", path, params=params, extra_headers=headers)

    def put(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        return self._request("PUT", path, json=json, extra_headers=headers)

    def post(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        return self._request(
            "POST", path, json=json, data=data, files=files, extra_headers=headers
        )
