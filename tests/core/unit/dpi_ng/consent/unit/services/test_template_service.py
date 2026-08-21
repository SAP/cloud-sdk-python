"""Unit tests for ConsentTemplateService."""

from __future__ import annotations

import pytest


_SVC = "consentTemplateExternalServices"


@pytest.fixture
def svc(mock_template_client):
    from sap_cloud_sdk.core.dpi_ng.consent.services.consent_template_service import (
        ConsentTemplateService,
    )

    return ConsentTemplateService(mock_template_client)


# ---------------------------------------------------------------------------
# ConsentTemplate CRUD
# ---------------------------------------------------------------------------


class TestConsentTemplateCRUD:
    def test_list_templates(self, svc, mock_template_client):
        result = svc.list_templates()
        mock_template_client.query.assert_called_with(_SVC, svc.ConsentTemplate)
        mock_template_client.query.return_value.all.assert_called_once()
        assert result == []

    def test_get_template(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        returned = svc.get_template("tid")
        mock_template_client.query.assert_called_with(_SVC, svc.ConsentTemplate)
        q.get.assert_called_with("tid")
        assert returned is q.get.return_value

    def test_create_template(self, svc, mock_template_client):
        svc.create_template({"template_name": "T1", "jurisdiction_code": "DE"})
        mock_template_client.save.assert_called_once()

    def test_create_template_sets_fields(self, svc, mock_template_client):
        svc.create_template({"template_name": "T1"})
        call_arg = mock_template_client.save.call_args[0][0]
        assert call_arg.template_name == "T1"

    def test_update_template(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.update_template("tid", {"template_name": "updated"})
        q.get.assert_called_with("tid")
        mock_template_client.save.assert_called_once()

    def test_update_template_applies_fields(self, svc, mock_template_client):
        svc.update_template("tid", {"template_name": "new-name"})
        mock_template_client._apply_body.assert_called_once()

    def test_delete_template(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.delete_template("tid")
        q.get.assert_called_with("tid")
        mock_template_client.delete_entity.assert_called_once_with(q.get.return_value)


# ---------------------------------------------------------------------------
# Lifecycle actions
# ---------------------------------------------------------------------------


class TestTemplateLifecycleActions:
    def test_set_template_active_calls_action(self, svc, mock_template_client):
        svc.set_template_active("tid")
        mock_template_client.call_action.assert_called_once_with(
            _SVC,
            "consentTemplateSetConsentTemplateToActive",
            {"templateId": "tid"},
        )

    def test_set_template_inactive_calls_action(self, svc, mock_template_client):
        svc.set_template_inactive("tid")
        mock_template_client.call_action.assert_called_once_with(
            _SVC,
            "consentTemplateSetConsentTemplateToInactive",
            {"templateId": "tid"},
        )

    def test_set_template_active_returns_refreshed(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        result = svc.set_template_active("tid")
        q.get.assert_called_with("tid")
        assert result is q.get.return_value

    def test_set_template_inactive_returns_refreshed(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        result = svc.set_template_inactive("tid")
        q.get.assert_called_with("tid")
        assert result is q.get.return_value


# ---------------------------------------------------------------------------
# ConsentTemplateText (composite key: template_id + type_code + language_code)
# ---------------------------------------------------------------------------


class TestConsentTemplateText:
    def test_list_template_texts(self, svc, mock_template_client):
        result = svc.list_template_texts()
        mock_template_client.query.assert_called_with(_SVC, svc.ConsentTemplateText)
        mock_template_client.query.return_value.all.assert_called_once()
        assert result == []

    def test_get_template_text_by_id(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        result = svc.get_template_text("ttid")
        mock_template_client.query.assert_called_with(_SVC, svc.ConsentTemplateText)
        q.get.assert_called_with("ttid")
        assert result is q.get.return_value

    def test_create_template_text(self, svc, mock_template_client):
        svc.create_template_text({"text": "hello", "language_code": "EN"})
        mock_template_client.save.assert_called_once()

    def test_create_template_text_sets_fields(self, svc, mock_template_client):
        svc.create_template_text({"text": "hello"})
        call_arg = mock_template_client.save.call_args[0][0]
        assert call_arg.text == "hello"

    def test_update_template_text_fetches_by_id(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.update_template_text("ttid", {"text": "updated"})
        q.get.assert_called_with("ttid")
        mock_template_client.save.assert_called_once()

    def test_update_template_text_applies_fields(self, svc, mock_template_client):
        svc.update_template_text("ttid", {"text": "new text"})
        mock_template_client._apply_body.assert_called_once()

    def test_delete_template_text_fetches_by_id(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.delete_template_text("ttid")
        q.get.assert_called_with("ttid")
        mock_template_client.delete_entity.assert_called_once_with(q.get.return_value)


# ---------------------------------------------------------------------------
# TemplateThirdPartyPersData (composite key: third_party_assignment_id + template_id)
# ---------------------------------------------------------------------------


class TestTemplateThirdPartyPersData:
    def test_list_third_party_pers_data(self, svc, mock_template_client):
        result = svc.list_third_party_pers_data()
        mock_template_client.query.assert_called_with(
            _SVC, svc.TemplateThirdPartyPersData
        )
        mock_template_client.query.return_value.all.assert_called_once()
        assert result == []

    def test_get_third_party_pers_data_by_assignment_and_template(
        self, svc, mock_template_client
    ):
        q = mock_template_client.query.return_value
        result = svc.get_third_party_pers_data("tpaid", "tid")
        mock_template_client.query.assert_called_with(
            _SVC, svc.TemplateThirdPartyPersData
        )
        q.get.assert_called_with(thirdPartyAssignmentId="tpaid", templateId="tid")
        assert result is q.get.return_value

    def test_create_third_party_pers_data(self, svc, mock_template_client):
        svc.create_third_party_pers_data({"third_party_function_code": "PROCESSOR"})
        mock_template_client.save.assert_called_once()

    def test_create_third_party_pers_data_sets_fields(self, svc, mock_template_client):
        svc.create_third_party_pers_data({"third_party_function_code": "PROCESSOR"})
        call_arg = mock_template_client.save.call_args[0][0]
        assert call_arg.third_party_function_code == "PROCESSOR"

    def test_update_third_party_pers_data_by_assignment_and_template(
        self, svc, mock_template_client
    ):
        q = mock_template_client.query.return_value
        svc.update_third_party_pers_data(
            "tpaid", "tid", {"third_party_function_code": "CONTROLLER"}
        )
        q.get.assert_called_with(thirdPartyAssignmentId="tpaid", templateId="tid")
        mock_template_client.save.assert_called_once()

    def test_update_third_party_pers_data_applies_fields(
        self, svc, mock_template_client
    ):
        svc.update_third_party_pers_data(
            "tpaid", "tid", {"third_party_function_code": "CONTROLLER"}
        )
        mock_template_client._apply_body.assert_called_once()

    def test_delete_third_party_pers_data_by_assignment_and_template(
        self, svc, mock_template_client
    ):
        q = mock_template_client.query.return_value
        svc.delete_third_party_pers_data("tpaid", "tid")
        q.get.assert_called_with(thirdPartyAssignmentId="tpaid", templateId="tid")
        mock_template_client.delete_entity.assert_called_once_with(q.get.return_value)


# ---------------------------------------------------------------------------
# Query parameter forwarding (_apply_query) on list_templates
# ---------------------------------------------------------------------------


class TestQueryParams:
    def test_query_filter(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.list_templates(filter="lifecycle_status_code eq '1'")
        q.filter.assert_called_with("lifecycle_status_code eq '1'")

    def test_query_top_skip(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.list_templates(top=10, skip=5)
        q.limit.assert_called_with(10)
        q.offset.assert_called_with(5)

    def test_query_orderby(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.list_templates(orderby="template_name asc")
        q.order_by.assert_called_with("template_name asc")

    def test_query_no_params_skips_raw(self, svc, mock_template_client):
        q = mock_template_client.query.return_value
        svc.list_templates()
        q.raw.assert_not_called()
        q.limit.assert_not_called()
        q.offset.assert_not_called()
