"""Service client for consentPurposeExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentPurposeExternalServices"


class ConsentPurposeService:
    """Client for consentPurposeExternalServices - CRUD on purposes and their texts."""

    def __init__(
        self,
        client: _ODataClient,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Bind entity classes from the consentPurposeExternalServices endpoint."""
        logger.info("Invoked ConsentPurposeService.__init__")
        self._client = client
        self._telemetry_source = _telemetry_source
        (
            self.ConsentPurpose,
            self.ConsentPurposeText,
        ) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentPurposeService.__init__")

    # ------ consentPurposes ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_PURPOSES)
    def list_purposes(self, **query: Any) -> list[Any]:
        """Return all consent purpose records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of ConsentPurpose objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.list_purposes")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentPurpose), query
        ).all()
        logger.info("Exiting ConsentPurposeService.list_purposes")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_PURPOSE)
    def get_purpose(self, purpose_id: str) -> Any:
        """Return a single ConsentPurpose entity by its UUID.

        Args:
            purpose_id: UUID of the ConsentPurpose to retrieve.

        Returns:
            The matching ConsentPurpose object.

        Raises:
            NotFoundError: If no ConsentPurpose with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.get_purpose")
        result = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        logger.info("Exiting ConsentPurposeService.get_purpose")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_PURPOSE)
    def create_purpose(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentPurpose entity and return it.

        Args:
            body: Dictionary of field names and values for the new ConsentPurpose.

        Returns:
            The newly created ConsentPurpose object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.create_purpose")
        entity = self.ConsentPurpose()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.create_purpose")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_PURPOSE)
    def update_purpose(self, purpose_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ConsentPurpose by ID, apply field updates, and PATCH it to the service.

        Args:
            purpose_id: UUID of the ConsentPurpose to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated ConsentPurpose object.

        Raises:
            NotFoundError: If no ConsentPurpose with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.update_purpose")
        entity = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.update_purpose")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_PURPOSE)
    def delete_purpose(self, purpose_id: str) -> None:
        """Delete a ConsentPurpose entity by its UUID.

        Args:
            purpose_id: UUID of the ConsentPurpose to delete.

        Raises:
            NotFoundError: If no ConsentPurpose with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.delete_purpose")
        entity = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentPurposeService.delete_purpose")

    # ------ lifecycle actions ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_PURPOSE_ACTIVE)
    def set_purpose_active(self, purpose_id: str) -> Any:
        """Activate a consent purpose and return the refreshed entity.

        Args:
            purpose_id: UUID of the ConsentPurpose to activate.

        Returns:
            The refreshed ConsentPurpose object with its status set to active.

        Raises:
            NotFoundError: If no ConsentPurpose with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.set_purpose_active")
        self._client.call_action(
            _SVC, "consentPurposeSetConsentPurposeToActive", {"purposeId": purpose_id}
        )
        result = self.get_purpose(purpose_id)
        logger.info("Exiting ConsentPurposeService.set_purpose_active")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_PURPOSE_INACTIVE)
    def set_purpose_inactive(self, purpose_id: str) -> Any:
        """Deactivate a consent purpose and return the refreshed entity.

        Args:
            purpose_id: UUID of the ConsentPurpose to deactivate.

        Returns:
            The refreshed ConsentPurpose object with its status set to inactive.

        Raises:
            NotFoundError: If no ConsentPurpose with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.set_purpose_inactive")
        self._client.call_action(
            _SVC, "consentPurposeSetConsentPurposeToInactive", {"purposeId": purpose_id}
        )
        result = self.get_purpose(purpose_id)
        logger.info("Exiting ConsentPurposeService.set_purpose_inactive")
        return result

    # ------ consentPurposeTexts ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_PURPOSE_TEXTS)
    def list_purpose_texts(self, **query: Any) -> list[Any]:
        """Return all consent purpose text records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of ConsentPurposeText objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.list_purpose_texts")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentPurposeText), query
        ).all()
        logger.info("Exiting ConsentPurposeService.list_purpose_texts")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_PURPOSE_TEXT)
    def get_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str
    ) -> Any:
        """Return a single ConsentPurposeText entity by its composite key.

        Args:
            purpose_id: UUID of the parent ConsentPurpose.
            type_code: Type code identifying the text category.
            language_code: BCP-47 language code of the text entry.

        Returns:
            The matching ConsentPurposeText object.

        Raises:
            NotFoundError: If no ConsentPurposeText for the given composite key exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.get_purpose_text")
        result = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        logger.info("Exiting ConsentPurposeService.get_purpose_text")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_PURPOSE_TEXT)
    def create_purpose_text(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentPurposeText entity and return it.

        Args:
            body: Dictionary of field names and values for the new ConsentPurposeText.
                Must include ``purposeId``, ``typeCode``, and ``languageCode`` as the composite key.

        Returns:
            The newly created ConsentPurposeText object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.create_purpose_text")
        entity = self.ConsentPurposeText()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.create_purpose_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_PURPOSE_TEXT)
    def update_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a ConsentPurposeText by composite key, apply field updates, and PATCH it to the service.

        Args:
            purpose_id: UUID of the parent ConsentPurpose.
            type_code: Type code identifying the text category.
            language_code: BCP-47 language code of the text entry.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated ConsentPurposeText object.

        Raises:
            NotFoundError: If no ConsentPurposeText for the given composite key exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.update_purpose_text")
        entity = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.update_purpose_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_PURPOSE_TEXT)
    def delete_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str
    ) -> None:
        """Delete a ConsentPurposeText entity by its composite key.

        Args:
            purpose_id: UUID of the parent ConsentPurpose.
            type_code: Type code identifying the text category.
            language_code: BCP-47 language code of the text entry to delete.

        Raises:
            NotFoundError: If no ConsentPurposeText for the given composite key exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentPurposeService.delete_purpose_text")
        entity = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentPurposeService.delete_purpose_text")
