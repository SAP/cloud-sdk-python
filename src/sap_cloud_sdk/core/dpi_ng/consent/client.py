"""OData v4 client backed by python-odata (https://pypi.org/project/python-odata/)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests
from odata import ODataService
from odata.flags import ODataServerFlags

from .config import ConsentSDKConfig
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ODataError,
    ValidationError,
)

if TYPE_CHECKING:
    from odata.query import Query

logger = logging.getLogger(__name__)

# Maps service name -> make_entities factory function
_ENTITY_FACTORIES: dict[str, Any] = {}


def _register_factories() -> None:
    """Populate _ENTITY_FACTORIES with one make_entities callable per service endpoint."""
    from .entities.consent import _make_entities as consent_entities
    from .entities.consent_configuration import _make_entities as config_entities
    from .entities.consent_purpose import _make_entities as purpose_entities
    from .entities.consent_retention import _make_entities as retention_entities
    from .entities.consent_template import _make_entities as template_entities

    _ENTITY_FACTORIES["consentServices"] = consent_entities
    _ENTITY_FACTORIES["consentPurposeExternalServices"] = purpose_entities
    _ENTITY_FACTORIES["consentTemplateExternalServices"] = template_entities
    _ENTITY_FACTORIES["consentRetentionExternalServices"] = retention_entities
    _ENTITY_FACTORIES["consentConfigurationExternalServices"] = config_entities


_register_factories()


class _ODataClient:
    """OData v4 client - one ODataService per SAP service endpoint, entity classes bound per service."""

    def __init__(self, config: ConsentSDKConfig) -> None:
        """Initialise the HTTP session and apply the configured auth strategy."""
        logger.info("Invoked ODataClient.__init__")
        self._config = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json;odata.metadata=minimal",
                "Content-Type": "application/json",
            }
        )
        self._session.verify = config.verify_ssl
        config.auth.apply(self._session)
        self._services: dict[str, ODataService] = {}
        self._server_flags = ODataServerFlags(
            provide_odata_type_annotation=False,
            skip_null_properties=True,
        )
        # Maps service_name -> dict of entity class name -> entity class
        self._entity_classes: dict[str, tuple] = {}
        logger.info("Exiting ODataClient.__init__")

    # ------------------------------------------------------------------
    # ODataService / entity class registry
    # ------------------------------------------------------------------

    def _get_service(self, service_name: str) -> ODataService:
        """Return (and lazily create) the ODataService for the given service endpoint."""
        logger.info("Invoked ODataClient._get_service")
        if service_name not in self._services:
            url = f"{self._config.base_url}{self._config.service_path}/{service_name}/"
            logger.debug("Creating new ODataService — url=%s", url)
            self._services[service_name] = ODataService(
                url,
                session=self._session,
                reflect_entities=False,
                server_flags=self._server_flags,
            )
        logger.info("Exiting ODataClient._get_service")
        return self._services[service_name]

    def get_entity_classes(self, service_name: str) -> tuple:
        """Return the tuple of entity classes bound to the given service endpoint.

        Classes are created once and cached; subsequent calls return the same objects.

        Args:
            service_name: OData service identifier (e.g. ``"consentServices"``).

        Returns:
            Tuple of python-odata entity classes in the order defined by the
            service's ``_make_entities`` factory.
        """
        logger.info("Invoked ODataClient.get_entity_classes")
        if service_name not in self._entity_classes:
            svc = self._get_service(service_name)
            factory = _ENTITY_FACTORIES[service_name]
            self._entity_classes[service_name] = factory(svc)
            logger.debug("Entity classes created for service_name=%s", service_name)
        logger.info("Exiting ODataClient.get_entity_classes")
        return self._entity_classes[service_name]

    # ------------------------------------------------------------------
    # Query / save / delete - python-odata ORM operations
    # ------------------------------------------------------------------

    def query(self, service_name: str, entity_cls: type) -> Query:
        """Return a Query builder for the given entity class.

        Args:
            service_name: OData service identifier (e.g. ``"consentServices"``).
            entity_cls: The python-odata entity class to query.

        Returns:
            A python-odata ``Query`` instance that can be further filtered,
            paged, or executed with ``.all()`` / ``.get()``.
        """
        logger.info("Invoked ODataClient.query")
        svc = self._get_service(service_name)
        result = svc.query(entity_cls)
        logger.info("Exiting ODataClient.query")
        return result

    def save(self, entity: Any) -> None:
        """Persist an entity: POST if new, PATCH dirty fields if already saved.

        Args:
            entity: A python-odata entity instance to create or update.
        """
        logger.info("Invoked ODataClient.save")
        entity.__odata_service__.save(entity)
        logger.info("Exiting ODataClient.save")

    def delete_entity(self, entity: Any) -> None:
        """Send a DELETE request for the given entity.

        Args:
            entity: A python-odata entity instance to delete.
        """
        logger.info("Invoked ODataClient.delete_entity")
        entity.__odata_service__.delete(entity)
        logger.info("Exiting ODataClient.delete_entity")

    # ------------------------------------------------------------------
    # Actions - raw POST (not modelled as python-odata Action descriptors)
    # ------------------------------------------------------------------

    def call_action(
        self,
        service: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """POST an OData action and return the parsed response body.

        Args:
            service: OData service identifier (e.g. ``"consentServices"``).
            path: Action name relative to the service root URL
                (e.g. ``"createConsentFromTemplate"``).
            body: JSON-serialisable request payload. Defaults to ``{}`` when omitted.
            params: Optional URL query parameters to append to the request.

        Returns:
            Parsed JSON response body as a dict, or ``None`` for HTTP 204 No Content.

        Raises:
            AuthenticationError: On HTTP 401.
            AuthorizationError: On HTTP 403.
            NotFoundError: On HTTP 404.
            ConflictError: On HTTP 409.
            ValidationError: On HTTP 400 or 422.
            ODataError: On any other 4xx or 5xx response.
        """
        logger.info("Invoked ODataClient.call_action")
        svc = self._get_service(service)
        url = f"{svc.url}{path}"
        logger.debug("Posting action — url=%s", url)
        resp = self._session.post(
            url, json=body or {}, params=params, timeout=self._config.timeout
        )
        self._raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            logger.info("Exiting ODataClient.call_action — 204 No Content")
            return None
        result = resp.json()
        logger.info("Exiting ODataClient.call_action")
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying requests.Session and release connection pool resources."""
        logger.info("Invoked ODataClient.close")
        self._session.close()
        logger.info("Exiting ODataClient.close")

    def __enter__(self) -> _ODataClient:
        """Support use as a context manager."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Close the session on context manager exit."""
        self.close()

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        """Translate 4xx/5xx HTTP responses into typed ``ConsentSDKError`` subclasses.

        Args:
            resp: The ``requests.Response`` to inspect.

        Raises:
            AuthenticationError: On HTTP 401.
            AuthorizationError: On HTTP 403.
            NotFoundError: On HTTP 404.
            ConflictError: On HTTP 409.
            ValidationError: On HTTP 400 or 422.
            ODataError: On any other 4xx or 5xx response.
        """
        status_code: int = resp.status_code  # ty: ignore[invalid-assignment]
        if status_code < 400:
            return
        try:
            body = resp.json()
            odata_error: dict[str, Any] = body.get("error", {})
            message: str = odata_error.get("message") or resp.text
            details: list[dict[str, Any]] = odata_error.get("details", [])
            if details:
                detail_messages = "; ".join(
                    f"{d['target']}: {d['message']}"
                    if d.get("target")
                    else d["message"]
                    for d in details
                    if d.get("message")
                )
                if detail_messages:
                    message = f"{message} - {detail_messages}"
        except Exception:
            odata_error = {}
            message = resp.text

        logger.error("HTTP error response — status=%d message=%s", status_code, message)
        match status_code:
            case 401:
                raise AuthenticationError(message, odata_error)
            case 403:
                raise AuthorizationError(message, odata_error)
            case 404:
                raise NotFoundError(message, odata_error)
            case 409:
                raise ConflictError(message, odata_error)
            case 400 | 422:
                raise ValidationError(message, odata_error)
            case _:
                raise ODataError(message, status_code, odata_error)
