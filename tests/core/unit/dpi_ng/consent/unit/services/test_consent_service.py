import pytest
from unittest.mock import MagicMock, patch
from sap_cloud_sdk.core.dpi_ng.consent.dtos.consent import (
    CheckConsentExistsResult,
    CreateConsentRequest,
    WithdrawConsentRequest,
)


@pytest.fixture
def svc(mock_consent_client):
    from sap_cloud_sdk.core.dpi_ng.consent.services.consent_service import (
        ConsentService,
    )

    return ConsentService(mock_consent_client)


@pytest.fixture
def client(mock_consent_client):
    return mock_consent_client


@pytest.fixture
def q(client):
    return client.query.return_value


class TestListAndGet:
    def test_list_consents(self, svc, mock_consent_client):
        result = svc.list_consents()
        mock_consent_client.query.assert_called_with("consentServices", svc.Consent)
        assert result == []

    def test_get_consent(self, svc, mock_consent_client):
        q = mock_consent_client.query.return_value
        svc.get_consent("some-uuid")
        mock_consent_client.query.assert_called_with("consentServices", svc.Consent)
        q.get.assert_called_once_with("some-uuid")


_MODULE = "sap_cloud_sdk.core.dpi_ng.consent.services.consent_service"


class TestCreateConsentFromTemplate:
    def test_create_consent_from_template_returns_list(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = {
            "value": [{"consent_id": "c-1"}]
        }
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Employee",
            jurisdiction_code="DE",
        )
        with patch(f"{_MODULE}._dict_to_entity", return_value=MagicMock()) as mock_dte:
            result = svc.create_consent_from_template(req)
            mock_dte.assert_called_once()
        mock_consent_client.call_action.assert_called_once_with(
            "consentServices", "createConsentFromTemplate", req.to_dict()
        )
        assert isinstance(result, list)
        assert len(result) == 1

    def test_create_consent_from_template_none_result(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = None
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Employee",
            jurisdiction_code="DE",
        )
        result = svc.create_consent_from_template(req)
        assert result == []

    def test_create_consent_from_template_bare_dict(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = {"consent_id": "c-2"}
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Employee",
            jurisdiction_code="DE",
        )
        with patch(f"{_MODULE}._dict_to_entity", return_value=MagicMock()) as mock_dte:
            result = svc.create_consent_from_template(req)
            mock_dte.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 1


class TestDeleteConsent:
    def test_delete_consent(self, svc, client, q):
        svc.delete_consent("c-1")
        q.get.assert_called_with("c-1")
        client.delete_entity.assert_called_once_with(q.get.return_value)


class TestWithdrawAndTerminate:
    def test_withdraw_consent(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = None
        req = WithdrawConsentRequest(consent_id="c-1", withdrawn_by="user-1")
        svc.withdraw_consent(req)
        mock_consent_client.call_action.assert_called_once_with(
            "consentServices", "withdrawConsent", req.to_dict()
        )

    def test_terminate_consent(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = None
        req = WithdrawConsentRequest(consent_id="c-1", withdrawn_by="user-1")
        svc.terminate_consent(req)
        mock_consent_client.call_action.assert_called_once_with(
            "consentServices", "terminateConsent", req.to_dict()
        )


class TestCheckConsentExists:
    def test_check_consent_exists(self, svc, mock_consent_client):
        mock_consent_client.call_action.return_value = {
            "consentId": "c-1",
            "consentExists": True,
        }
        result = svc.check_consent_exists("ds-1", "tmpl-1")
        mock_consent_client.call_action.assert_called_once_with(
            "consentServices",
            "checkConsentExists",
            {"dataSubjectId": "ds-1", "templateId": "tmpl-1"},
        )
        assert isinstance(result, CheckConsentExistsResult)
        assert result.consent_exists is True


class TestQueryKwargs:
    def test_query_filter_kwarg(self, svc, mock_consent_client):
        q = mock_consent_client.query.return_value
        svc.list_consents(filter="x eq 'y'")
        q.filter.assert_called_with("x eq 'y'")

    def test_query_top_skip(self, svc, mock_consent_client):
        q = mock_consent_client.query.return_value
        svc.list_consents(top=10, skip=5)
        q.limit.assert_called_with(10)
        q.offset.assert_called_with(5)

    def test_query_orderby(self, svc, mock_consent_client):
        q = mock_consent_client.query.return_value
        svc.list_consents(orderby="changedAt desc")
        q.order_by.assert_called_with("changedAt desc")


class TestDictToEntity:
    def test_wraps_data_as_persisted_entity(self):
        from sap_cloud_sdk.core.dpi_ng.consent.services.consent_service import (
            _dict_to_entity,
        )

        entity_cls = MagicMock()
        entity = entity_cls.return_value
        entity.__odata__ = MagicMock()
        data = {"consentId": "c-1", "status": "active"}
        result = _dict_to_entity(entity_cls, data)
        entity.__odata__.update.assert_called_once_with(data)
        assert entity.__odata__.persisted is True
        assert result is entity
