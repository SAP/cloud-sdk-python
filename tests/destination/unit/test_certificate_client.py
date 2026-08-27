"""Unit tests for CertificateClient."""

import pytest
from unittest.mock import Mock, call
from requests import Response

from sap_cloud_sdk.destination.certificate_client import CertificateClient
from sap_cloud_sdk.destination._models import AccessStrategy, Certificate, Label, Level, ListOptions, PatchLabels
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)


def _make_response(status=200, json_data=None, text="", headers=None):
    resp = Mock(spec=Response)
    resp.status_code = status
    resp.text = text
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


@pytest.fixture
def mock_http():
    http = Mock()
    http.request.return_value = _make_response(200)
    return http


@pytest.fixture
def certificate_client(mock_http):
    return CertificateClient(http=mock_http)


class TestCertificateClientInit:

    def test_init_with_http(self, mock_http):
        client = CertificateClient(http=mock_http)
        assert client._http is mock_http


class TestCertificateClientRead:

    def test_get_instance_certificate_success(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM",
        })
        certificate = certificate_client.get_instance_certificate("test-cert.pem")
        assert certificate is not None
        assert certificate.name == "test-cert.pem"
        assert certificate.content == "base64-encoded-content"
        assert certificate.type == "PEM"
        args, kwargs = mock_http.request.call_args
        assert args[0] == "GET"
        assert args[1] == "/v1/instanceCertificates/test-cert.pem"
        assert kwargs["tenant_subdomain"] is None

    def test_get_subaccount_certificate_success(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM",
        })
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert certificate is not None
        assert certificate.name == "test-cert.pem"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountCertificates/test-cert.pem"
        assert kwargs["tenant_subdomain"] is None

    def test_get_certificate_not_found(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        certificate = certificate_client.get_instance_certificate("nonexistent.pem")
        assert certificate is None

    def test_get_certificate_http_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert.pem")
        assert "failed to get certificate 'test-cert.pem'" in str(exc_info.value)

    def test_get_certificate_invalid_json(self, certificate_client, mock_http):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert.pem")
        assert "invalid JSON in get certificate response" in str(exc_info.value)

    def test_get_subaccount_certificate_access_strategies(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM",
        })
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert certificate is not None
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

        mock_http.reset_mock()
        mock_http.request.return_value = _make_response(200, {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM",
        })
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert certificate is not None
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_subaccount_certificate_requires_tenant_for_subscriber_access(self, certificate_client, mock_http):
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_get_subaccount_certificate_fallback_strategies(self, certificate_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(404, text="Not Found"),
            _make_response(200, {"Name": "test-cert.pem", "Content": "base64-encoded-content", "Type": "PEM"}),
        ]
        certificate = certificate_client.get_subaccount_certificate(
            "test-cert.pem",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
        )
        assert certificate is not None
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] == "test-tenant"
        assert calls[1][1]["tenant_subdomain"] is None


class TestCertificateClientWrite:

    def test_create_certificate_subaccount(self, certificate_client, mock_http):
        certificate = Certificate(name="new-cert.pem", content="base64-encoded-content", type="PEM")
        certificate_client.create_certificate(certificate, level=Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/v1/subaccountCertificates"
        assert kwargs["json"]["Name"] == "new-cert.pem"
        assert kwargs["json"]["Content"] == "base64-encoded-content"
        assert kwargs["json"]["Type"] == "PEM"

    def test_create_certificate_instance(self, certificate_client, mock_http):
        certificate = Certificate(name="new-cert.jks", content="base64-encoded-jks-content", type="JKS")
        certificate_client.create_certificate(certificate, level=Level.SERVICE_INSTANCE)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/instanceCertificates"

    def test_create_certificate_with_tenant(self, certificate_client, mock_http):
        certificate = Certificate(name="new-cert.pem", content="base64-encoded-content", type="PEM")
        certificate_client.create_certificate(certificate, level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_create_certificate_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        certificate = Certificate(name="new-cert.pem", content="base64-encoded-content")
        certificate_client.create_certificate(certificate)
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_create_certificate_http_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(409, text="Conflict")
        certificate = Certificate(name="test-cert.pem", content="content")
        with pytest.raises(HttpError):
            certificate_client.create_certificate(certificate)

    def test_update_certificate_success(self, certificate_client, mock_http):
        certificate = Certificate(name="existing-cert.pem", content="updated-base64-content", type="PEM")
        certificate_client.update_certificate(certificate, level=Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == "PUT"
        assert args[1] == "/v1/subaccountCertificates"
        assert kwargs["json"]["Name"] == "existing-cert.pem"

    def test_update_certificate_with_tenant(self, certificate_client, mock_http):
        certificate = Certificate(name="existing-cert.pem", content="updated-content", type="PEM")
        certificate_client.update_certificate(certificate, level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_certificate_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        certificate = Certificate(name="existing-cert.pem", content="content")
        certificate_client.update_certificate(certificate)
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_certificate_http_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        certificate = Certificate(name="test-cert.pem", content="content")
        with pytest.raises(HttpError):
            certificate_client.update_certificate(certificate)

    def test_delete_certificate_with_tenant(self, certificate_client, mock_http):
        certificate_client.delete_certificate("test-cert.pem", level=Level.SUB_ACCOUNT, tenant="test-tenant")
        args, kwargs = mock_http.request.call_args
        assert args[0] == "DELETE"
        assert args[1] == "/v1/subaccountCertificates/test-cert.pem"
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_delete_certificate_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        certificate_client.delete_certificate("test-cert.pem")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_delete_certificate_success(self, certificate_client, mock_http):
        certificate_client.delete_certificate("test-cert.pem", level=Level.SUB_ACCOUNT)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountCertificates/test-cert.pem"

    def test_delete_certificate_instance_level(self, certificate_client, mock_http):
        certificate_client.delete_certificate("test-cert.pem", level=Level.SERVICE_INSTANCE)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/instanceCertificates/test-cert.pem"

    def test_delete_certificate_http_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            certificate_client.delete_certificate("test-cert.pem")


class TestCertificateClientHelpers:

    def test_sub_path_for_level_instance(self):
        path = CertificateClient._sub_path_for_level(Level.SERVICE_INSTANCE)
        assert path == "instanceCertificates"

    def test_sub_path_for_level_subaccount(self):
        path = CertificateClient._sub_path_for_level(Level.SUB_ACCOUNT)
        assert path == "subaccountCertificates"


class TestCertificateClientListOperations:

    def test_list_instance_certificates_success(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [
            {"Name": "cert1.pem", "Content": "content1", "Type": "PEM"},
            {"Name": "cert2.jks", "Content": "content2", "Type": "JKS"},
        ])
        certificates = certificate_client.list_instance_certificates()
        assert len(certificates.items) == 2
        assert certificates.items[0].name == "cert1.pem"
        assert certificates.items[1].name == "cert2.jks"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceCertificates"
        assert kwargs["tenant_subdomain"] is None

    def test_list_instance_certificates_empty(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificates = certificate_client.list_instance_certificates()
        assert certificates == PagedResult(items=[])

    def test_list_instance_certificates_with_filter(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        filter_obj = ListOptions(filter_names=["cert1.pem", "cert2.pem"])
        certificates = certificate_client.list_instance_certificates(filter=filter_obj)
        assert len(certificates.items) == 1
        _, kwargs = mock_http.request.call_args
        assert "$filter" in kwargs["params"]

    def test_list_instance_certificates_http_error_wrapped(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        assert "failed to list instance certificates" in str(exc_info.value)

    def test_list_instance_certificates_invalid_json_wrapped(self, certificate_client, mock_http):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        assert "invalid JSON in list certificates response" in str(exc_info.value)

    def test_list_instance_certificates_with_tenant(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1", "Type": "PEM"}])
        certificates = certificate_client.list_instance_certificates(tenant="my-tenant")
        assert len(certificates.items) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "my-tenant"

    def test_list_subaccount_certificates_requires_tenant_for_subscriber_access(self, certificate_client, mock_http):
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided" in str(exc_info.value)

    def test_list_subaccount_certificates_provider_only_no_tenant_required(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert len(certificates.items) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_list_subaccount_certificates_subscriber_only_with_tenant(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert len(certificates.items) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_list_subaccount_certificates_subscriber_first_no_fallback(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert len(certificates.items) == 1
        assert mock_http.request.call_count == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_list_subaccount_certificates_subscriber_first_fallback_to_provider(self, certificate_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(200, []),
            _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}]),
        ]
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert len(certificates.items) == 1
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] == "test-tenant"
        assert calls[1][1]["tenant_subdomain"] is None

    def test_list_subaccount_certificates_provider_first_no_fallback(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert len(certificates.items) == 1
        assert mock_http.request.call_count == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_list_subaccount_certificates_provider_first_fallback_to_subscriber(self, certificate_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(200, []),
            _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}]),
        ]
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert len(certificates.items) == 1
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] is None
        assert calls[1][1]["tenant_subdomain"] == "test-tenant"

    def test_list_subaccount_certificates_with_filter(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"Name": "cert1.pem", "Content": "content1"}])
        filter_obj = ListOptions(filter_names=["cert1.pem"])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_ONLY, filter=filter_obj)
        assert len(certificates.items) == 1
        _, kwargs = mock_http.request.call_args
        assert "$filter" in kwargs["params"]

    def test_list_subaccount_certificates_http_error_wrapped(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert "failed to list subaccount certificates" in str(exc_info.value)


class TestCertificateClientEdgeCases:

    def test_create_certificate_unexpected_exception(self, certificate_client, mock_http):
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.request.side_effect = RuntimeError("Unexpected error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.create_certificate(certificate)
        assert "failed to create certificate 'test-cert.pem'" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)

    def test_update_certificate_unexpected_exception(self, certificate_client, mock_http):
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.request.side_effect = ValueError("Unexpected error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.update_certificate(certificate)
        assert "failed to update certificate 'test-cert.pem'" in str(exc_info.value)

    def test_delete_certificate_unexpected_exception(self, certificate_client, mock_http):
        mock_http.request.side_effect = ConnectionError("Network error")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.delete_certificate("test-cert.pem")
        assert "failed to delete certificate 'test-cert.pem'" in str(exc_info.value)

    def test_list_certificates_non_list_response(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"error": "not a list"})
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        assert "expected JSON array in list certificates response" in str(exc_info.value)

    def test_list_certificates_404_returns_empty(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        certificates = certificate_client.list_instance_certificates()
        assert certificates.items == []

    def test_list_subaccount_certificates_both_empty_subscriber_first(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert certificates == PagedResult(items=[])
        assert mock_http.request.call_count == 2

    def test_list_subaccount_certificates_both_empty_provider_first(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert certificates == PagedResult(items=[])
        assert mock_http.request.call_count == 2

    def test_get_certificate_malformed_certificate_data(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"Name": "", "Content": ""})
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert")
        assert "invalid JSON in get certificate response" in str(exc_info.value)

    def test_list_certificates_invalid_certificate_in_array(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [
            {"Name": "cert1.pem", "Content": "content1"},
            {"Name": "", "Content": ""},
        ])
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        assert "certificate is missing required fields" in str(exc_info.value)

    def test_apply_access_strategy_unknown_strategy(self, certificate_client, mock_http):
        unknown_strategy = Mock()
        unknown_strategy.value = "UNKNOWN"
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client._apply_access_strategy(
                access_strategy=unknown_strategy,
                tenant="test-tenant",
                fetch_func=lambda t: certificate_client._list_certificates(level=Level.SUB_ACCOUNT, tenant_subdomain=t),
            )
        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_get_subaccount_certificate_provider_first_both_none(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        certificate = certificate_client.get_subaccount_certificate("test-cert", access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert certificate is None
        assert mock_http.request.call_count == 2

    def test_get_subaccount_certificate_subscriber_first_both_none(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        certificate = certificate_client.get_subaccount_certificate("test-cert", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert certificate is None
        assert mock_http.request.call_count == 2

    def test_list_certificates_with_http_403_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(403, text="Forbidden")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        assert "failed to list instance certificates" in str(exc_info.value)

    def test_get_certificate_with_http_401_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(401, text="Unauthorized")
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert")
        assert "failed to get certificate 'test-cert'" in str(exc_info.value)


class TestCertificateClientLabels:

    def test_get_certificate_labels_instance(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"key": "env", "values": ["prod"]}])
        labels = certificate_client.get_certificate_labels("cert1", Level.SERVICE_INSTANCE)
        assert len(labels) == 1
        assert labels[0].key == "env"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceCertificates/cert1/labels"
        assert kwargs["tenant_subdomain"] is None

    def test_get_certificate_labels_subaccount(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"key": "team", "values": ["platform"]}])
        labels = certificate_client.get_certificate_labels("cert1", Level.SUB_ACCOUNT)
        assert labels[0].key == "team"
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountCertificates/cert1/labels"

    def test_get_certificate_labels_default_level_is_subaccount(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificate_client.get_certificate_labels("cert1")
        args, _ = mock_http.request.call_args
        assert "subaccountCertificates" in args[1]

    def test_get_certificate_labels_non_list_response_raises(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"key": "env"})
        with pytest.raises(DestinationOperationError):
            certificate_client.get_certificate_labels("cert1")

    def test_get_certificate_labels_http_error_raises_operation_error(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(DestinationOperationError, match="failed to get labels for certificate"):
            certificate_client.get_certificate_labels("cert1")

    def test_update_certificate_labels_instance(self, certificate_client, mock_http):
        labels = [Label(key="env", values=["prod"])]
        certificate_client.update_certificate_labels("cert1", labels, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == "PUT"
        assert args[1] == "/v1/instanceCertificates/cert1/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["prod"]}]
        assert kwargs["tenant_subdomain"] is None

    def test_update_certificate_labels_subaccount(self, certificate_client, mock_http):
        labels = [Label(key="env", values=["staging"])]
        certificate_client.update_certificate_labels("cert1", labels, Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountCertificates/cert1/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["staging"]}]

    def test_update_certificate_labels_http_error_propagates(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            certificate_client.update_certificate_labels("cert1", [], Level.SUB_ACCOUNT)

    def test_patch_certificate_labels_instance(self, certificate_client, mock_http):
        patch = PatchLabels(action="ADD", labels=[Label(key="env", values=["prod"])])
        certificate_client.patch_certificate_labels("cert1", patch, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == "PATCH"
        assert args[1] == "/v1/instanceCertificates/cert1/labels"
        assert kwargs["json"]["action"] == "ADD"
        assert kwargs["tenant_subdomain"] is None

    def test_patch_certificate_labels_subaccount(self, certificate_client, mock_http):
        patch = PatchLabels(action="DELETE", labels=[Label(key="env", values=[])])
        certificate_client.patch_certificate_labels("cert1", patch, Level.SUB_ACCOUNT)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountCertificates/cert1/labels"

    def test_patch_certificate_labels_http_error_propagates(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            certificate_client.patch_certificate_labels("cert1", PatchLabels(action="ADD", labels=[]), Level.SUB_ACCOUNT)

    def test_get_certificate_labels_with_tenant(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificate_client.get_certificate_labels("cert1", tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_certificate_labels_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        certificate_client.get_certificate_labels("cert1")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_certificate_labels_with_tenant(self, certificate_client, mock_http):
        certificate_client.update_certificate_labels("cert1", [], tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_certificate_labels_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        certificate_client.update_certificate_labels("cert1", [])
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_patch_certificate_labels_with_tenant(self, certificate_client, mock_http):
        certificate_client.patch_certificate_labels("cert1", PatchLabels(action="ADD", labels=[]), tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_patch_certificate_labels_without_tenant_uses_provider_context(self, certificate_client, mock_http):
        certificate_client.patch_certificate_labels("cert1", PatchLabels(action="ADD", labels=[]))
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None
