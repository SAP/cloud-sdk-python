"""Service client for consentTemplateExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentTemplateExternalServices"


class ConsentTemplateService:
    """Client for consentTemplateExternalServices - CRUD on templates and related entities."""

    def __init__(
        self,
        client: _ODataClient,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Bind entity classes from the consentTemplateExternalServices endpoint."""
        logger.info("Invoked ConsentTemplateService.__init__")
        self._client = client
        self._telemetry_source = _telemetry_source
        (
            self.ConsentTemplate,
            self.ConsentTemplateText,
            self.TemplateThirdPartyPersData,
        ) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentTemplateService.__init__")

    # ------ consentTemplates ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_TEMPLATES)
    def list_templates(self, **query: Any) -> list[Any]:
        """Return all consent templates, optionally filtered/paged via OData query kwargs."""
        logger.info("Invoked ConsentTemplateService.list_templates")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentTemplate), query
        ).all()
        logger.info("Exiting ConsentTemplateService.list_templates")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_TEMPLATE)
    def get_template(self, template_id: str) -> Any:
        """Return a single ConsentTemplate entity by its UUID."""
        logger.info("Invoked ConsentTemplateService.get_template")
        result = self._client.query(_SVC, self.ConsentTemplate).get(template_id)
        logger.info("Exiting ConsentTemplateService.get_template")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_TEMPLATE)
    def create_template(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentTemplate entity and return it."""
        logger.info("Invoked ConsentTemplateService.create_template")
        entity = self.ConsentTemplate()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.create_template")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_TEMPLATE)
    def update_template(self, template_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ConsentTemplate by ID, apply field updates, and PATCH it."""
        logger.info("Invoked ConsentTemplateService.update_template")
        entity = self._client.query(_SVC, self.ConsentTemplate).get(template_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.update_template")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_TEMPLATE)
    def delete_template(self, template_id: str) -> None:
        """Delete a ConsentTemplate by its UUID."""
        logger.info("Invoked ConsentTemplateService.delete_template")
        entity = self._client.query(_SVC, self.ConsentTemplate).get(template_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentTemplateService.delete_template")

    # ------ lifecycle actions ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_TEMPLATE_ACTIVE)
    def set_template_active(self, template_id: str) -> Any:
        """Activate a consent template and return the refreshed entity."""
        logger.info("Invoked ConsentTemplateService.set_template_active")
        self._client.call_action(
            _SVC,
            "consentTemplateSetConsentTemplateToActive",
            {"templateId": template_id},
        )
        result = self.get_template(template_id)
        logger.info("Exiting ConsentTemplateService.set_template_active")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_TEMPLATE_INACTIVE)
    def set_template_inactive(self, template_id: str) -> Any:
        """Deactivate a consent template and return the refreshed entity."""
        logger.info("Invoked ConsentTemplateService.set_template_inactive")
        self._client.call_action(
            _SVC,
            "consentTemplateSetConsentTemplateToInactive",
            {"templateId": template_id},
        )
        result = self.get_template(template_id)
        logger.info("Exiting ConsentTemplateService.set_template_inactive")
        return result

    # ------ consentTemplateTexts ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_TEMPLATE_TEXTS)
    def list_template_texts(self, **query: Any) -> list[Any]:
        """Return all template text records, optionally filtered/paged."""
        logger.info("Invoked ConsentTemplateService.list_template_texts")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentTemplateText), query
        ).all()
        logger.info("Exiting ConsentTemplateService.list_template_texts")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_TEMPLATE_TEXT)
    def get_template_text(
        self, template_id: str, type_code: str, language_code: str
    ) -> Any:
        """Return a single ConsentTemplateText by its composite key."""
        logger.info("Invoked ConsentTemplateService.get_template_text")
        result = self._client.query(_SVC, self.ConsentTemplateText).get(
            templateId=template_id, typeCode=type_code, languageCode=language_code
        )
        logger.info("Exiting ConsentTemplateService.get_template_text")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_TEMPLATE_TEXT)
    def create_template_text(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentTemplateText entity and return it."""
        logger.info("Invoked ConsentTemplateService.create_template_text")
        entity = self.ConsentTemplateText()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.create_template_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_TEMPLATE_TEXT)
    def update_template_text(
        self, template_id: str, type_code: str, language_code: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a ConsentTemplateText by composite key, apply updates, and PATCH it."""
        logger.info("Invoked ConsentTemplateService.update_template_text")
        entity = self._client.query(_SVC, self.ConsentTemplateText).get(
            templateId=template_id, typeCode=type_code, languageCode=language_code
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.update_template_text")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_TEMPLATE_TEXT)
    def delete_template_text(
        self, template_id: str, type_code: str, language_code: str
    ) -> None:
        """Delete a ConsentTemplateText by its composite key."""
        logger.info("Invoked ConsentTemplateService.delete_template_text")
        entity = self._client.query(_SVC, self.ConsentTemplateText).get(
            templateId=template_id, typeCode=type_code, languageCode=language_code
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentTemplateService.delete_template_text")

    # ------ templateThirdPartyPersDatas ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_THIRD_PARTY_PERS_DATA)
    def list_third_party_pers_data(self, **query: Any) -> list[Any]:
        """Return all template third-party personal data records."""
        logger.info("Invoked ConsentTemplateService.list_third_party_pers_data")
        result = _apply_query(
            self._client.query(_SVC, self.TemplateThirdPartyPersData), query
        ).all()
        logger.info("Exiting ConsentTemplateService.list_third_party_pers_data")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_THIRD_PARTY_PERS_DATA)
    def get_third_party_pers_data(self, template_id: str, third_party_id: str) -> Any:
        """Return a single TemplateThirdPartyPersData by its composite key."""
        logger.info("Invoked ConsentTemplateService.get_third_party_pers_data")
        result = self._client.query(_SVC, self.TemplateThirdPartyPersData).get(
            templateId=template_id, thirdPartyId=third_party_id
        )
        logger.info("Exiting ConsentTemplateService.get_third_party_pers_data")
        return result

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_THIRD_PARTY_PERS_DATA
    )
    def create_third_party_pers_data(self, body: dict[str, Any]) -> Any:
        """Create a new TemplateThirdPartyPersData entity and return it."""
        logger.info("Invoked ConsentTemplateService.create_third_party_pers_data")
        entity = self.TemplateThirdPartyPersData()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.create_third_party_pers_data")
        return entity

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_THIRD_PARTY_PERS_DATA
    )
    def update_third_party_pers_data(
        self, template_id: str, third_party_id: str, body: dict[str, Any]
    ) -> Any:
        """Fetch a TemplateThirdPartyPersData by composite key, apply updates, and PATCH it."""
        logger.info("Invoked ConsentTemplateService.update_third_party_pers_data")
        entity = self._client.query(_SVC, self.TemplateThirdPartyPersData).get(
            templateId=template_id, thirdPartyId=third_party_id
        )
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentTemplateService.update_third_party_pers_data")
        return entity

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_THIRD_PARTY_PERS_DATA
    )
    def delete_third_party_pers_data(
        self, template_id: str, third_party_id: str
    ) -> None:
        """Delete a TemplateThirdPartyPersData by its composite key."""
        logger.info("Invoked ConsentTemplateService.delete_third_party_pers_data")
        entity = self._client.query(_SVC, self.TemplateThirdPartyPersData).get(
            templateId=template_id, thirdPartyId=third_party_id
        )
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentTemplateService.delete_third_party_pers_data")
