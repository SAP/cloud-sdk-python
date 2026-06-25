"""Unit tests for ConsentPurposeService."""

from __future__ import annotations

import pytest

_SVC = "consentPurposeExternalServices"


@pytest.fixture
def svc(mock_purpose_client):
    from sap_cloud_sdk.core.dpi_ng.consent.services.consent_purpose_service import (
        ConsentPurposeService,
    )

    return ConsentPurposeService(mock_purpose_client)


@pytest.fixture
def client(mock_purpose_client):
    return mock_purpose_client


@pytest.fixture
def q(client):
    return client.query.return_value


class TestListPurposes:
    def test_list_purposes(self, svc, client, q):
        result = svc.list_purposes()
        client.query.assert_called_with(_SVC, svc.ConsentPurpose)
        q.all.assert_called_once()
        assert result == q.all.return_value

    def test_query_filter(self, svc, client, q):
        svc.list_purposes(filter="purpose_name eq 'test'")
        q.raw.assert_called_with({"$filter": "purpose_name eq 'test'"})

    def test_query_top_skip(self, svc, client, q):
        svc.list_purposes(top=5, skip=2)
        q.limit.assert_called_with(5)
        q.offset.assert_called_with(2)


class TestGetPurpose:
    def test_get_purpose(self, svc, client, q):
        result = svc.get_purpose("pid")
        client.query.assert_called_with(_SVC, svc.ConsentPurpose)
        q.get.assert_called_with("pid")
        assert result == q.get.return_value


class TestCreatePurpose:
    def test_create_purpose(self, svc, client):
        body = {"purpose_name": "My Purpose", "lifecycle_status_code": "1"}
        svc.create_purpose(body)
        client.save.assert_called_once()


class TestUpdatePurpose:
    def test_update_purpose(self, svc, client, q):
        body = {"purpose_name": "Updated"}
        svc.update_purpose("pid", body)
        q.get.assert_called_with("pid")
        client.save.assert_called_once()


class TestDeletePurpose:
    def test_delete_purpose(self, svc, client, q):
        svc.delete_purpose("pid")
        q.get.assert_called_with("pid")
        client.delete_entity.assert_called_once_with(q.get.return_value)


class TestSetPurposeActive:
    def test_set_purpose_active_calls_action(self, svc, client):
        svc.set_purpose_active("pid")
        client.call_action.assert_called_once_with(
            _SVC,
            "consentPurposeSetConsentPurposeToActive",
            {"purposeId": "pid"},
        )

    def test_set_purpose_active_returns_refreshed_entity(self, svc, client, q):
        svc.set_purpose_active("pid")
        q.get.assert_called_with("pid")


class TestSetPurposeInactive:
    def test_set_purpose_inactive_calls_action(self, svc, client):
        svc.set_purpose_inactive("pid")
        client.call_action.assert_called_once_with(
            _SVC,
            "consentPurposeSetConsentPurposeToInactive",
            {"purposeId": "pid"},
        )

    def test_set_purpose_inactive_returns_refreshed_entity(self, svc, client, q):
        svc.set_purpose_inactive("pid")
        q.get.assert_called_with("pid")


class TestListPurposeTexts:
    def test_list_purpose_texts(self, svc, client, q):
        result = svc.list_purpose_texts()
        client.query.assert_called_with(_SVC, svc.ConsentPurposeText)
        q.all.assert_called_once()
        assert result == q.all.return_value


class TestGetPurposeText:
    def test_get_purpose_text_composite_key(self, svc, client, q):
        result = svc.get_purpose_text("pid", "tc", "EN")
        client.query.assert_called_with(_SVC, svc.ConsentPurposeText)
        q.get.assert_called_with(purposeId="pid", typeCode="tc", languageCode="EN")
        assert result == q.get.return_value


class TestCreatePurposeText:
    def test_create_purpose_text(self, svc, client):
        body = {
            "purpose_id": "pid",
            "type_code": "tc",
            "language_code": "EN",
            "text": "hello",
        }
        svc.create_purpose_text(body)
        client.save.assert_called_once()


class TestUpdatePurposeText:
    def test_update_purpose_text_composite_key(self, svc, client, q):
        body = {"text": "updated"}
        svc.update_purpose_text("pid", "tc", "EN", body)
        q.get.assert_called_with(purposeId="pid", typeCode="tc", languageCode="EN")
        client.save.assert_called_once()


class TestDeletePurposeText:
    def test_delete_purpose_text_composite_key(self, svc, client, q):
        svc.delete_purpose_text("pid", "tc", "EN")
        q.get.assert_called_with(purposeId="pid", typeCode="tc", languageCode="EN")
        client.delete_entity.assert_called_once_with(q.get.return_value)
