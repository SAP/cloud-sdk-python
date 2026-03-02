"""Unit tests for CertificateClient."""

import pytest
from unittest.mock import Mock
from requests import Response

from cloud_sdk_python.destination.certificate_client import CertificateClient
from cloud_sdk_python.destination._models import AccessStrategy, Certificate, Level, ListOptions
from cloud_sdk_python.destination.utils._pagination import PagedResult
from cloud_sdk_python.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)


@pytest.fixture
def mock_http():
    """Create a mock DestinationHttp instance."""
    return Mock()


@pytest.fixture
def certificate_client(mock_http):
    """Create a CertificateClient with mocked HTTP."""
    return CertificateClient(http=mock_http)


class TestCertificateClientInit:
    """Tests for CertificateClient initialization."""

    def test_init_with_http(self, mock_http):
        """Test CertificateClient initialization with HTTP transport."""
        client = CertificateClient(http=mock_http)
        assert client._http is mock_http


class TestCertificateClientRead:
    """Tests for CertificateClient read operations."""

    def test_get_instance_certificate_success(self, certificate_client, mock_http):
        """Test successful retrieval of instance certificate."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM"
        }
        mock_http.get.return_value = mock_response

        # Execute
        certificate = certificate_client.get_instance_certificate("test-cert.pem")

        # Verify
        assert certificate is not None
        assert certificate.name == "test-cert.pem"
        assert certificate.content == "base64-encoded-content"
        assert certificate.type == "PEM"
        mock_http.get.assert_called_once_with("v1/instanceCertificates/test-cert.pem", tenant_subdomain=None)

    def test_get_subaccount_certificate_success(self, certificate_client, mock_http):
        """Test successful retrieval of subaccount certificate."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM"
        }
        mock_http.get.return_value = mock_response

        # Execute
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_ONLY)

        # Verify
        assert certificate is not None
        assert certificate.name == "test-cert.pem"
        assert certificate.content == "base64-encoded-content"
        mock_http.get.assert_called_once_with("v1/subaccountCertificates/test-cert.pem", tenant_subdomain=None)

    def test_get_certificate_not_found(self, certificate_client, mock_http):
        """Test certificate retrieval when certificate doesn't exist (404)."""
        # Setup mock to raise 404
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        # Execute
        certificate = certificate_client.get_instance_certificate("nonexistent.pem")

        # Verify
        assert certificate is None

    def test_get_certificate_http_error(self, certificate_client, mock_http):
        """Test certificate retrieval with HTTP error (non-404)."""
        # Setup mock to raise 500
        http_error = HttpError("Internal Server Error")
        http_error.status_code = 500
        mock_http.get.side_effect = http_error

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert.pem")
        
        assert "failed to get certificate 'test-cert.pem'" in str(exc_info.value)

    def test_get_certificate_invalid_json(self, certificate_client, mock_http):
        """Test certificate retrieval with invalid JSON response."""
        # Setup mock response with invalid JSON
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = mock_response

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert.pem")
        
        assert "invalid JSON in get certificate response" in str(exc_info.value)

    def test_get_subaccount_certificate_access_strategies(self, certificate_client, mock_http):
        """Test subaccount certificate retrieval with different access strategies."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM"
        }
        mock_http.get.return_value = mock_response

        # Test PROVIDER_ONLY
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert certificate is not None
        mock_http.get.assert_called_with("v1/subaccountCertificates/test-cert.pem", tenant_subdomain=None)

        # Reset mock
        mock_http.reset_mock()

        # Test SUBSCRIBER_ONLY with tenant
        certificate = certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert certificate is not None
        mock_http.get.assert_called_with("v1/subaccountCertificates/test-cert.pem", tenant_subdomain="test-tenant")

    def test_get_subaccount_certificate_requires_tenant_for_subscriber_access(self, certificate_client, mock_http):
        """Test that subscriber access strategies require tenant parameter."""
        # Test SUBSCRIBER_ONLY without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test SUBSCRIBER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test PROVIDER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_subaccount_certificate("test-cert.pem", access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_get_subaccount_certificate_fallback_strategies(self, certificate_client, mock_http):
        """Test fallback behavior for SUBSCRIBER_FIRST and PROVIDER_FIRST strategies."""
        # Setup mock to return None for first call, certificate for second call
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM"
        }
        
        # Test SUBSCRIBER_FIRST fallback (subscriber fails, provider succeeds)
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = [
            http_error,  # Subscriber call fails
            mock_response  # Provider call succeeds
        ]
        
        certificate = certificate_client.get_subaccount_certificate(
            "test-cert.pem", 
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST, 
            tenant="test-tenant"
        )
        assert certificate is not None
        assert mock_http.get.call_count == 2
        
        # Verify calls were made in correct order
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountCertificates/test-cert.pem",), {"tenant_subdomain": "test-tenant"})
        assert calls[1] == (("v1/subaccountCertificates/test-cert.pem",), {"tenant_subdomain": None})


class TestCertificateClientWrite:
    """Tests for CertificateClient write operations."""

    def test_create_certificate_subaccount(self, certificate_client, mock_http):
        """Test creating a certificate at subaccount level."""
        # Setup
        certificate = Certificate(
            name="new-cert.pem",
            content="base64-encoded-content",
            type="PEM"
        )

        # Execute
        certificate_client.create_certificate(certificate, level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "v1/subaccountCertificates"
        assert call_args[1]["body"]["Name"] == "new-cert.pem"
        assert call_args[1]["body"]["Content"] == "base64-encoded-content"
        assert call_args[1]["body"]["Type"] == "PEM"

    def test_create_certificate_instance(self, certificate_client, mock_http):
        """Test creating a certificate at instance level."""
        # Setup
        certificate = Certificate(
            name="new-cert.jks",
            content="base64-encoded-jks-content",
            type="JKS"
        )

        # Execute
        certificate_client.create_certificate(certificate, level=Level.SERVICE_INSTANCE)

        # Verify
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "v1/instanceCertificates"

    def test_create_certificate_http_error(self, certificate_client, mock_http):
        """Test create certificate with HTTP error."""
        # Setup
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.post.side_effect = HttpError("Conflict")

        # Execute & Verify
        with pytest.raises(HttpError):
            certificate_client.create_certificate(certificate)

    def test_update_certificate_success(self, certificate_client, mock_http):
        """Test updating a certificate."""
        # Setup
        certificate = Certificate(
            name="existing-cert.pem",
            content="updated-base64-content",
            type="PEM"
        )

        # Execute
        certificate_client.update_certificate(certificate, level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.put.assert_called_once()
        call_args = mock_http.put.call_args
        assert call_args[0][0] == "v1/subaccountCertificates"
        assert call_args[1]["body"]["Name"] == "existing-cert.pem"

    def test_update_certificate_http_error(self, certificate_client, mock_http):
        """Test update certificate with HTTP error."""
        # Setup
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.put.side_effect = HttpError("Not Found")

        # Execute & Verify
        with pytest.raises(HttpError):
            certificate_client.update_certificate(certificate)

    def test_delete_certificate_success(self, certificate_client, mock_http):
        """Test deleting a certificate."""
        # Execute
        certificate_client.delete_certificate("test-cert.pem", level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.delete.assert_called_once_with("v1/subaccountCertificates/test-cert.pem")

    def test_delete_certificate_instance_level(self, certificate_client, mock_http):
        """Test deleting a certificate at instance level."""
        # Execute
        certificate_client.delete_certificate("test-cert.pem", level=Level.SERVICE_INSTANCE)

        # Verify
        mock_http.delete.assert_called_once_with("v1/instanceCertificates/test-cert.pem")

    def test_delete_certificate_http_error(self, certificate_client, mock_http):
        """Test delete certificate with HTTP error."""
        # Setup
        mock_http.delete.side_effect = HttpError("Not Found")

        # Execute & Verify
        with pytest.raises(HttpError):
            certificate_client.delete_certificate("test-cert.pem")


class TestCertificateClientHelpers:
    """Tests for CertificateClient helper methods."""

    def test_sub_path_for_level_instance(self):
        """Test sub-path generation for instance level."""
        path = CertificateClient._sub_path_for_level(Level.SERVICE_INSTANCE)
        assert path == "instanceCertificates"

    def test_sub_path_for_level_subaccount(self):
        """Test sub-path generation for subaccount level."""
        path = CertificateClient._sub_path_for_level(Level.SUB_ACCOUNT)
        assert path == "subaccountCertificates"


class TestCertificateClientListOperations:
    """Tests for CertificateClient list operations."""

    def test_list_instance_certificates_success(self, certificate_client, mock_http):
        """Test successful listing of instance certificates."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [
            {"Name": "cert1.pem", "Content": "content1", "Type": "PEM"},
            {"Name": "cert2.jks", "Content": "content2", "Type": "JKS"}
        ]
        mock_http.get.return_value = mock_response

        # Execute
        certificates = certificate_client.list_instance_certificates()

        # Verify
        assert len(certificates.items) == 2
        assert certificates.items[0].name == "cert1.pem"
        assert certificates.items[1].name == "cert2.jks"
        mock_http.get.assert_called_once_with("v1/instanceCertificates", tenant_subdomain=None, params={})

    def test_list_instance_certificates_empty(self, certificate_client, mock_http):
        """Test listing instance certificates when none exist."""
        # Setup mock response with empty array
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = []
        mock_http.get.return_value = mock_response

        # Execute
        certificates = certificate_client.list_instance_certificates()

        # Verify
        assert certificates == PagedResult(items=[])
        mock_http.get.assert_called_once()

    def test_list_instance_certificates_with_filter(self, certificate_client, mock_http):
        """Test listing instance certificates with filter."""

        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        filter_obj = ListOptions(filter_names=["cert1.pem", "cert2.pem"])

        # Execute
        certificates = certificate_client.list_instance_certificates(filter=filter_obj)

        # Verify
        assert len(certificates.items) == 1
        call_args = mock_http.get.call_args
        assert "params" in call_args[1]
        assert "$filter" in call_args[1]["params"]

    def test_list_instance_certificates_http_error_wrapped(self, certificate_client, mock_http):
        """Test that HTTP errors (non-404) are wrapped in DestinationOperationError."""
        # Setup
        http_error = HttpError("Internal Server Error")
        http_error.status_code = 500
        mock_http.get.side_effect = http_error

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        
        assert "failed to list instance certificates" in str(exc_info.value)

    def test_list_instance_certificates_invalid_json_wrapped(self, certificate_client, mock_http):
        """Test that invalid JSON responses are wrapped properly."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = mock_response

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        
        assert "invalid JSON in list certificates response" in str(exc_info.value)

    def test_list_subaccount_certificates_requires_tenant_for_subscriber_access(self, certificate_client, mock_http):
        """Test that subscriber access strategies require tenant parameter."""
        # Test SUBSCRIBER_ONLY
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided" in str(exc_info.value)

        # Test SUBSCRIBER_FIRST
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided" in str(exc_info.value)

    def test_list_subaccount_certificates_provider_only_no_tenant_required(self, certificate_client, mock_http):
        """Test PROVIDER_ONLY doesn't require tenant."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response

        # Execute (no tenant needed)
        certificates = certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_ONLY)

        # Verify
        assert len(certificates.items) == 1
        mock_http.get.assert_called_once_with("v1/subaccountCertificates", tenant_subdomain=None, params={})

    def test_list_subaccount_certificates_subscriber_only_with_tenant(self, certificate_client, mock_http):
        """Test SUBSCRIBER_ONLY with tenant."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY, 
            tenant="test-tenant"
        )

        # Verify
        assert len(certificates.items) == 1
        mock_http.get.assert_called_once_with("v1/subaccountCertificates", tenant_subdomain="test-tenant", params={})

    def test_list_subaccount_certificates_subscriber_first_no_fallback(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST when subscriber returns certificates (no fallback needed)."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST, 
            tenant="test-tenant"
        )

        # Verify - should only call subscriber, not provider
        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 1
        mock_http.get.assert_called_with("v1/subaccountCertificates", tenant_subdomain="test-tenant", params={})

    def test_list_subaccount_certificates_subscriber_first_fallback_to_provider(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST falls back to provider when subscriber returns empty list."""
        # Setup - subscriber returns empty, provider returns certificates
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        provider_response = Mock(spec=Response)
        provider_response.headers = {}
        provider_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        
        mock_http.get.side_effect = [empty_response, provider_response]

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST, 
            tenant="test-tenant"
        )

        # Verify - should call both subscriber then provider
        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 2
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountCertificates",), {"tenant_subdomain": "test-tenant", "params": {}})
        assert calls[1] == (("v1/subaccountCertificates",), {"tenant_subdomain": None, "params": {}})

    def test_list_subaccount_certificates_provider_first_no_fallback(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST when provider returns certificates (no fallback needed)."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.PROVIDER_FIRST, 
            tenant="test-tenant"
        )

        # Verify - should only call provider, not subscriber
        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 1
        mock_http.get.assert_called_with("v1/subaccountCertificates", tenant_subdomain=None, params={})

    def test_list_subaccount_certificates_provider_first_fallback_to_subscriber(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST falls back to subscriber when provider returns empty list."""
        # Setup - provider returns empty, subscriber returns certificates
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        subscriber_response = Mock(spec=Response)
        subscriber_response.headers = {}
        subscriber_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        
        mock_http.get.side_effect = [empty_response, subscriber_response]

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.PROVIDER_FIRST, 
            tenant="test-tenant"
        )

        # Verify - should call both provider then subscriber
        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 2
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountCertificates",), {"tenant_subdomain": None, "params": {}})
        assert calls[1] == (("v1/subaccountCertificates",), {"tenant_subdomain": "test-tenant", "params": {}})

    def test_list_subaccount_certificates_with_filter(self, certificate_client, mock_http):
        """Test listing subaccount certificates with filter."""
        # Setup
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        filter_obj = ListOptions(filter_names=["cert1.pem"])

        # Execute
        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.PROVIDER_ONLY,
            filter=filter_obj
        )

        # Verify
        assert len(certificates.items) == 1
        call_args = mock_http.get.call_args
        assert "params" in call_args[1]
        assert "$filter" in call_args[1]["params"]

    def test_list_subaccount_certificates_http_error_wrapped(self, certificate_client, mock_http):
        """Test that HTTP errors are wrapped in DestinationOperationError."""
        # Setup
        http_error = HttpError("Internal Server Error")
        http_error.status_code = 500
        mock_http.get.side_effect = http_error

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_subaccount_certificates(access_strategy=AccessStrategy.PROVIDER_ONLY)
        
        assert "failed to list subaccount certificates" in str(exc_info.value)


class TestCertificateClientAccessStrategy:
    """Tests for CertificateClient access strategy helper."""

    def test_apply_access_strategy_subscriber_only(self, certificate_client, mock_http):
        """Test _apply_access_strategy with SUBSCRIBER_ONLY."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        mock_http.get.assert_called_once_with("v1/subaccountCertificates", tenant_subdomain="test-tenant", params={})

    def test_apply_access_strategy_provider_only(self, certificate_client, mock_http):
        """Test _apply_access_strategy with PROVIDER_ONLY."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_ONLY,
            tenant=None,
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        mock_http.get.assert_called_once_with("v1/subaccountCertificates", tenant_subdomain=None, params={})

    def test_apply_access_strategy_subscriber_first_no_fallback(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST when subscriber has certificates (no fallback)."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 1

    def test_apply_access_strategy_subscriber_first_with_fallback(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST falls back to provider when subscriber is empty."""
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        provider_response = Mock(spec=Response)
        provider_response.headers = {}
        provider_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        
        mock_http.get.side_effect = [empty_response, provider_response]

        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 2

    def test_apply_access_strategy_provider_first_no_fallback(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST when provider has certificates (no fallback)."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        mock_http.get.return_value = mock_response
        
        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 1

    def test_apply_access_strategy_provider_first_with_fallback(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST falls back to subscriber when provider is empty."""
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        subscriber_response = Mock(spec=Response)
        subscriber_response.headers = {}
        subscriber_response.json.return_value = [{"Name": "cert1.pem", "Content": "content1"}]
        
        mock_http.get.side_effect = [empty_response, subscriber_response]

        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        assert len(certificates.items) == 1
        assert mock_http.get.call_count == 2

    def test_apply_access_strategy_with_list_empty_value(self, certificate_client, mock_http):
        """Test that empty lists from fallback scenarios work correctly."""
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        
        mock_http.get.return_value = empty_response

        certificates = certificate_client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
            fetch_func=lambda t: certificate_client._list_certificates(
                level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
            )
        )

        # Both subscriber and provider return empty, final result is empty
        assert certificates == PagedResult(items=[])
        assert mock_http.get.call_count == 2


class TestCertificateClientEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_subaccount_certificate_unknown_access_strategy(self, certificate_client, mock_http):
        """Test that unknown access strategy raises appropriate error."""
        # Create an invalid access strategy by mocking
        from unittest.mock import patch
        
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {"Name": "cert1.pem", "Content": "content1"}
        mock_http.get.return_value = mock_response
        
        # Patch AccessStrategy to add an unknown value
        with patch('cloud_sdk_python.destination.certificate_client.AccessStrategy') as mock_strategy:
            unknown_strategy = Mock()
            unknown_strategy.value = "UNKNOWN_STRATEGY"
            
            with pytest.raises(DestinationOperationError) as exc_info:
                # Directly call with a value that won't match any case
                certificate_client.get_subaccount_certificate(
                    "test-cert",
                    access_strategy=unknown_strategy,
                    tenant="test-tenant"
                )
            
            assert "unknown access strategy" in str(exc_info.value).lower()

    def test_create_certificate_unexpected_exception(self, certificate_client, mock_http):
        """Test create certificate with unexpected exception (not HttpError)."""
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.post.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.create_certificate(certificate)
        
        assert "failed to create certificate 'test-cert.pem'" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)

    def test_update_certificate_unexpected_exception(self, certificate_client, mock_http):
        """Test update certificate with unexpected exception (not HttpError)."""
        certificate = Certificate(name="test-cert.pem", content="content")
        mock_http.put.side_effect = ValueError("Unexpected error")

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.update_certificate(certificate)
        
        assert "failed to update certificate 'test-cert.pem'" in str(exc_info.value)

    def test_delete_certificate_unexpected_exception(self, certificate_client, mock_http):
        """Test delete certificate with unexpected exception (not HttpError)."""
        mock_http.delete.side_effect = ConnectionError("Network error")

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.delete_certificate("test-cert.pem")
        
        assert "failed to delete certificate 'test-cert.pem'" in str(exc_info.value)

    def test_list_certificates_non_list_response(self, certificate_client, mock_http):
        """Test list certificates when response is not a list."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        mock_response.json.return_value = {"error": "not a list"}
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        
        assert "expected JSON array in list certificates response" in str(exc_info.value)

    def test_list_certificates_404_returns_none(self, certificate_client, mock_http):
        """Test that 404 on list operations returns empty list."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        certificates = certificate_client.list_instance_certificates()
        
        assert certificates is None

    def test_list_subaccount_certificates_both_empty_subscriber_first(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return empty."""
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        mock_http.get.return_value = empty_response

        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert certificates == PagedResult(items=[])
        assert mock_http.get.call_count == 2

    def test_list_subaccount_certificates_both_empty_provider_first(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST when both provider and subscriber return empty."""
        empty_response = Mock(spec=Response)
        empty_response.headers = {}
        empty_response.json.return_value = []
        mock_http.get.return_value = empty_response

        certificates = certificate_client.list_subaccount_certificates(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        assert certificates == PagedResult(items=[])
        assert mock_http.get.call_count == 2

    def test_get_certificate_malformed_certificate_data(self, certificate_client, mock_http):
        """Test get certificate with malformed Certificate data in response."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        # Missing required fields for Certificate.from_dict
        mock_response.json.return_value = {"Name": "", "Content": ""}
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert")
        
        assert "invalid JSON in get certificate response" in str(exc_info.value)

    def test_list_certificates_invalid_certificate_in_array(self, certificate_client, mock_http):
        """Test list certificates with invalid certificate object in array."""
        mock_response = Mock(spec=Response)
        mock_response.headers = {}
        # One valid, one invalid certificate
        mock_response.json.return_value = [
            {"Name": "cert1.pem", "Content": "content1"},
            {"Name": "", "Content": ""}  # Invalid - will cause from_dict to fail
        ]
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()

        # The error message includes the specific validation error from Certificate.from_dict
        assert "certificate is missing required fields" in str(exc_info.value)

    def test_apply_access_strategy_unknown_strategy(self, certificate_client, mock_http):
        """Test _apply_access_strategy with unknown strategy."""
        from unittest.mock import Mock as MockStrategy
        
        unknown_strategy = MockStrategy()
        unknown_strategy.value = "UNKNOWN"
        
        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client._apply_access_strategy(
                access_strategy=unknown_strategy,
                tenant="test-tenant",
                fetch_func=lambda t: certificate_client._list_certificates(
                    level=Level.SUB_ACCOUNT, tenant_subdomain=t, filter=None
                )
            )
        
        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_get_subaccount_certificate_provider_first_both_none(self, certificate_client, mock_http):
        """Test PROVIDER_FIRST when both provider and subscriber return None."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        certificate = certificate_client.get_subaccount_certificate(
            "test-cert",
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        assert certificate is None
        assert mock_http.get.call_count == 2

    def test_get_subaccount_certificate_subscriber_first_both_none(self, certificate_client, mock_http):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return None."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        certificate = certificate_client.get_subaccount_certificate(
            "test-cert",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert certificate is None
        assert mock_http.get.call_count == 2

    def test_list_certificates_with_http_403_error(self, certificate_client, mock_http):
        """Test list certificates with 403 Forbidden error."""
        http_error = HttpError("Forbidden")
        http_error.status_code = 403
        mock_http.get.side_effect = http_error

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.list_instance_certificates()
        
        assert "failed to list instance certificates" in str(exc_info.value)

    def test_get_certificate_with_http_401_error(self, certificate_client, mock_http):
        """Test get certificate with 401 Unauthorized error."""
        http_error = HttpError("Unauthorized")
        http_error.status_code = 401
        mock_http.get.side_effect = http_error

        with pytest.raises(DestinationOperationError) as exc_info:
            certificate_client.get_instance_certificate("test-cert")
        
        assert "failed to get certificate 'test-cert'" in str(exc_info.value)
