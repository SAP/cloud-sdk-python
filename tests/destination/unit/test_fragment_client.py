"""Unit tests for FragmentClient."""

import pytest
from unittest.mock import Mock, MagicMock
from requests import Response

from sap_cloud_sdk.destination.fragment_client import FragmentClient
from sap_cloud_sdk.destination._models import AccessStrategy, Fragment, Label, Level, PatchLabels
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)


@pytest.fixture
def mock_http():
    """Create a mock DestinationHttp instance."""
    return Mock()


@pytest.fixture
def fragment_client(mock_http):
    """Create a FragmentClient with mocked HTTP."""
    return FragmentClient(http=mock_http)


class TestFragmentClientInit:
    """Tests for FragmentClient initialization."""

    def test_init_with_http(self, mock_http):
        """Test FragmentClient initialization with HTTP transport."""
        client = FragmentClient(http=mock_http)
        assert client._http is mock_http


class TestFragmentClientRead:
    """Tests for FragmentClient read operations."""

    def test_get_instance_fragment_success(self, fragment_client, mock_http):
        """Test successful retrieval of instance fragment."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "FragmentName": "test-fragment",
            "URL": "https://api.example.com",
            "Authentication": "OAuth2ClientCredentials"
        }
        mock_http.get.return_value = mock_response

        # Execute
        fragment = fragment_client.get_instance_fragment("test-fragment")

        # Verify
        assert fragment is not None
        assert fragment.name == "test-fragment"
        assert fragment.properties["URL"] == "https://api.example.com"
        assert fragment.properties["Authentication"] == "OAuth2ClientCredentials"
        mock_http.get.assert_called_once_with("v1/instanceDestinationFragments/test-fragment", tenant_subdomain=None)

    def test_get_subaccount_fragment_success(self, fragment_client, mock_http):
        """Test successful retrieval of subaccount fragment."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "FragmentName": "test-fragment",
            "ProxyType": "Internet"
        }
        mock_http.get.return_value = mock_response

        # Execute
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_ONLY)

        # Verify
        assert fragment is not None
        assert fragment.name == "test-fragment"
        assert fragment.properties["ProxyType"] == "Internet"
        mock_http.get.assert_called_once_with("v1/subaccountDestinationFragments/test-fragment", tenant_subdomain=None)

    def test_get_fragment_not_found(self, fragment_client, mock_http):
        """Test fragment retrieval when fragment doesn't exist (404)."""
        # Setup mock to raise 404
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        # Execute
        fragment = fragment_client.get_instance_fragment("nonexistent")

        # Verify
        assert fragment is None

    def test_get_fragment_http_error(self, fragment_client, mock_http):
        """Test fragment retrieval with HTTP error (non-404)."""
        # Setup mock to raise 500
        http_error = HttpError("Internal Server Error")
        http_error.status_code = 500
        mock_http.get.side_effect = http_error

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")

        assert "failed to get fragment 'test-fragment'" in str(exc_info.value)

    def test_get_fragment_invalid_json(self, fragment_client, mock_http):
        """Test fragment retrieval with invalid JSON response."""
        # Setup mock response with invalid JSON
        mock_response = Mock(spec=Response)
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = mock_response

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")

        assert "invalid JSON in get fragment response" in str(exc_info.value)

    def test_get_subaccount_fragment_access_strategies(self, fragment_client, mock_http):
        """Test subaccount fragment retrieval with different access strategies."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "FragmentName": "test-fragment",
            "ProxyType": "Internet"
        }
        mock_http.get.return_value = mock_response

        # Test PROVIDER_ONLY
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert fragment is not None
        mock_http.get.assert_called_with("v1/subaccountDestinationFragments/test-fragment", tenant_subdomain=None)

        # Reset mock
        mock_http.reset_mock()

        # Test SUBSCRIBER_ONLY with tenant
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert fragment is not None
        mock_http.get.assert_called_with("v1/subaccountDestinationFragments/test-fragment", tenant_subdomain="test-tenant")

    def test_get_subaccount_fragment_requires_tenant_for_subscriber_access(self, fragment_client, mock_http):
        """Test that subscriber access strategies require tenant parameter."""
        # Test SUBSCRIBER_ONLY without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test SUBSCRIBER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test PROVIDER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_get_subaccount_fragment_fallback_strategies(self, fragment_client, mock_http):
        """Test fallback behavior for SUBSCRIBER_FIRST and PROVIDER_FIRST strategies."""
        # Setup mock to return None for first call, fragment for second call
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {
            "FragmentName": "test-fragment",
            "ProxyType": "Internet"
        }

        # Test SUBSCRIBER_FIRST fallback (subscriber fails, provider succeeds)
        mock_http.get.side_effect = [
            HttpError("Not Found", status_code=404),  # Subscriber call fails
            mock_response  # Provider call succeeds
        ]

        fragment = fragment_client.get_subaccount_fragment(
            "test-fragment",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )
        assert fragment is not None
        assert mock_http.get.call_count == 2

        # Verify calls were made in correct order
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountDestinationFragments/test-fragment",), {"tenant_subdomain": "test-tenant"})
        assert calls[1] == (("v1/subaccountDestinationFragments/test-fragment",), {"tenant_subdomain": None})


class TestFragmentClientWrite:
    """Tests for FragmentClient write operations."""

    def test_create_fragment_subaccount(self, fragment_client, mock_http):
        """Test creating a fragment at subaccount level."""
        # Setup
        fragment = Fragment(
            name="new-fragment",
            properties={"URL": "https://api.example.com"}
        )

        # Execute
        fragment_client.create_fragment(fragment, level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "v1/subaccountDestinationFragments"
        assert call_args[1]["body"]["FragmentName"] == "new-fragment"
        assert call_args[1]["body"]["URL"] == "https://api.example.com"

    def test_create_fragment_instance(self, fragment_client, mock_http):
        """Test creating a fragment at instance level."""
        # Setup
        fragment = Fragment(
            name="new-fragment",
            properties={"ProxyType": "Internet"}
        )

        # Execute
        fragment_client.create_fragment(fragment, level=Level.SERVICE_INSTANCE)

        # Verify
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "v1/instanceDestinationFragments"

    def test_create_fragment_with_tenant(self, fragment_client, mock_http):
        """Test creating a fragment with a subscriber tenant."""
        fragment = Fragment(name="new-fragment", properties={"URL": "https://api.example.com"})

        fragment_client.create_fragment(fragment, level=Level.SUB_ACCOUNT, tenant="test-tenant")

        call_args = mock_http.post.call_args
        assert call_args[1]["tenant_subdomain"] == "test-tenant"

    def test_create_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        """Test creating a fragment without tenant uses provider context (tenant_subdomain=None)."""
        fragment = Fragment(name="new-fragment", properties={})

        fragment_client.create_fragment(fragment)

        call_args = mock_http.post.call_args
        assert call_args[1]["tenant_subdomain"] is None

    def test_create_fragment_http_error(self, fragment_client, mock_http):
        """Test create fragment with HTTP error."""
        # Setup
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.post.side_effect = HttpError("Conflict")

        # Execute & Verify
        with pytest.raises(HttpError):
            fragment_client.create_fragment(fragment)

    def test_update_fragment_success(self, fragment_client, mock_http):
        """Test updating a fragment."""
        # Setup
        fragment = Fragment(
            name="existing-fragment",
            properties={"URL": "https://updated.example.com"}
        )

        # Execute
        fragment_client.update_fragment(fragment, level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.put.assert_called_once()
        call_args = mock_http.put.call_args
        assert call_args[0][0] == "v1/subaccountDestinationFragments"
        assert call_args[1]["body"]["FragmentName"] == "existing-fragment"

    def test_update_fragment_with_tenant(self, fragment_client, mock_http):
        """Test updating a fragment with a subscriber tenant."""
        fragment = Fragment(name="existing-fragment", properties={"URL": "https://updated.example.com"})

        fragment_client.update_fragment(fragment, level=Level.SUB_ACCOUNT, tenant="test-tenant")

        call_args = mock_http.put.call_args
        assert call_args[1]["tenant_subdomain"] == "test-tenant"

    def test_update_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        """Test updating a fragment without tenant uses provider context (tenant_subdomain=None)."""
        fragment = Fragment(name="existing-fragment", properties={})

        fragment_client.update_fragment(fragment)

        call_args = mock_http.put.call_args
        assert call_args[1]["tenant_subdomain"] is None

    def test_update_fragment_http_error(self, fragment_client, mock_http):
        """Test update fragment with HTTP error."""
        # Setup
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.put.side_effect = HttpError("Not Found")

        # Execute & Verify
        with pytest.raises(HttpError):
            fragment_client.update_fragment(fragment)

    def test_delete_fragment_with_tenant(self, fragment_client, mock_http):
        """Test deleting a fragment with a subscriber tenant."""
        fragment_client.delete_fragment("test-fragment", level=Level.SUB_ACCOUNT, tenant="test-tenant")

        mock_http.delete.assert_called_once_with(
            "v1/subaccountDestinationFragments/test-fragment", tenant_subdomain="test-tenant"
        )

    def test_delete_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        """Test deleting a fragment without tenant uses provider context (tenant_subdomain=None)."""
        fragment_client.delete_fragment("test-fragment")

        mock_http.delete.assert_called_once_with(
            "v1/subaccountDestinationFragments/test-fragment", tenant_subdomain=None
        )

    def test_delete_fragment_success(self, fragment_client, mock_http):
        """Test deleting a fragment."""
        # Execute
        fragment_client.delete_fragment("test-fragment", level=Level.SUB_ACCOUNT)

        # Verify
        mock_http.delete.assert_called_once_with(
            "v1/subaccountDestinationFragments/test-fragment", tenant_subdomain=None
        )

    def test_delete_fragment_instance_level(self, fragment_client, mock_http):
        """Test deleting a fragment at instance level."""
        # Execute
        fragment_client.delete_fragment("test-fragment", level=Level.SERVICE_INSTANCE)

        # Verify
        mock_http.delete.assert_called_once_with(
            "v1/instanceDestinationFragments/test-fragment", tenant_subdomain=None
        )

    def test_delete_fragment_http_error(self, fragment_client, mock_http):
        """Test delete fragment with HTTP error."""
        # Setup
        mock_http.delete.side_effect = HttpError("Not Found")

        # Execute & Verify
        with pytest.raises(HttpError):
            fragment_client.delete_fragment("test-fragment")


class TestFragmentClientHelpers:
    """Tests for FragmentClient helper methods."""

    def test_sub_path_for_level_instance(self):
        """Test sub-path generation for instance level."""
        path = FragmentClient._sub_path_for_level(Level.SERVICE_INSTANCE)
        assert path == "instanceDestinationFragments"

    def test_sub_path_for_level_subaccount(self):
        """Test sub-path generation for subaccount level."""
        path = FragmentClient._sub_path_for_level(Level.SUB_ACCOUNT)
        assert path == "subaccountDestinationFragments"


class TestFragmentClientListOperations:
    """Tests for FragmentClient list operations."""

    def test_list_instance_fragments_success(self, fragment_client, mock_http):
        """Test successful listing of instance fragments."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"},
            {"FragmentName": "frag2", "ProxyType": "Internet"}
        ]
        mock_http.get.return_value = mock_response

        # Execute
        fragments = fragment_client.list_instance_fragments()

        # Verify
        assert len(fragments) == 2
        assert fragments[0].name == "frag1"
        assert fragments[0].properties["URL"] == "https://api1.example.com"
        assert fragments[1].name == "frag2"
        assert fragments[1].properties["ProxyType"] == "Internet"
        mock_http.get.assert_called_once_with("v1/instanceDestinationFragments", tenant_subdomain=None, params={})

    def test_list_instance_fragments_empty(self, fragment_client, mock_http):
        """Test listing instance fragments when none exist."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = []
        mock_http.get.return_value = mock_response

        # Execute
        fragments = fragment_client.list_instance_fragments()

        # Verify
        assert fragments == []
        mock_http.get.assert_called_once()

    def test_list_instance_fragments_http_error(self, fragment_client, mock_http):
        """Test listing instance fragments with HTTP error."""
        # Setup mock to raise error
        mock_http.get.side_effect = HttpError("Internal Server Error")

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        assert "failed to list instance fragments" in str(exc_info.value)

    def test_list_instance_fragments_invalid_json(self, fragment_client, mock_http):
        """Test listing instance fragments with invalid JSON response."""
        # Setup mock response with invalid format (not a list)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"error": "not a list"}
        mock_http.get.return_value = mock_response

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        assert "expected list in response" in str(exc_info.value)

    def test_list_subaccount_fragments_provider_only(self, fragment_client, mock_http):
        """Test listing subaccount fragments with PROVIDER_ONLY strategy."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"}
        ]
        mock_http.get.return_value = mock_response

        # Execute
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_ONLY)

        # Verify
        assert len(fragments) == 1
        assert fragments[0].name == "frag1"
        mock_http.get.assert_called_once_with("v1/subaccountDestinationFragments", tenant_subdomain=None, params={})

    def test_list_subaccount_fragments_subscriber_only(self, fragment_client, mock_http):
        """Test listing subaccount fragments with SUBSCRIBER_ONLY strategy."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"}
        ]
        mock_http.get.return_value = mock_response

        # Execute
        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
            tenant="test-tenant"
        )

        # Verify
        assert len(fragments) == 1
        mock_http.get.assert_called_once_with("v1/subaccountDestinationFragments", tenant_subdomain="test-tenant", params={})

    def test_list_subaccount_fragments_requires_tenant(self, fragment_client, mock_http):
        """Test that subscriber access strategies require tenant parameter."""
        # Test SUBSCRIBER_ONLY without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test SUBSCRIBER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        # Test PROVIDER_FIRST without tenant
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_list_subaccount_fragments_subscriber_first_fallback(self, fragment_client, mock_http):
        """Test SUBSCRIBER_FIRST strategy with fallback to provider."""
        # Setup mock: subscriber returns empty, provider returns data
        mock_response_empty = Mock(spec=Response)
        mock_response_empty.json.return_value = []

        mock_response_data = Mock(spec=Response)
        mock_response_data.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"}
        ]

        mock_http.get.side_effect = [mock_response_empty, mock_response_data]

        # Execute
        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        # Verify
        assert len(fragments) == 1
        assert fragments[0].name == "frag1"
        assert mock_http.get.call_count == 2

        # Verify calls were made in correct order
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountDestinationFragments",), {"tenant_subdomain": "test-tenant", "params": {}})
        assert calls[1] == (("v1/subaccountDestinationFragments",), {"tenant_subdomain": None, "params": {}})

    def test_list_subaccount_fragments_provider_first_fallback(self, fragment_client, mock_http):
        """Test PROVIDER_FIRST strategy with fallback to subscriber."""
        # Setup mock: provider returns empty, subscriber returns data
        mock_response_empty = Mock(spec=Response)
        mock_response_empty.json.return_value = []

        mock_response_data = Mock(spec=Response)
        mock_response_data.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"}
        ]

        mock_http.get.side_effect = [mock_response_empty, mock_response_data]

        # Execute
        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        # Verify
        assert len(fragments) == 1
        assert mock_http.get.call_count == 2

        # Verify calls were made in correct order
        calls = mock_http.get.call_args_list
        assert calls[0] == (("v1/subaccountDestinationFragments",), {"tenant_subdomain": None, "params": {}})
        assert calls[1] == (("v1/subaccountDestinationFragments",), {"tenant_subdomain": "test-tenant", "params": {}})

    def test_list_subaccount_fragments_http_error(self, fragment_client, mock_http):
        """Test listing subaccount fragments with HTTP error."""
        # Setup mock to raise error
        mock_http.get.side_effect = HttpError("Internal Server Error")

        # Execute & Verify
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_ONLY)

        assert "failed to list subaccount fragments" in str(exc_info.value)


class TestFragmentClientAccessStrategy:
    """Tests for FragmentClient access strategy refactoring."""

    def test_get_subaccount_fragment_uses_strategy_pattern(self, fragment_client, mock_http):
        """Test that get_subaccount_fragment uses the new _apply_access_strategy method."""
        # Setup mock response
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"FragmentName": "test-frag", "URL": "https://api.example.com"}
        mock_http.get.return_value = mock_response

        # Execute
        fragment = fragment_client.get_subaccount_fragment(
            "test-frag",
            access_strategy=AccessStrategy.PROVIDER_ONLY
        )

        # Verify
        assert fragment is not None
        assert fragment.name == "test-frag"
        mock_http.get.assert_called_once()

    def test_get_subaccount_fragment_fallback_none_to_provider(self, fragment_client, mock_http):
        """Test get with SUBSCRIBER_FIRST when subscriber returns None, fallback to provider."""
        # Setup mock: subscriber returns 404 (None), provider returns fragment
        http_error = HttpError("Not Found")
        http_error.status_code = 404

        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"FragmentName": "test-frag", "URL": "https://api.example.com"}

        mock_http.get.side_effect = [http_error, mock_response]

        # Execute
        fragment = fragment_client.get_subaccount_fragment(
            "test-frag",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        # Verify
        assert fragment is not None
        assert fragment.name == "test-frag"
        assert mock_http.get.call_count == 2


class TestFragmentClientEdgeCases:
    """Tests for edge cases and error handling."""

    def test_create_fragment_unexpected_exception(self, fragment_client, mock_http):
        """Test create fragment with unexpected exception (not HttpError)."""
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.post.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.create_fragment(fragment)

        assert "failed to create fragment 'test-fragment'" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)

    def test_update_fragment_unexpected_exception(self, fragment_client, mock_http):
        """Test update fragment with unexpected exception (not HttpError)."""
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.put.side_effect = ValueError("Unexpected error")

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.update_fragment(fragment)

        assert "failed to update fragment 'test-fragment'" in str(exc_info.value)

    def test_delete_fragment_unexpected_exception(self, fragment_client, mock_http):
        """Test delete fragment with unexpected exception (not HttpError)."""
        mock_http.delete.side_effect = ConnectionError("Network error")

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.delete_fragment("test-fragment")

        assert "failed to delete fragment 'test-fragment'" in str(exc_info.value)

    def test_apply_access_strategy_unknown_strategy(self, fragment_client, mock_http):
        """Test _apply_access_strategy with unknown strategy."""
        from unittest.mock import Mock as MockStrategy

        unknown_strategy = MockStrategy()
        unknown_strategy.value = "UNKNOWN"

        def fetch_func(tenant):
            return None

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client._apply_access_strategy(
                access_strategy=unknown_strategy,
                tenant="test-tenant",
                fetch_func=fetch_func,
                empty_value=None
            )

        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_list_fragments_non_list_response_raises_specific_error(self, fragment_client, mock_http):
        """Test that _list_fragments raises DestinationOperationError for non-list response."""
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"error": "not a list"}
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        assert "expected list in response" in str(exc_info.value)

    def test_list_fragments_json_parsing_error(self, fragment_client, mock_http):
        """Test that JSON parsing errors are wrapped properly."""
        mock_response = Mock(spec=Response)
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        assert "invalid JSON in list fragments response" in str(exc_info.value)

    def test_get_fragment_malformed_fragment_data(self, fragment_client, mock_http):
        """Test get fragment with malformed Fragment data in response."""
        mock_response = Mock(spec=Response)
        # Missing required FragmentName field
        mock_response.json.return_value = {"URL": "https://api.example.com"}
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")

        assert "invalid JSON in get fragment response" in str(exc_info.value)

    def test_list_subaccount_fragments_both_empty_subscriber_first(self, fragment_client, mock_http):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return empty."""
        empty_response = Mock(spec=Response)
        empty_response.json.return_value = []
        mock_http.get.return_value = empty_response

        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert fragments == []
        assert mock_http.get.call_count == 2

    def test_list_subaccount_fragments_both_empty_provider_first(self, fragment_client, mock_http):
        """Test PROVIDER_FIRST when both provider and subscriber return empty."""
        empty_response = Mock(spec=Response)
        empty_response.json.return_value = []
        mock_http.get.return_value = empty_response

        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        assert fragments == []
        assert mock_http.get.call_count == 2

    def test_get_subaccount_fragment_provider_first_both_none(self, fragment_client, mock_http):
        """Test PROVIDER_FIRST when both provider and subscriber return None."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        fragment = fragment_client.get_subaccount_fragment(
            "test-fragment",
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        assert fragment is None
        assert mock_http.get.call_count == 2

    def test_get_subaccount_fragment_subscriber_first_both_none(self, fragment_client, mock_http):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return None."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404
        mock_http.get.side_effect = http_error

        fragment = fragment_client.get_subaccount_fragment(
            "test-fragment",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert fragment is None
        assert mock_http.get.call_count == 2

    def test_list_fragments_with_http_403_error(self, fragment_client, mock_http):
        """Test list fragments with 403 Forbidden error."""
        http_error = HttpError("Forbidden")
        http_error.status_code = 403
        mock_http.get.side_effect = http_error

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        assert "failed to list instance fragments" in str(exc_info.value)

    def test_get_fragment_with_http_401_error(self, fragment_client, mock_http):
        """Test get fragment with 401 Unauthorized error."""
        http_error = HttpError("Unauthorized")
        http_error.status_code = 401
        mock_http.get.side_effect = http_error

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")

        assert "failed to get fragment 'test-fragment'" in str(exc_info.value)

    def test_list_fragments_invalid_fragment_in_array(self, fragment_client, mock_http):
        """Test list fragments with invalid fragment object in array."""
        mock_response = Mock(spec=Response)
        # One valid, one invalid fragment
        mock_response.json.return_value = [
            {"FragmentName": "frag1", "URL": "https://api.example.com"},
            {"URL": "https://api2.example.com"}  # Invalid - missing FragmentName
        ]
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()

        # The error bubbles up from Fragment.from_dict but gets caught and wrapped
        assert "fragment is missing required field" in str(exc_info.value) or "invalid JSON in list fragments response" in str(exc_info.value)

    def test_apply_access_strategy_subscriber_first_no_fallback_with_data(self, fragment_client, mock_http):
        """Test SUBSCRIBER_FIRST when subscriber returns data (no fallback needed)."""
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [{"FragmentName": "frag1", "URL": "https://api.example.com"}]
        mock_http.get.return_value = mock_response

        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert len(fragments) == 1
        assert mock_http.get.call_count == 1  # No fallback to provider

    def test_apply_access_strategy_provider_first_no_fallback_with_data(self, fragment_client, mock_http):
        """Test PROVIDER_FIRST when provider returns data (no fallback needed)."""
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [{"FragmentName": "frag1", "URL": "https://api.example.com"}]
        mock_http.get.return_value = mock_response

        fragments = fragment_client.list_subaccount_fragments(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="test-tenant"
        )

        assert len(fragments) == 1
        assert mock_http.get.call_count == 1  # No fallback to subscriber

    def test_get_fragment_with_none_empty_value_equality(self, fragment_client, mock_http):
        """Test that None empty_value works correctly in access strategy."""
        http_error = HttpError("Not Found")
        http_error.status_code = 404

        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"FragmentName": "test-frag", "URL": "https://api.example.com"}

        # First call returns None (404), second returns fragment
        mock_http.get.side_effect = [http_error, mock_response]

        fragment = fragment_client.get_subaccount_fragment(
            "test-frag",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant"
        )

        assert fragment is not None
        assert fragment.name == "test-frag"
        # Verify fallback occurred
        assert mock_http.get.call_count == 2


class TestFragmentClientLabels:
    """Tests for FragmentClient label operations."""

    def test_get_fragment_labels_instance(self, fragment_client, mock_http):
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [{"key": "env", "values": ["prod"]}]
        mock_http.get.return_value = mock_response

        labels = fragment_client.get_fragment_labels("fragA", Level.SERVICE_INSTANCE)

        assert len(labels) == 1
        assert labels[0].key == "env"
        assert labels[0].values == ["prod"]
        mock_http.get.assert_called_once_with("v1/instanceDestinationFragments/fragA/labels", tenant_subdomain=None)

    def test_get_fragment_labels_subaccount(self, fragment_client, mock_http):
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [{"key": "team", "values": ["platform"]}]
        mock_http.get.return_value = mock_response

        labels = fragment_client.get_fragment_labels("fragA", Level.SUB_ACCOUNT)

        assert labels[0].key == "team"
        mock_http.get.assert_called_once_with("v1/subaccountDestinationFragments/fragA/labels", tenant_subdomain=None)

    def test_get_fragment_labels_default_level_is_subaccount(self, fragment_client, mock_http):
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = []
        mock_http.get.return_value = mock_response

        fragment_client.get_fragment_labels("fragA")

        mock_http.get.assert_called_once_with("v1/subaccountDestinationFragments/fragA/labels", tenant_subdomain=None)

    def test_get_fragment_labels_non_list_response_raises(self, fragment_client, mock_http):
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = {"key": "env", "values": ["prod"]}
        mock_http.get.return_value = mock_response

        with pytest.raises(DestinationOperationError):
            fragment_client.get_fragment_labels("fragA")

    def test_get_fragment_labels_http_error_raises_operation_error(self, fragment_client, mock_http):
        mock_http.get.side_effect = HttpError("Not Found", status_code=404, response_text="Not Found")

        with pytest.raises(DestinationOperationError, match="failed to get labels for fragment"):
            fragment_client.get_fragment_labels("fragA")

    def test_update_fragment_labels_instance(self, fragment_client, mock_http):
        labels = [Label(key="env", values=["prod"])]

        fragment_client.update_fragment_labels("fragA", labels, Level.SERVICE_INSTANCE)

        mock_http.put.assert_called_once_with(
            "v1/instanceDestinationFragments/fragA/labels",
            body=[{"key": "env", "values": ["prod"]}],
            tenant_subdomain=None,
        )

    def test_update_fragment_labels_subaccount(self, fragment_client, mock_http):
        labels = [Label(key="env", values=["staging"])]

        fragment_client.update_fragment_labels("fragA", labels, Level.SUB_ACCOUNT)

        mock_http.put.assert_called_once_with(
            "v1/subaccountDestinationFragments/fragA/labels",
            body=[{"key": "env", "values": ["staging"]}],
            tenant_subdomain=None,
        )

    def test_update_fragment_labels_http_error_propagates(self, fragment_client, mock_http):
        mock_http.put.side_effect = HttpError("Conflict", status_code=409, response_text="Conflict")

        with pytest.raises(HttpError):
            fragment_client.update_fragment_labels("fragA", [], Level.SUB_ACCOUNT)

    def test_patch_fragment_labels_instance(self, fragment_client, mock_http):
        patch = PatchLabels(action="ADD", labels=[Label(key="env", values=["prod"])])

        fragment_client.patch_fragment_labels("fragA", patch, Level.SERVICE_INSTANCE)

        mock_http.patch.assert_called_once_with(
            "v1/instanceDestinationFragments/fragA/labels",
            body={"action": "ADD", "labels": [{"key": "env", "values": ["prod"]}]},
            tenant_subdomain=None,
        )

    def test_patch_fragment_labels_subaccount(self, fragment_client, mock_http):
        patch = PatchLabels(action="DELETE", labels=[Label(key="env", values=[])])

        fragment_client.patch_fragment_labels("fragA", patch, Level.SUB_ACCOUNT)

        mock_http.patch.assert_called_once_with(
            "v1/subaccountDestinationFragments/fragA/labels",
            body={"action": "DELETE", "labels": [{"key": "env", "values": []}]},
            tenant_subdomain=None,
        )

    def test_patch_fragment_labels_http_error_propagates(self, fragment_client, mock_http):
        mock_http.patch.side_effect = HttpError("Not Found", status_code=404, response_text="Not Found")

        with pytest.raises(HttpError):
            fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]), Level.SUB_ACCOUNT)

    def test_get_fragment_labels_with_tenant(self, fragment_client, mock_http):
        mock_http.get.return_value.json.return_value = []

        fragment_client.get_fragment_labels("fragA", tenant="test-tenant")

        _, kwargs = mock_http.get.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        mock_http.get.return_value.json.return_value = []

        fragment_client.get_fragment_labels("fragA")

        _, kwargs = mock_http.get.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_fragment_labels_with_tenant(self, fragment_client, mock_http):
        fragment_client.update_fragment_labels("fragA", [], tenant="test-tenant")

        _, kwargs = mock_http.put.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment_client.update_fragment_labels("fragA", [])

        _, kwargs = mock_http.put.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_patch_fragment_labels_with_tenant(self, fragment_client, mock_http):
        fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]), tenant="test-tenant")

        _, kwargs = mock_http.patch.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_patch_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]))

        _, kwargs = mock_http.patch.call_args
        assert kwargs["tenant_subdomain"] is None
