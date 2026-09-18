"""HTTP transport implementation for cloud mode."""

from typing import Callable, Optional

import requests

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
)
from sap_cloud_sdk.core.auditlog._transport import Transport, AuditMessage
from sap_cloud_sdk.core.auditlog.config import AuditLogConfig
from sap_cloud_sdk.core.auditlog.exceptions import TransportError, AuthenticationError


class HttpTransport(Transport):
    """HTTP-based transport for cloud mode with OAuth2 authentication.

    Accepts either a fixed :class:`AuditLogConfig` or a config factory (any callable
    returning ``AuditLogConfig`` with an optional ``has_changed() -> bool`` method).
    When a factory is supplied, credentials are re-read on every token refresh and
    the factory's ``has_changed()`` method is checked proactively before each request
    so that rotated secrets are picked up automatically.
    """

    def __init__(self, config: AuditLogConfig | Callable[[], AuditLogConfig]):
        """Initialize HTTP transport with provided configuration.

        Args:
            config: AuditLogConfig (or a factory returning one) with OAuth2 credentials
                and service URL.
        """
        if callable(config) and not isinstance(config, AuditLogConfig):
            self._config_factory: Callable[[], AuditLogConfig] = config
            self.config = config()
        else:
            self._config_factory = lambda: config  # type: ignore[arg-type]
            self.config = config  # type: ignore[assignment]
        self.oauth: Optional[OAuth2Session] = None

    def _ensure_session(self) -> OAuth2Session:
        """Return a valid OAuth2 session, refreshing credentials if the binding changed."""
        has_changed = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            self.config = self._config_factory()
            self.oauth = None

        if self.oauth is None:
            token_url = f"{self.config.oauth_url.rstrip('/')}/oauth/token"
            client = BackendApplicationClient(client_id=self.config.client_id)
            oauth = OAuth2Session(client=client)
            try:
                oauth.fetch_token(
                    token_url=token_url,
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                )
            except Exception as e:
                raise AuthenticationError(f"Failed to obtain OAuth2 token: {e}")
            self.oauth = oauth

        return self.oauth

    def send(self, event: AuditMessage) -> None:
        """Send audit event via HTTP.

        Args:
            event: The audit event to send.

        Raises:
            TransportError: If the HTTP request fails.
        """
        try:
            event_dict = event.to_dict()

            endpoint = self._get_endpoint(event)
            path_prefix = "/audit-log/oauth2/v2"
            url = f"{self.config.service_url.rstrip('/')}{path_prefix}{endpoint}"

            oauth = self._ensure_session()
            response = oauth.post(
                url,
                json=event_dict,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if not (200 <= response.status_code < 300):
                raise TransportError(
                    f"POST request to {url} completed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            raise TransportError(f"Network error: {e}")
        except Exception as e:
            raise TransportError(f"Unexpected error sending audit event: {e}")

    def _get_endpoint(self, event: AuditMessage) -> str:
        """Get the appropriate API endpoint for the event type."""
        if isinstance(event, SecurityEvent):
            return "/security-events"
        elif isinstance(event, DataAccessEvent):
            return "/data-accesses"
        elif isinstance(event, (DataModificationEvent, DataDeletionEvent)):
            # DataDeletionEvent maps to same endpoint as DataModificationEvent
            return "/data-modifications"
        elif isinstance(event, (ConfigurationChangeEvent, ConfigurationDeletionEvent)):
            # ConfigurationDeletionEvent maps to same endpoint as ConfigurationChangeEvent
            return "/configuration-changes"
        else:
            raise TransportError(f"Unknown event type: {type(event)}")
