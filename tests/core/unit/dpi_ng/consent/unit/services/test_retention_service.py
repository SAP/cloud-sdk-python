"""Unit tests for ConsentRetentionService."""

from __future__ import annotations

import pytest

_SVC = "consentRetentionExternalServices"


@pytest.fixture
def svc(mock_retention_client):
    from sap_cloud_sdk.core.dpi_ng.consent.services.consent_retention_service import (
        ConsentRetentionService,
    )

    return ConsentRetentionService(mock_retention_client)


@pytest.fixture
def client(mock_retention_client):
    return mock_retention_client


@pytest.fixture
def q(client):
    return client.query.return_value


class TestListRules:
    def test_list_rules(self, svc, client, q):
        result = svc.list_rules()
        client.query.assert_called_with(_SVC, svc.ConsentRetentionRule)
        q.all.assert_called_once()
        assert result == q.all.return_value

    def test_query_filter(self, svc, client, q):
        svc.list_rules(filter="lifecycle_status_code eq '1'")
        q.raw.assert_called_with({"$filter": "lifecycle_status_code eq '1'"})

    def test_query_top(self, svc, client, q):
        svc.list_rules(top=3)
        q.limit.assert_called_with(3)


class TestGetRule:
    def test_get_rule(self, svc, client, q):
        result = svc.get_rule("rid")
        client.query.assert_called_with(_SVC, svc.ConsentRetentionRule)
        q.get.assert_called_with("rid")
        assert result == q.get.return_value


class TestCreateRule:
    def test_create_rule(self, svc, client):
        body = {"rule_name": "Rule A", "retention_years": 2}
        svc.create_rule(body)
        client.save.assert_called_once()


class TestUpdateRule:
    def test_update_rule(self, svc, client, q):
        body = {"retention_years": 5}
        svc.update_rule("rid", body)
        q.get.assert_called_with("rid")
        client.save.assert_called_once()


class TestDeleteRule:
    def test_delete_rule(self, svc, client, q):
        svc.delete_rule("rid")
        q.get.assert_called_with("rid")
        client.delete_entity.assert_called_once_with(q.get.return_value)


class TestSetRuleActive:
    def test_set_rule_active(self, svc, client):
        svc.set_rule_active("rid")
        client.call_action.assert_called_once_with(
            _SVC,
            "consentRetentionRuleSetConsentRetentionToActive",
            {"ruleId": "rid"},
        )

    def test_set_rule_active_returns_refreshed(self, svc, client, q):
        svc.set_rule_active("rid")
        q.get.assert_called_with("rid")


class TestSetRuleInactive:
    def test_set_rule_inactive(self, svc, client):
        svc.set_rule_inactive("rid")
        client.call_action.assert_called_once_with(
            _SVC,
            "consentRetentionRuleSetConsentRetentionToInactive",
            {"ruleId": "rid"},
        )

    def test_set_rule_inactive_returns_refreshed(self, svc, client, q):
        svc.set_rule_inactive("rid")
        q.get.assert_called_with("rid")
