"""Unit tests for dtos/consent.py — pure dataclass serialisation and from_dict."""

from __future__ import annotations


from sap_cloud_sdk.core.dpi_ng.consent.dtos.consent import (
    CheckConsentExistsResult,
    CreateConsentRequest,
    WithdrawConsentRequest,
)


class TestCreateConsentRequest:
    def test_to_dict_includes_required_fields(self):
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Customer",
            jurisdiction_code="DE",
        )
        result = req.to_dict()
        assert result["dataSubjectId"] == "ds-1"
        assert result["templateName"] == "tmpl"
        assert result["languageCode"] == "EN"
        assert result["dataSubjectTypeName"] == "Customer"
        assert result["jurisdictionCode"] == "DE"

    def test_to_dict_omits_none_optional_fields(self):
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Customer",
            jurisdiction_code="DE",
        )
        result = req.to_dict()
        optional_keys = [
            "dataSubjectDescription",
            "outboundChannelTypeName",
            "outboundChannel",
            "validFrom",
            "applicationTemplateId",
            "controllerName",
            "grantedBy",
            "grantedAt",
            "submissionSite",
        ]
        for key in optional_keys:
            assert key not in result

    def test_to_dict_includes_optional_fields_when_set(self):
        req = CreateConsentRequest(
            data_subject_id="ds-1",
            template_name="tmpl",
            language_code="EN",
            data_subject_type_name="Customer",
            jurisdiction_code="DE",
            data_subject_description="A customer",
            outbound_channel_type_name="Email",
            outbound_channel="channel-x",
            valid_from="2024-01-01",
            application_template_id="app-tmpl-99",
            controller_name="Controller A",
            granted_by="admin",
            granted_at="2024-01-01T00:00:00Z",
            submission_site="site-1",
        )
        result = req.to_dict()
        assert result["dataSubjectDescription"] == "A customer"
        assert result["outboundChannelTypeName"] == "Email"
        assert result["outboundChannel"] == "channel-x"
        assert result["validFrom"] == "2024-01-01"
        assert result["applicationTemplateId"] == "app-tmpl-99"
        assert result["controllerName"] == "Controller A"
        assert result["grantedBy"] == "admin"
        assert result["grantedAt"] == "2024-01-01T00:00:00Z"
        assert result["submissionSite"] == "site-1"


class TestWithdrawConsentRequest:
    def test_to_dict_includes_required_fields_and_omits_none(self):
        req = WithdrawConsentRequest(consent_id="c-1", withdrawn_by="user-a")
        result = req.to_dict()
        assert result["consentId"] == "c-1"
        assert result["withdrawnBy"] == "user-a"
        assert "withdrawnAt" not in result

    def test_to_dict_includes_withdrawn_at_when_set(self):
        req = WithdrawConsentRequest(
            consent_id="c-1",
            withdrawn_by="user-a",
            withdrawn_at="2024-06-01T12:00:00Z",
        )
        result = req.to_dict()
        assert result["withdrawnAt"] == "2024-06-01T12:00:00Z"


class TestCheckConsentExistsResult:
    def test_from_dict_round_trip(self):
        data = {"consentId": "c-99", "consentExists": True}
        result = CheckConsentExistsResult.from_dict(data)
        assert result.consent_id == "c-99"
        assert result.consent_exists is True

    def test_from_dict_consent_not_exists(self):
        data = {"consentId": "c-00", "consentExists": False}
        result = CheckConsentExistsResult.from_dict(data)
        assert result.consent_exists is False

    def test_from_dict_empty_dict_yields_none_fields(self):
        result = CheckConsentExistsResult.from_dict({})
        assert result.consent_id is None
        assert result.consent_exists is None

    def test_from_dict_returns_check_consent_exists_result_instance(self):
        result = CheckConsentExistsResult.from_dict(
            {"consentId": "c-1", "consentExists": True}
        )
        assert isinstance(result, CheckConsentExistsResult)
