"""Service client for consentRetentionExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentRetentionExternalServices"


class ConsentRetentionService:
    """Client for consentRetentionExternalServices - CRUD on data retention rules."""

    def __init__(
        self,
        client: _ODataClient,
        *,
        _telemetry_source: Module | None = None,
    ) -> None:
        """Bind entity classes from the consentRetentionExternalServices endpoint."""
        logger.info("Invoked ConsentRetentionService.__init__")
        self._client = client
        self._telemetry_source = _telemetry_source
        (self.ConsentRetentionRule,) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentRetentionService.__init__")

    # ------ consentRetentionRules ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_LIST_RULES)
    def list_rules(self, **query: Any) -> list[Any]:
        """Return all consent retention rule records, optionally filtered and paged via OData query kwargs.

        Args:
            **query: OData query options forwarded to the service (e.g. ``filter``,
                ``top``, ``skip``, ``orderby``).

        Returns:
            list of ConsentRetentionRule objects matching the query.

        Raises:
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.list_rules")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentRetentionRule), query
        ).all()
        logger.info("Exiting ConsentRetentionService.list_rules")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_GET_RULE)
    def get_rule(self, rule_id: str) -> Any:
        """Return a single ConsentRetentionRule entity by its UUID.

        Args:
            rule_id: UUID of the ConsentRetentionRule to retrieve.

        Returns:
            The matching ConsentRetentionRule object.

        Raises:
            NotFoundError: If no ConsentRetentionRule with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.get_rule")
        result = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        logger.info("Exiting ConsentRetentionService.get_rule")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_CREATE_RULE)
    def create_rule(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentRetentionRule entity and return it.

        Args:
            body: Dictionary of field names and values for the new ConsentRetentionRule.

        Returns:
            The newly created ConsentRetentionRule object with server-assigned fields populated.

        Raises:
            ValidationError: If the request body fails server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.create_rule")
        entity = self.ConsentRetentionRule()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentRetentionService.create_rule")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_UPDATE_RULE)
    def update_rule(self, rule_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ConsentRetentionRule by ID, apply field updates, and PATCH it to the service.

        Args:
            rule_id: UUID of the ConsentRetentionRule to update.
            body: Dictionary of field names and values to apply.

        Returns:
            The updated ConsentRetentionRule object.

        Raises:
            NotFoundError: If no ConsentRetentionRule with the given ID exists.
            ValidationError: If the updated fields fail server-side validation.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.update_rule")
        entity = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        self._client._apply_body(entity, body)
        self._client.save(entity)
        logger.info("Exiting ConsentRetentionService.update_rule")
        return entity

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_DELETE_RULE)
    def delete_rule(self, rule_id: str) -> None:
        """Delete a ConsentRetentionRule entity by its UUID.

        Args:
            rule_id: UUID of the ConsentRetentionRule to delete.

        Raises:
            NotFoundError: If no ConsentRetentionRule with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.delete_rule")
        entity = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentRetentionService.delete_rule")

    # ------ lifecycle actions ------

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_RULE_ACTIVE)
    def set_rule_active(self, rule_id: str) -> Any:
        """Activate a consent retention rule and return the refreshed entity.

        Args:
            rule_id: UUID of the ConsentRetentionRule to activate.

        Returns:
            The refreshed ConsentRetentionRule object with its status set to active.

        Raises:
            NotFoundError: If no ConsentRetentionRule with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.set_rule_active")
        self._client.call_action(
            _SVC, "consentRetentionRuleSetConsentRetentionToActive", {"ruleId": rule_id}
        )
        result = self.get_rule(rule_id)
        logger.info("Exiting ConsentRetentionService.set_rule_active")
        return result

    @record_metrics(Module.DPI_NG, Operation.DPI_NG_CONSENT_SET_RULE_INACTIVE)
    def set_rule_inactive(self, rule_id: str) -> Any:
        """Deactivate a consent retention rule and return the refreshed entity.

        Args:
            rule_id: UUID of the ConsentRetentionRule to deactivate.

        Returns:
            The refreshed ConsentRetentionRule object with its status set to inactive.

        Raises:
            NotFoundError: If no ConsentRetentionRule with the given ID exists.
            ODataError: If the OData service returns an unexpected error response.
        """
        logger.info("Invoked ConsentRetentionService.set_rule_inactive")
        self._client.call_action(
            _SVC,
            "consentRetentionRuleSetConsentRetentionToInactive",
            {"ruleId": rule_id},
        )
        result = self.get_rule(rule_id)
        logger.info("Exiting ConsentRetentionService.set_rule_inactive")
        return result
