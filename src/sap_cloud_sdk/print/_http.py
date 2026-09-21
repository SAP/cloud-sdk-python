"""OAuth token provider for SAP Print Service."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Callable, Dict, Optional

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.print.config import PrintConfig
from sap_cloud_sdk.print.exceptions import HttpError

logger = logging.getLogger(__name__)


class TokenProvider:
    """Provides OAuth2 access tokens via client credentials flow.

    Accepts either a fixed :class:`PrintConfig` or a config factory (any callable
    returning ``PrintConfig`` with an optional ``has_changed() -> bool`` method).
    When a factory is supplied, credentials are re-read on every token fetch and
    the factory's ``has_changed()`` method is checked before serving a cached token
    so that rotated secrets are picked up proactively.
    """

    def __init__(self, config: PrintConfig | Callable[[], PrintConfig]) -> None:
        if callable(config) and not isinstance(config, PrintConfig):
            self._config_factory: Callable[[], PrintConfig] = config
            self._config = config()
        else:
            self._config_factory = lambda: config  # type: ignore[arg-type]
            self._config = config  # type: ignore[assignment]
        client = BackendApplicationClient(client_id=self._config.client_id)
        self._session = OAuth2Session(client=client)
        self._cached_token: Optional[str] = None

    def _refresh_if_rotated(self) -> None:
        has_changed = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            self._config = self._config_factory()
            self._cached_token = None
            client = BackendApplicationClient(client_id=self._config.client_id)
            self._session = OAuth2Session(client=client)

    def get_token(self) -> str:
        """Return a valid bearer token for the Print Service.

        Returns:
            A non-empty OAuth2 access token string.

        Raises:
            HttpError: If the token response is missing an access_token or
                token acquisition fails.
        """
        self._refresh_if_rotated()

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
