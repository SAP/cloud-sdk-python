"""Transport layer abstraction and HTTP implementation for audit log messages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Union

from sap_cloud_sdk.core.protocol.http import HttpClient, HttpMethod, XsuaaAuthProvider
from sap_cloud_sdk.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
)
from sap_cloud_sdk.core.auditlog.config import AuditLogConfig
from sap_cloud_sdk.core.auditlog.exceptions import TransportError

AuditMessage = Union[
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
]

_PATH_PREFIX = "/audit-log/oauth2/v2"


class Transport(ABC):
    """Abstract base class for audit log transport implementations."""

    @abstractmethod
    def send(self, event: AuditMessage) -> None:
        """Send an audit event.

        Args:
            event: The audit event to send.

        Raises:
            TransportError: If the transport operation fails.
        """
        pass

    def close(self) -> None:
        """Close the transport and release resources.

        Default implementation is a no-op. Subclasses may override
        to perform cleanup (e.g., closing HTTP sessions).
        """
        pass


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

        auth_provider = XsuaaAuthProvider(self._config_factory)
        self._http = HttpClient(self.config.service_url, auth_provider)

    def send(self, event: AuditMessage) -> None:
        """Send audit event via HTTP.

        Args:
            event: The audit event to send.

        Raises:
            TransportError: If the HTTP request fails.
        """
        try:
            endpoint = self._get_endpoint(event)
            response = self._http.request(
                HttpMethod.POST,
                f"{_PATH_PREFIX}{endpoint}",
                json=event.to_dict(),
                headers={"Content-Type": "application/json"},
            )

            if not (200 <= response.status_code < 300):
                url = f"{self.config.service_url.rstrip('/')}{_PATH_PREFIX}{endpoint}"
                raise TransportError(
                    f"POST request to {url} completed with status {response.status_code}: {response.text}"
                )

        except TransportError:
            raise
        except Exception as e:
            raise TransportError(f"Unexpected error sending audit event: {e}")

    def _get_endpoint(self, event: AuditMessage) -> str:
        """Get the appropriate API endpoint for the event type."""
        if isinstance(event, SecurityEvent):
            return "/security-events"
        elif isinstance(event, DataAccessEvent):
            return "/data-accesses"
        elif isinstance(event, (DataModificationEvent, DataDeletionEvent)):
            return "/data-modifications"
        elif isinstance(event, (ConfigurationChangeEvent, ConfigurationDeletionEvent)):
            return "/configuration-changes"
        else:
            raise TransportError(f"Unknown event type: {type(event)}")
