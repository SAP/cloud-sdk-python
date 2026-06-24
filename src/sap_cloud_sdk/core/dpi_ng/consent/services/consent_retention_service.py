"""Service client for consentRetentionExternalServices."""

from __future__ import annotations

import logging
from typing import Any

from ..client import _ODataClient
from ._query import _apply_query

logger = logging.getLogger(__name__)

_SVC = "consentRetentionExternalServices"


class ConsentRetentionService:
    """Client for consentRetentionExternalServices - CRUD on data retention rules."""

    def __init__(self, client: _ODataClient) -> None:
        """Bind entity classes from the consentRetentionExternalServices endpoint."""
        logger.info("Invoked ConsentRetentionService.__init__")
        self._client = client
        (self.ConsentRetentionRule,) = client.get_entity_classes(_SVC)
        logger.info("Exiting ConsentRetentionService.__init__")

    # ------ consentRetentionRules ------

    def list_rules(self, **query: Any) -> list[Any]:
        """Return all retention rules, optionally filtered/paged via OData query kwargs."""
        logger.info("Invoked ConsentRetentionService.list_rules")
        result = _apply_query(
            self._client.query(_SVC, self.ConsentRetentionRule), query
        ).all()
        logger.info("Exiting ConsentRetentionService.list_rules")
        return result

    def get_rule(self, rule_id: str) -> Any:
        """Return a single ConsentRetentionRule entity by its UUID."""
        logger.info("Invoked ConsentRetentionService.get_rule")
        result = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        logger.info("Exiting ConsentRetentionService.get_rule")
        return result

    def create_rule(self, body: dict[str, Any]) -> Any:
        """Create a new ConsentRetentionRule entity and return it."""
        logger.info("Invoked ConsentRetentionService.create_rule")
        entity = self.ConsentRetentionRule()
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentRetentionService.create_rule")
        return entity

    def update_rule(self, rule_id: str, body: dict[str, Any]) -> Any:
        """Fetch a ConsentRetentionRule by ID, apply field updates, and PATCH it."""
        logger.info("Invoked ConsentRetentionService.update_rule")
        entity = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        for k, v in body.items():
            setattr(entity, k, v)
        self._client.save(entity)
        logger.info("Exiting ConsentRetentionService.update_rule")
        return entity

    def delete_rule(self, rule_id: str) -> None:
        """Delete a ConsentRetentionRule by its UUID."""
        logger.info("Invoked ConsentRetentionService.delete_rule")
        entity = self._client.query(_SVC, self.ConsentRetentionRule).get(rule_id)
        self._client.delete_entity(entity)
        logger.info("Exiting ConsentRetentionService.delete_rule")

    # ------ lifecycle actions ------

    def set_rule_active(self, rule_id: str) -> Any:
        """Activate a retention rule and return the refreshed entity."""
        logger.info("Invoked ConsentRetentionService.set_rule_active")
        self._client.call_action(
            _SVC, "consentRetentionRuleSetConsentRetentionToActive", {"ruleId": rule_id}
        )
        result = self.get_rule(rule_id)
        logger.info("Exiting ConsentRetentionService.set_rule_active")
        return result

    def set_rule_inactive(self, rule_id: str) -> Any:
        """Deactivate a retention rule and return the refreshed entity."""
        logger.info("Invoked ConsentRetentionService.set_rule_inactive")
        self._client.call_action(
            _SVC,
            "consentRetentionRuleSetConsentRetentionToInactive",
            {"ruleId": rule_id},
        )
        result = self.get_rule(rule_id)
        logger.info("Exiting ConsentRetentionService.set_rule_inactive")
        return result
