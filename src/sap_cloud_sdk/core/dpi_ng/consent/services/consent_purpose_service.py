"""Service client for consentPurposeExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentPurposeExternalServices"


class ConsentPurposeService:
    """Client for consentPurposeExternalServices - CRUD on purposes and their texts."""

    def __init__(self, client: _ODataClient) -> None:
        """Bind entity classes from the consentPurposeExternalServices endpoint."""
        logger.info("Invoked ConsentPurposeService.__init__")
        self._client = client
        (
            self.ConsentPurpose,
            self.ConsentPurposeText,
        ) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentPurposeService.__init__")

    # ------ consentPurposes ------

    def list_purposes(self, **query: Any) -> list[Any]:
        """Return all consent purposes, optionally filtered/paged via OData query kwargs."""
        logger.info("Invoked ConsentPurposeService.list_purposes")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentPurpose), query
        ).all()
        logger.info("Exiting ConsentPurposeService.list_purposes")
        return result

    def get_purpose(self, purpose_id: str) -> Any:
        """Return a single ConsentPurpose entity by its UUID."""
        logger.info("Invoked ConsentPurposeService.get_purpose")
        result = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        logger.info("Exiting ConsentPurposeService.get_purpose")
        return result

    def create_purpose(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentPurpose entity and return it."""
        logger.info("Invoked ConsentPurposeService.create_purpose")
        entity = self.ConsentPurpose()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.create_purpose")
        return entity

    def update_purpose(self, purpose_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ConsentPurpose by ID, apply field updates, and PATCH it."""
        logger.info("Invoked ConsentPurposeService.update_purpose")
        entity = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.update_purpose")
        return entity

    def delete_purpose(self, purpose_id: str) -> None:
        """Delete a ConsentPurpose by its UUID."""
        logger.info("Invoked ConsentPurposeService.delete_purpose")
        entity = self._client.query(_SVC, self.ConsentPurpose).get(purpose_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentPurposeService.delete_purpose")

    # ------ lifecycle actions ------

    def set_purpose_active(self, purpose_id: str) -> Any:
        """Activate a consent purpose and return the refreshed entity."""
        logger.info("Invoked ConsentPurposeService.set_purpose_active")
        self._client.call_action(
            _SVC, "consentPurposeSetConsentPurposeToActive", {"purposeId": purpose_id}
        )
        result = self.get_purpose(purpose_id)
        logger.info("Exiting ConsentPurposeService.set_purpose_active")
        return result

    def set_purpose_inactive(self, purpose_id: str) -> Any:
        """Deactivate a consent purpose and return the refreshed entity."""
        logger.info("Invoked ConsentPurposeService.set_purpose_inactive")
        self._client.call_action(
            _SVC, "consentPurposeSetConsentPurposeToInactive", {"purposeId": purpose_id}
        )
        result = self.get_purpose(purpose_id)
        logger.info("Exiting ConsentPurposeService.set_purpose_inactive")
        return result

    # ------ consentPurposeTexts ------

    def list_purpose_texts(self, **query: Any) -> list[Any]:
        """Return all purpose text records, optionally filtered/paged."""
        logger.info("Invoked ConsentPurposeService.list_purpose_texts")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentPurposeText), query
        ).all()
        logger.info("Exiting ConsentPurposeService.list_purpose_texts")
        return result

    def get_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str
    ) -> Any:
        """Return a single ConsentPurposeText by its composite key."""
        logger.info("Invoked ConsentPurposeService.get_purpose_text")
        result = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        logger.info("Exiting ConsentPurposeService.get_purpose_text")
        return result

    def create_purpose_text(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentPurposeText entity and return it."""
        logger.info("Invoked ConsentPurposeService.create_purpose_text")
        entity = self.ConsentPurposeText()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.create_purpose_text")
        return entity

    def update_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a ConsentPurposeText by composite key, apply updates, and PATCH it."""
        logger.info("Invoked ConsentPurposeService.update_purpose_text")
        entity = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentPurposeService.update_purpose_text")
        return entity

    def delete_purpose_text(
        self, purpose_id: str, type_code: str, language_code: str
    ) -> None:
        """Delete a ConsentPurposeText by its composite key."""
        logger.info("Invoked ConsentPurposeService.delete_purpose_text")
        entity = self._client.query(_SVC, self.ConsentPurposeText).get(
            purposeId=purpose_id, typeCode=type_code, languageCode=language_code
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentPurposeService.delete_purpose_text")
