"""Authentication strategy implementations for the Consent SDK.

Each provider implements AuthProvider.apply(), which configures the
requests.Session passed to it to inject the chosen auth mechanism.

Supported strategies:
  - BearerTokenAuth          - static bearer token (e.g. already-fetched XSUAA token)
  - ClientCredentialsAuth    - OAuth2 client_credentials flow with automatic token refresh
  - ClientCertificateAuth    - mTLS with client certificate + private key
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import requests
import requests.auth

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Abstract base for all authentication strategies.

    Subclasses configure a ``requests.Session`` to inject their chosen
    mechanism (headers, cert, custom auth flow, etc.).
    Adding a new auth type means subclassing this; nothing else changes.
    """

    @abstractmethod
    def apply(self, session: requests.Session) -> None:
        """Configure the requests.Session to inject authentication."""


class BearerTokenAuth(AuthProvider):
    """Static bearer token - use when the caller manages token lifecycle externally."""

    def __init__(self, token: str) -> None:
        """Store the bearer token.

        Args:
            token: A valid bearer token string (e.g. an already-fetched XSUAA access token).

        Raises:
            ValueError: If *token* is an empty string.
        """
        logger.info("Invoked BearerTokenAuth.__init__")
        if not token:
            logger.error("token is empty")
            raise ValueError("token must not be empty")
        self._token = token
        logger.info("Exiting BearerTokenAuth.__init__")

    def apply(self, session: requests.Session) -> None:
        """Set the ``Authorization: Bearer <token>`` header on the session.

        Args:
            session: The ``requests.Session`` to configure.
        """
        logger.info("Invoked BearerTokenAuth.apply")
        session.headers["Authorization"] = f"Bearer {self._token}"
        logger.info("Exiting BearerTokenAuth.apply")


class ClientCredentialsAuth(AuthProvider):
    """OAuth2 client_credentials flow with automatic token refresh.

    Fetches a bearer token from ``token_url`` using ``client_id`` / ``client_secret``
    and refreshes it transparently 60 seconds before it expires.
    """

    def __init__(self, token_url: str, client_id: str, client_secret: str) -> None:
        """Store OAuth2 credentials for lazy token fetching.

        Args:
            token_url: Full URL of the OAuth2 token endpoint
                (e.g. ``https://<subdomain>.authentication.eu10.hana.ondemand.com/oauth/token``).
            client_id: OAuth2 client identifier.
            client_secret: OAuth2 client secret.

        Raises:
            ValueError: If any of *token_url*, *client_id*, or *client_secret* is empty.
        """
        logger.info("Invoked ClientCredentialsAuth.__init__")
        if not token_url or not client_id or not client_secret:
            logger.error("token_url, client_id, or client_secret is empty")
            raise ValueError("token_url, client_id, and client_secret are all required")
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        logger.info("Exiting ClientCredentialsAuth.__init__")

    def apply(self, session: requests.Session) -> None:
        """Attach the OAuth2 flow handler to the session.

        Tokens are fetched on the first request and refreshed automatically
        60 seconds before expiry.

        Args:
            session: The ``requests.Session`` to configure.
        """
        logger.info("Invoked ClientCredentialsAuth.apply")
        session.auth = _OAuth2Flow(
            self._token_url, self._client_id, self._client_secret
        )
        logger.info("Exiting ClientCredentialsAuth.apply")


class ClientCertificateAuth(AuthProvider):
    """Mutual TLS (mTLS) authentication using a client certificate and private key.

    Args:
        cert_file: Path to the client certificate PEM file.
        key_file: Path to the client private key PEM file.
        ca_file: Path to the CA certificate PEM file for server verification.
                 When omitted, the system CA bundle is used.
    """

    def __init__(
        self,
        cert_file: str,
        key_file: str,
        ca_file: str | None = None,
    ) -> None:
        """Store mTLS file paths.

        Args:
            cert_file: Path to the PEM-encoded client certificate file.
            key_file: Path to the PEM-encoded client private key file.
            ca_file: Path to a PEM-encoded CA certificate file for server
                verification. When omitted the system CA bundle is used.

        Raises:
            ValueError: If *cert_file* or *key_file* is empty.
        """
        logger.info("Invoked ClientCertificateAuth.__init__")
        if not cert_file or not key_file:
            logger.error("cert_file or key_file is empty")
            raise ValueError("cert_file and key_file are required")
        self._cert_file = cert_file
        self._key_file = key_file
        self._ca_file = ca_file
        logger.info("Exiting ClientCertificateAuth.__init__")

    def apply(self, session: requests.Session) -> None:
        """Configure the session with the client cert/key pair and optional CA bundle.

        Args:
            session: The ``requests.Session`` to configure.
        """
        logger.info("Invoked ClientCertificateAuth.apply")
        session.cert = (self._cert_file, self._key_file)
        if self._ca_file:
            session.verify = self._ca_file  # ty: ignore[invalid-assignment]
            logger.debug("Custom CA bundle applied — ca_file=%s", self._ca_file)
        logger.info("Exiting ClientCertificateAuth.apply")


# ------------------------------------------------------------------
# Internal OAuth2 flow - not part of the public API
# ------------------------------------------------------------------


class _OAuth2Flow(requests.auth.AuthBase):
    """requests.auth.AuthBase implementation that handles token fetch and refresh."""

    # 60-second buffer before actual expiry to avoid clock-skew races
    _EXPIRY_BUFFER = 60.0

    def __init__(self, token_url: str, client_id: str, client_secret: str) -> None:
        """Initialise with OAuth2 endpoint and credentials; token is fetched lazily."""
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Inject a valid bearer token, refreshing it if expired or not yet fetched."""
        if self._is_expired():
            logger.debug("Token expired or absent — fetching new token")
            self._fetch_token()
        r.headers["Authorization"] = f"Bearer {self._access_token}"  # ty: ignore[invalid-assignment]
        return r

    def _is_expired(self) -> bool:
        """Return True if no token has been fetched or the expiry buffer has been reached."""
        return self._access_token is None or time.monotonic() >= self._expires_at

    def _fetch_token(self) -> None:
        """POST to the token URL and store the new access token and its expiry time."""
        logger.info("Invoked _OAuth2Flow._fetch_token")
        try:
            resp = requests.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            self._access_token = payload["access_token"]
            expires_in: float = float(payload.get("expires_in", 3600))
            self._expires_at = time.monotonic() + expires_in - self._EXPIRY_BUFFER
            logger.debug("Token acquired — expires_in=%.0fs", expires_in)
        except Exception:
            logger.exception("Failed to fetch access token from %s", self._token_url)
            raise
        logger.info("Exiting _OAuth2Flow._fetch_token")
