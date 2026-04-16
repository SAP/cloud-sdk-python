"""HTTP transport implementation for cloud mode."""

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
)
from sap_cloud_sdk.auditlog._transport import Transport, AuditMessage
from sap_cloud_sdk.auditlog.config import AuditLogConfig
from sap_cloud_sdk.auditlog.exceptions import TransportError, AuthenticationError


class HttpTransport(Transport):
    """HTTP-based transport for cloud mode with OAuth2 authentication."""

    def __init__(self, config: AuditLogConfig):
        """Initialize HTTP transport with provided configuration.

        Args:
            config: AuditLogConfig with OAuth2 credentials and service URL
        """
        self.config = config

        token_url = f"{config.oauth_url.rstrip('/')}/oauth/token"

        client = BackendApplicationClient(client_id=config.client_id)
        self.oauth = OAuth2Session(client=client)

        try:
            _token = self.oauth.fetch_token(
                token_url=token_url,
                client_id=config.client_id,
                client_secret=config.client_secret,
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to obtain OAuth2 token: {e}")

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

            response = self.oauth.post(
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
