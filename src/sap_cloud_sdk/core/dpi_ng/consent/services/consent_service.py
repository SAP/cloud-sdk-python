"""Service client for consentServices."""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ..client import _ODataClient
from ..dtos.consent import (
    CheckConsentExistsResult,
    CreateConsentRequest,
    WithdrawConsentRequest,
)
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentServices"


class ConsentService:
    """Client for consentServices - consent creation, withdrawal, and reads."""

    def __init__(
        self,
        client: _ODataClient,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Bind entity classes from the consentServices endpoint."""
        logger.info("Invoked ConsentService.__init__")
        self._client = client
        self._telemetry_source = _telemetry_source
        (self.Consent,) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentService.__init__")

    # ------ consents ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_CONSENTS)
    def list_consents(self, **query: Any) -> list[Any]:
        """Return all consents, optionally filtered/paged via OData query kwargs."""
        logger.info("Invoked ConsentService.list_consents")
        result = _apply_query(self._client.query(_SVC, self.Consent), query).all()
        logger.info("Exiting ConsentService.list_consents")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_CONSENT)
    def get_consent(self, consent_id: str) -> Any:
        """Return a single Consent entity by its UUID."""
        logger.info("Invoked ConsentService.get_consent")
        result = self._client.query(_SVC, self.Consent).get(consent_id)
        logger.info("Exiting ConsentService.get_consent")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_CONSENT)
    def delete_consent(self, consent_id: str) -> None:
        """Delete a Consent entity by its UUID."""
        logger.info("Invoked ConsentService.delete_consent")
        entity = self._client.query(_SVC, self.Consent).get(consent_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentService.delete_consent")

    # ------ actions ------

    @record_metrics(
        Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_CONSENT_FROM_TEMPLATE
    )
    def create_consent_from_template(self, request: CreateConsentRequest) -> list[Any]:
        """Invoke createConsentFromTemplate and return the resulting Consent entities."""
        logger.info("Invoked ConsentService.create_consent_from_template")
        result = self._client.call_action(
            _SVC, "createConsentFromTemplate", request.to_dict()
        )
        if result is None:
            logger.info(
                "Exiting ConsentService.create_consent_from_template — empty result"
            )
            return []
        values = result.get("value", result) if isinstance(result, dict) else result
        if not isinstance(values, list):
            values = [values]
        entities = [_dict_to_entity(self.Consent, v) for v in values]
        logger.info("Exiting ConsentService.create_consent_from_template")
        return entities

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_WITHDRAW_CONSENT)
    def withdraw_consent(
        self, request: WithdrawConsentRequest
    ) -> dict[str, Any] | None:
        """Invoke withdrawConsent and return the raw action response."""
        logger.info("Invoked ConsentService.withdraw_consent")
        result = self._client.call_action(_SVC, "withdrawConsent", request.to_dict())
        logger.info("Exiting ConsentService.withdraw_consent")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_TERMINATE_CONSENT)
    def terminate_consent(
        self, request: WithdrawConsentRequest
    ) -> dict[str, Any] | None:
        """Invoke terminateConsent and return the raw action response."""
        logger.info("Invoked ConsentService.terminate_consent")
        result = self._client.call_action(_SVC, "terminateConsent", request.to_dict())
        logger.info("Exiting ConsentService.terminate_consent")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CHECK_CONSENT_EXISTS)
    def check_consent_exists(
        self, data_subject_id: str, template_id: str
    ) -> CheckConsentExistsResult:
        """Check whether a consent record exists for the given data subject and template."""
        logger.info("Invoked ConsentService.check_consent_exists")
        result = self._client.call_action(
            _SVC,
            "checkConsentExists",
            {"dataSubjectId": data_subject_id, "templateId": template_id},
        )
        check_result = CheckConsentExistsResult.from_dict(result or {})
        logger.info("Exiting ConsentService.check_consent_exists")
        return check_result


def _dict_to_entity(entity_cls: type, data: dict[str, Any]) -> Any:
    """Wrap a raw dict as a persisted OData entity instance."""
    entity = entity_cls()
    entity.__odata__.update(data)
    entity.__odata__.persisted = True
    return entity
