"""Unit tests for FragmentClient."""

import pytest
from unittest.mock import Mock
from requests import Response

from sap_cloud_sdk.destination.fragment_client import FragmentClient
from sap_cloud_sdk.core._http_client import HttpMethod
from sap_cloud_sdk.destination._models import AccessStrategy, Fragment, Label, Level, PatchLabels
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
def fragment_client(mock_http):
    return FragmentClient(http=mock_http)


class TestFragmentClientInit:

    def test_init_with_http(self, mock_http):
        client = FragmentClient(http=mock_http)
        assert client._http is mock_http


class TestFragmentClientRead:

    def test_get_instance_fragment_success(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {
            "FragmentName": "test-fragment",
            "URL": "https://api.example.com",
            "Authentication": "OAuth2ClientCredentials",
        })
        fragment = fragment_client.get_instance_fragment("test-fragment")
        assert fragment is not None
        assert fragment.name == "test-fragment"
        assert fragment.properties["URL"] == "https://api.example.com"
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.GET
        assert args[1] == "/v1/instanceDestinationFragments/test-fragment"
        assert kwargs["tenant_subdomain"] is None

    def test_get_subaccount_fragment_success(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {
            "FragmentName": "test-fragment",
            "ProxyType": "Internet",
        })
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert fragment is not None
        assert fragment.properties["ProxyType"] == "Internet"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinationFragments/test-fragment"
        assert kwargs["tenant_subdomain"] is None

    def test_get_fragment_not_found(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        fragment = fragment_client.get_instance_fragment("nonexistent")
        assert fragment is None

    def test_get_fragment_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")
        assert "failed to get fragment 'test-fragment'" in str(exc_info.value)

    def test_get_fragment_invalid_json(self, fragment_client, mock_http):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")
        assert "invalid JSON in get fragment response" in str(exc_info.value)

    def test_get_subaccount_fragment_access_strategies(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"FragmentName": "test-fragment", "ProxyType": "Internet"})
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert fragment is not None
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

        mock_http.reset_mock()
        mock_http.request.return_value = _make_response(200, {"FragmentName": "test-fragment", "ProxyType": "Internet"})
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert fragment is not None
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_subaccount_fragment_requires_tenant_for_subscriber_access(self, fragment_client, mock_http):
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_get_subaccount_fragment_fallback_strategies(self, fragment_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(404, text="Not Found"),
            _make_response(200, {"FragmentName": "test-fragment", "ProxyType": "Internet"}),
        ]
        fragment = fragment_client.get_subaccount_fragment(
            "test-fragment",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
        )
        assert fragment is not None
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] == "test-tenant"
        assert calls[1][1]["tenant_subdomain"] is None


class TestFragmentClientWrite:

    def test_create_fragment_subaccount(self, fragment_client, mock_http):
        fragment = Fragment(name="new-fragment", properties={"URL": "https://api.example.com"})
        fragment_client.create_fragment(fragment, level=Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.POST
        assert args[1] == "/v1/subaccountDestinationFragments"
        assert kwargs["json"]["FragmentName"] == "new-fragment"
        assert kwargs["json"]["URL"] == "https://api.example.com"

    def test_create_fragment_instance(self, fragment_client, mock_http):
        fragment = Fragment(name="new-fragment", properties={"ProxyType": "Internet"})
        fragment_client.create_fragment(fragment, level=Level.SERVICE_INSTANCE)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinationFragments"

    def test_create_fragment_with_tenant(self, fragment_client, mock_http):
        fragment = Fragment(name="new-fragment", properties={"URL": "https://api.example.com"})
        fragment_client.create_fragment(fragment, level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_create_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment = Fragment(name="new-fragment", properties={})
        fragment_client.create_fragment(fragment)
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_create_fragment_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(409, text="Conflict")
        fragment = Fragment(name="test-fragment", properties={})
        with pytest.raises(HttpError):
            fragment_client.create_fragment(fragment)

    def test_update_fragment_success(self, fragment_client, mock_http):
        fragment = Fragment(name="existing-fragment", properties={"URL": "https://updated.example.com"})
        fragment_client.update_fragment(fragment, level=Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PUT
        assert args[1] == "/v1/subaccountDestinationFragments"
        assert kwargs["json"]["FragmentName"] == "existing-fragment"

    def test_update_fragment_with_tenant(self, fragment_client, mock_http):
        fragment = Fragment(name="existing-fragment", properties={"URL": "https://updated.example.com"})
        fragment_client.update_fragment(fragment, level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment = Fragment(name="existing-fragment", properties={})
        fragment_client.update_fragment(fragment)
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_fragment_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        fragment = Fragment(name="test-fragment", properties={})
        with pytest.raises(HttpError):
            fragment_client.update_fragment(fragment)

    def test_delete_fragment_with_tenant(self, fragment_client, mock_http):
        fragment_client.delete_fragment("test-fragment", level=Level.SUB_ACCOUNT, tenant="test-tenant")
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.DELETE
        assert args[1] == "/v1/subaccountDestinationFragments/test-fragment"
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_delete_fragment_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment_client.delete_fragment("test-fragment")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_delete_fragment_success(self, fragment_client, mock_http):
        fragment_client.delete_fragment("test-fragment", level=Level.SUB_ACCOUNT)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinationFragments/test-fragment"

    def test_delete_fragment_instance_level(self, fragment_client, mock_http):
        fragment_client.delete_fragment("test-fragment", level=Level.SERVICE_INSTANCE)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinationFragments/test-fragment"

    def test_delete_fragment_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            fragment_client.delete_fragment("test-fragment")


class TestFragmentClientHelpers:

    def test_sub_path_for_level_instance(self):
        path = FragmentClient._sub_path_for_level(Level.SERVICE_INSTANCE)
        assert path == "instanceDestinationFragments"

    def test_sub_path_for_level_subaccount(self):
        path = FragmentClient._sub_path_for_level(Level.SUB_ACCOUNT)
        assert path == "subaccountDestinationFragments"


class TestFragmentClientListOperations:

    def test_list_instance_fragments_success(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [
            {"FragmentName": "frag1", "URL": "https://api1.example.com"},
            {"FragmentName": "frag2", "ProxyType": "Internet"},
        ])
        fragments = fragment_client.list_instance_fragments()
        assert len(fragments) == 2
        assert fragments[0].name == "frag1"
        assert fragments[1].name == "frag2"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinationFragments"
        assert kwargs["tenant_subdomain"] is None

    def test_list_instance_fragments_empty(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragments = fragment_client.list_instance_fragments()
        assert fragments == []

    def test_list_instance_fragments_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "failed to list instance fragments" in str(exc_info.value)

    def test_list_instance_fragments_invalid_json(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"error": "not a list"})
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "expected list in response" in str(exc_info.value)

    def test_list_instance_fragments_with_tenant(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"FragmentName": "frag1", "URL": "https://api1.example.com"}])
        fragments = fragment_client.list_instance_fragments(tenant="my-tenant")
        assert len(fragments) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "my-tenant"

    def test_list_subaccount_fragments_provider_only(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"FragmentName": "frag1", "URL": "https://api1.example.com"}])
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert len(fragments) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_list_subaccount_fragments_subscriber_only(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"FragmentName": "frag1", "URL": "https://api1.example.com"}])
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant")
        assert len(fragments) == 1
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_list_subaccount_fragments_requires_tenant(self, fragment_client, mock_http):
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_ONLY)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_FIRST)
        assert "tenant subdomain must be provided for subscriber access" in str(exc_info.value)

    def test_list_subaccount_fragments_subscriber_first_fallback(self, fragment_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(200, []),
            _make_response(200, [{"FragmentName": "frag1", "URL": "https://api1.example.com"}]),
        ]
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert len(fragments) == 1
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] == "test-tenant"
        assert calls[1][1]["tenant_subdomain"] is None

    def test_list_subaccount_fragments_provider_first_fallback(self, fragment_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(200, []),
            _make_response(200, [{"FragmentName": "frag1", "URL": "https://api1.example.com"}]),
        ]
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert len(fragments) == 1
        assert mock_http.request.call_count == 2
        calls = mock_http.request.call_args_list
        assert calls[0][1]["tenant_subdomain"] is None
        assert calls[1][1]["tenant_subdomain"] == "test-tenant"

    def test_list_subaccount_fragments_http_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(500, text="Internal Server Error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_ONLY)
        assert "failed to list subaccount fragments" in str(exc_info.value)


class TestFragmentClientEdgeCases:

    def test_create_fragment_unexpected_exception(self, fragment_client, mock_http):
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.request.side_effect = RuntimeError("Unexpected error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.create_fragment(fragment)
        assert "failed to create fragment 'test-fragment'" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)

    def test_update_fragment_unexpected_exception(self, fragment_client, mock_http):
        fragment = Fragment(name="test-fragment", properties={})
        mock_http.request.side_effect = ValueError("Unexpected error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.update_fragment(fragment)
        assert "failed to update fragment 'test-fragment'" in str(exc_info.value)

    def test_delete_fragment_unexpected_exception(self, fragment_client, mock_http):
        mock_http.request.side_effect = ConnectionError("Network error")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.delete_fragment("test-fragment")
        assert "failed to delete fragment 'test-fragment'" in str(exc_info.value)

    def test_apply_access_strategy_unknown_strategy(self, fragment_client, mock_http):
        unknown_strategy = Mock()
        unknown_strategy.value = "UNKNOWN"
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client._apply_access_strategy(
                access_strategy=unknown_strategy,
                tenant="test-tenant",
                fetch_func=lambda t: None,
                empty_value=None,
            )
        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_list_fragments_non_list_response_raises_specific_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"error": "not a list"})
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "expected list in response" in str(exc_info.value)

    def test_list_fragments_json_parsing_error(self, fragment_client, mock_http):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "invalid JSON in list fragments response" in str(exc_info.value)

    def test_get_fragment_malformed_fragment_data(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"URL": "https://api.example.com"})
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")
        assert "invalid JSON in get fragment response" in str(exc_info.value)

    def test_list_subaccount_fragments_both_empty_subscriber_first(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert fragments == []
        assert mock_http.request.call_count == 2

    def test_list_subaccount_fragments_both_empty_provider_first(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragments = fragment_client.list_subaccount_fragments(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert fragments == []
        assert mock_http.request.call_count == 2

    def test_get_subaccount_fragment_provider_first_both_none(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
        assert fragment is None
        assert mock_http.request.call_count == 2

    def test_get_subaccount_fragment_subscriber_first_both_none(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        fragment = fragment_client.get_subaccount_fragment("test-fragment", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert fragment is None
        assert mock_http.request.call_count == 2

    def test_list_fragments_with_http_403_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(403, text="Forbidden")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "failed to list instance fragments" in str(exc_info.value)

    def test_get_fragment_with_http_401_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(401, text="Unauthorized")
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.get_instance_fragment("test-fragment")
        assert "failed to get fragment 'test-fragment'" in str(exc_info.value)

    def test_list_fragments_invalid_fragment_in_array(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [
            {"FragmentName": "frag1", "URL": "https://api.example.com"},
            {"URL": "https://api2.example.com"},
        ])
        with pytest.raises(DestinationOperationError) as exc_info:
            fragment_client.list_instance_fragments()
        assert "fragment is missing required field" in str(exc_info.value) or "invalid JSON in list fragments response" in str(exc_info.value)

    def test_get_subaccount_fragment_fallback_none_to_provider(self, fragment_client, mock_http):
        mock_http.request.side_effect = [
            _make_response(404, text="Not Found"),
            _make_response(200, {"FragmentName": "test-frag", "URL": "https://api.example.com"}),
        ]
        fragment = fragment_client.get_subaccount_fragment("test-frag", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
        assert fragment is not None
        assert fragment.name == "test-frag"
        assert mock_http.request.call_count == 2


class TestFragmentClientLabels:

    def test_get_fragment_labels_instance(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"key": "env", "values": ["prod"]}])
        labels = fragment_client.get_fragment_labels("fragA", Level.SERVICE_INSTANCE)
        assert len(labels) == 1
        assert labels[0].key == "env"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinationFragments/fragA/labels"
        assert kwargs["tenant_subdomain"] is None

    def test_get_fragment_labels_subaccount(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [{"key": "team", "values": ["platform"]}])
        labels = fragment_client.get_fragment_labels("fragA", Level.SUB_ACCOUNT)
        assert labels[0].key == "team"
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinationFragments/fragA/labels"

    def test_get_fragment_labels_default_level_is_subaccount(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragment_client.get_fragment_labels("fragA")
        args, _ = mock_http.request.call_args
        assert "subaccountDestinationFragments" in args[1]

    def test_get_fragment_labels_non_list_response_raises(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, {"key": "env", "values": ["prod"]})
        with pytest.raises(DestinationOperationError):
            fragment_client.get_fragment_labels("fragA")

    def test_get_fragment_labels_http_error_raises_operation_error(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(DestinationOperationError, match="failed to get labels for fragment"):
            fragment_client.get_fragment_labels("fragA")

    def test_update_fragment_labels_instance(self, fragment_client, mock_http):
        labels = [Label(key="env", values=["prod"])]
        fragment_client.update_fragment_labels("fragA", labels, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PUT
        assert args[1] == "/v1/instanceDestinationFragments/fragA/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["prod"]}]
        assert kwargs["tenant_subdomain"] is None

    def test_update_fragment_labels_subaccount(self, fragment_client, mock_http):
        labels = [Label(key="env", values=["staging"])]
        fragment_client.update_fragment_labels("fragA", labels, Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinationFragments/fragA/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["staging"]}]

    def test_update_fragment_labels_http_error_propagates(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(409, text="Conflict")
        with pytest.raises(HttpError):
            fragment_client.update_fragment_labels("fragA", [], Level.SUB_ACCOUNT)

    def test_patch_fragment_labels_instance(self, fragment_client, mock_http):
        patch = PatchLabels(action="ADD", labels=[Label(key="env", values=["prod"])])
        fragment_client.patch_fragment_labels("fragA", patch, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PATCH
        assert args[1] == "/v1/instanceDestinationFragments/fragA/labels"
        assert kwargs["json"]["action"] == "ADD"
        assert kwargs["tenant_subdomain"] is None

    def test_patch_fragment_labels_subaccount(self, fragment_client, mock_http):
        patch = PatchLabels(action="DELETE", labels=[Label(key="env", values=[])])
        fragment_client.patch_fragment_labels("fragA", patch, Level.SUB_ACCOUNT)
        args, _ = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinationFragments/fragA/labels"

    def test_patch_fragment_labels_http_error_propagates(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]), Level.SUB_ACCOUNT)

    def test_get_fragment_labels_with_tenant(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragment_client.get_fragment_labels("fragA", tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        mock_http.request.return_value = _make_response(200, [])
        fragment_client.get_fragment_labels("fragA")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_fragment_labels_with_tenant(self, fragment_client, mock_http):
        fragment_client.update_fragment_labels("fragA", [], tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment_client.update_fragment_labels("fragA", [])
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_patch_fragment_labels_with_tenant(self, fragment_client, mock_http):
        fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]), tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_patch_fragment_labels_without_tenant_uses_provider_context(self, fragment_client, mock_http):
        fragment_client.patch_fragment_labels("fragA", PatchLabels(action="ADD", labels=[]))
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None
