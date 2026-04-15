"""Unit tests for Destination data models."""

from dataclasses import is_dataclass

import pytest

from sap_cloud_sdk.destination._models import Destination, DestinationType, ProxyType, Authentication
from sap_cloud_sdk.destination._models import Fragment
from sap_cloud_sdk.destination._models import Label, PatchLabels
from sap_cloud_sdk.destination._models import ListOptions
from sap_cloud_sdk.destination.config import DestinationConfig
from sap_cloud_sdk.destination.exceptions import DestinationOperationError


class TestDestinationConfigModel:

    def test_is_dataclass(self):
        assert is_dataclass(DestinationConfig)

    def test_initialization_and_fields(self):
        sb = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            identityzone="provider-zone",
        )
        assert sb.url == "https://destination.example.com"
        assert sb.token_url == "https://auth.example.com/oauth/token"
        assert sb.client_id == "cid"
        assert sb.client_secret == "csecret"
        assert sb.identityzone == "provider-zone"


class TestDestinationModel:

    def test_is_dataclass(self):
        assert is_dataclass(Destination)

    def test_from_dict_minimal(self):
        data = {"name": "my-dest", "type": "HTTP"}
        dest = Destination.from_dict(data)
        assert dest.name == "my-dest"
        assert dest.type == DestinationType.HTTP
        assert dest.url is None
        assert dest.properties == {}

    def test_from_dict_accepts_upper_camel(self):
        data = {"Name": "my-dest", "Type": "HTTP", "URL": "https://api.example.com"}
        dest = Destination.from_dict(data)
        assert dest.name == "my-dest"
        assert dest.type == DestinationType.HTTP
        assert dest.url == "https://api.example.com"

    def test_from_dict_unknown_string_properties_captured(self):
        data = {
            "name": "my-dest",
            "type": "HTTP",
            "description": "desc",
            "SomeCustomProp": "value",
            "NonString": {"nested": "ignore"},
        }
        dest = Destination.from_dict(data)
        # Known field is set and not duplicated
        assert dest.description == "desc"
        # Unknown string prop goes to properties
        assert dest.properties.get("SomeCustomProp") == "value"
        # Non-string should be ignored
        assert "NonString" not in dest.properties

    def test_from_dict_missing_required_raises(self):
        with pytest.raises(DestinationOperationError, match="missing required fields"):
            Destination.from_dict({"name": "", "type": ""})

    def test_to_dict_serialization_subset(self):
        dest = Destination(
            name="my-dest",
            type=DestinationType.HTTP,
            url="https://api.example.com",
            proxy_type=ProxyType.INTERNET,
            authentication=Authentication.NO_AUTHENTICATION,
            description="desc",
            properties={"extra1": "v1", "description": "should_not_override"},
        )
        payload = dest.to_dict()
        assert payload["Name"] == "my-dest"
        assert payload["Type"] == "HTTP"
        assert payload["URL"] == "https://api.example.com"
        assert payload["ProxyType"] == "Internet"
        assert payload["Authentication"] == "NoAuthentication"
        assert payload["Description"] == "desc"
        # extra1 merged; description from properties must NOT override known field
        assert payload["extra1"] == "v1"
        assert payload["Description"] == "desc"
        # Lowercase 'description' from properties should be preserved and must not override the known 'Description' field
        assert payload.get("description") == "should_not_override"

    def test_destination_from_dict_with_string_type_not_in_enum(self):
        """Test parsing destination with string type not in DestinationType enum."""
        data = {"name": "my-dest", "type": "CUSTOM_TYPE"}
        dest = Destination.from_dict(data)

        # Should store as string when not matching enum
        assert dest.name == "my-dest"
        assert dest.type == "CUSTOM_TYPE"
        assert isinstance(dest.type, str)

    def test_destination_from_dict_with_string_proxy_type_not_in_enum(self):
        """Test parsing destination with string proxy type not in ProxyType enum."""
        data = {"name": "my-dest", "type": "HTTP", "proxyType": "CustomProxy"}
        dest = Destination.from_dict(data)

        assert dest.proxy_type == "CustomProxy"
        assert isinstance(dest.proxy_type, str)

    def test_destination_from_dict_with_string_authentication_not_in_enum(self):
        """Test parsing destination with string authentication not in Authentication enum."""
        data = {"name": "my-dest", "type": "HTTP", "authentication": "CustomAuth"}
        dest = Destination.from_dict(data)

        assert dest.authentication == "CustomAuth"
        assert isinstance(dest.authentication, str)

    def test_destination_from_dict_empty_name(self):
        """Test that empty name raises error."""
        data = {"name": "   ", "type": "HTTP"}

        with pytest.raises(DestinationOperationError) as exc_info:
            Destination.from_dict(data)

        assert "missing required fields" in str(exc_info.value)

    def test_destination_from_dict_empty_type(self):
        """Test that empty type raises error."""
        data = {"name": "my-dest", "type": "   "}

        with pytest.raises(DestinationOperationError) as exc_info:
            Destination.from_dict(data)

        assert "missing required fields" in str(exc_info.value)

    def test_destination_to_dict_with_string_types(self):
        """Test serializing destination with string types (not enums)."""
        dest = Destination(
            name="my-dest",
            type="CUSTOM_TYPE",
            proxy_type="CustomProxy",
            authentication="CustomAuth"
        )

        payload = dest.to_dict()

        assert payload["Type"] == "CUSTOM_TYPE"
        assert payload["ProxyType"] == "CustomProxy"
        assert payload["Authentication"] == "CustomAuth"

    def test_parse_destination_type_with_none(self):
        """Test _parse_destination_type with None returns None."""
        from sap_cloud_sdk.destination._models import _parse_destination_type

        result = _parse_destination_type(None)
        assert result is None

    def test_parse_destination_type_with_enum(self):
        """Test _parse_destination_type with enum instance."""
        from sap_cloud_sdk.destination._models import _parse_destination_type, DestinationType

        result = _parse_destination_type(DestinationType.HTTP)
        assert result == DestinationType.HTTP

    def test_parse_destination_type_with_string_match(self):
        """Test _parse_destination_type with matching string."""
        from sap_cloud_sdk.destination._models import _parse_destination_type, DestinationType

        result = _parse_destination_type("HTTP")
        assert result == DestinationType.HTTP

    def test_parse_destination_type_with_string_no_match(self):
        """Test _parse_destination_type with non-matching string."""
        from sap_cloud_sdk.destination._models import _parse_destination_type

        result = _parse_destination_type("CUSTOM_TYPE")
        assert result == "CUSTOM_TYPE"

    def test_parse_destination_type_with_invalid_type(self):
        """Test _parse_destination_type with invalid type returns None."""
        from sap_cloud_sdk.destination._models import _parse_destination_type

        result = _parse_destination_type(12345)
        assert result is None

    def test_parse_proxy_type_with_none(self):
        """Test _parse_proxy_type with None returns None."""
        from sap_cloud_sdk.destination._models import _parse_proxy_type

        result = _parse_proxy_type(None)
        assert result is None

    def test_parse_proxy_type_with_enum(self):
        """Test _parse_proxy_type with enum instance."""
        from sap_cloud_sdk.destination._models import _parse_proxy_type, ProxyType

        result = _parse_proxy_type(ProxyType.INTERNET)
        assert result == ProxyType.INTERNET

    def test_parse_proxy_type_with_string_no_match(self):
        """Test _parse_proxy_type with non-matching string."""
        from sap_cloud_sdk.destination._models import _parse_proxy_type

        result = _parse_proxy_type("CustomProxy")
        assert result == "CustomProxy"

    def test_parse_authentication_with_none(self):
        """Test _parse_authentication with None returns None."""
        from sap_cloud_sdk.destination._models import _parse_authentication

        result = _parse_authentication(None)
        assert result is None

    def test_parse_authentication_with_enum(self):
        """Test _parse_authentication with enum instance."""
        from sap_cloud_sdk.destination._models import _parse_authentication, Authentication

        result = _parse_authentication(Authentication.BASIC_AUTHENTICATION)
        assert result == Authentication.BASIC_AUTHENTICATION

    def test_parse_authentication_with_string_no_match(self):
        """Test _parse_authentication with non-matching string."""
        from sap_cloud_sdk.destination._models import _parse_authentication

        result = _parse_authentication("CustomAuth")
        assert result == "CustomAuth"

    def test_destination_from_dict_with_none_type(self):
        """Test that None type raises error."""
        data = {"name": "my-dest"}

        with pytest.raises(DestinationOperationError) as exc_info:
            Destination.from_dict(data)

        assert "missing required fields" in str(exc_info.value)


class TestFragmentModel:
    """Tests for Fragment dataclass."""

    def test_fragment_creation(self):
        """Test creating a Fragment instance."""
        fragment = Fragment(
            name="test-fragment",
            properties={"URL": "https://api.example.com", "ProxyType": "Internet"}
        )

        assert fragment.name == "test-fragment"
        assert fragment.properties["URL"] == "https://api.example.com"
        assert fragment.properties["ProxyType"] == "Internet"

    def test_fragment_from_dict_basic(self):
        """Test parsing a basic fragment from dict."""
        data = {
            "FragmentName": "my-fragment",
            "URL": "https://api.example.com",
            "Authentication": "OAuth2ClientCredentials"
        }

        fragment = Fragment.from_dict(data)

        assert fragment.name == "my-fragment"
        assert fragment.properties["URL"] == "https://api.example.com"
        assert fragment.properties["Authentication"] == "OAuth2ClientCredentials"

    def test_fragment_from_dict_camel_case(self):
        """Test parsing fragment with camelCase FragmentName."""
        data = {
            "fragmentName": "my-fragment",
            "ProxyType": "Internet"
        }

        fragment = Fragment.from_dict(data)

        assert fragment.name == "my-fragment"
        assert fragment.properties["ProxyType"] == "Internet"

    def test_fragment_from_dict_missing_name(self):
        """Test parsing fragment without FragmentName raises error."""
        data = {
            "URL": "https://api.example.com"
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Fragment.from_dict(data)

        assert "fragment is missing required field (FragmentName)" in str(exc_info.value)

    def test_fragment_from_dict_empty_name(self):
        """Test parsing fragment with empty FragmentName raises error."""
        data = {
            "FragmentName": "   ",
            "URL": "https://api.example.com"
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Fragment.from_dict(data)

        assert "fragment is missing required field (FragmentName)" in str(exc_info.value)

    def test_fragment_from_dict_filters_non_string_properties(self):
        """Test that non-string properties are not captured."""
        data = {
            "FragmentName": "my-fragment",
            "URL": "https://api.example.com",
            "Port": 8080,  # integer, should be filtered
            "Enabled": True,  # boolean, should be filtered
            "Config": {"key": "value"}  # dict, should be filtered
        }

        fragment = Fragment.from_dict(data)

        assert fragment.name == "my-fragment"
        assert fragment.properties["URL"] == "https://api.example.com"
        assert "Port" not in fragment.properties
        assert "Enabled" not in fragment.properties
        assert "Config" not in fragment.properties

    def test_fragment_to_dict_basic(self):
        """Test serializing a fragment to dict."""
        fragment = Fragment(
            name="my-fragment",
            properties={"URL": "https://api.example.com", "ProxyType": "Internet"}
        )

        result = fragment.to_dict()

        assert result["FragmentName"] == "my-fragment"
        assert result["URL"] == "https://api.example.com"
        assert result["ProxyType"] == "Internet"

    def test_fragment_to_dict_empty_properties(self):
        """Test serializing a fragment with no properties."""
        fragment = Fragment(name="my-fragment", properties={})

        result = fragment.to_dict()

        assert result["FragmentName"] == "my-fragment"
        assert len(result) == 1

    def test_fragment_to_dict_does_not_override_fragment_name(self):
        """Test that properties don't override FragmentName field."""
        fragment = Fragment(
            name="my-fragment",
            properties={"FragmentName": "should-not-override", "URL": "https://api.example.com"}
        )

        result = fragment.to_dict()

        # FragmentName should be from the name field, not properties
        assert result["FragmentName"] == "my-fragment"
        assert result["URL"] == "https://api.example.com"

    def test_fragment_roundtrip(self):
        """Test that from_dict and to_dict are inverse operations."""
        original_data = {
            "FragmentName": "test-fragment",
            "URL": "https://api.example.com",
            "Authentication": "OAuth2ClientCredentials",
            "ProxyType": "Internet"
        }

        # Parse from dict
        fragment = Fragment.from_dict(original_data)

        # Serialize back to dict
        result = fragment.to_dict()

        # Should have same data (though order may differ)
        assert result["FragmentName"] == original_data["FragmentName"]
        assert result["URL"] == original_data["URL"]
        assert result["Authentication"] == original_data["Authentication"]
        assert result["ProxyType"] == original_data["ProxyType"]

    def test_fragment_with_custom_properties(self):
        """Test fragment with custom/unknown properties."""
        data = {
            "FragmentName": "my-fragment",
            "CustomProperty1": "value1",
            "CustomProperty2": "value2",
            "X-Custom-Header": "custom-value"
        }

        fragment = Fragment.from_dict(data)

        assert fragment.name == "my-fragment"
        assert fragment.properties["CustomProperty1"] == "value1"
        assert fragment.properties["CustomProperty2"] == "value2"
        assert fragment.properties["X-Custom-Header"] == "custom-value"

        # Verify roundtrip
        result = fragment.to_dict()
        assert result["CustomProperty1"] == "value1"
        assert result["CustomProperty2"] == "value2"
        assert result["X-Custom-Header"] == "custom-value"


class TestListOptionsModel:
    """Tests for ListOptions dataclass."""

    def test_list_options_is_dataclass(self):
        """Test that ListOptions is a dataclass."""
        assert is_dataclass(ListOptions)

    def test_list_options_default_initialization(self):
        """Test default initialization with no parameters."""
        filter_obj = ListOptions()

        assert filter_obj.filter_names is None
        assert filter_obj.page is None
        assert filter_obj.page_size is None
        assert filter_obj.page_count is False
        assert filter_obj.entity_count is False

    def test_to_query_params_empty_filter(self):
        """Test generating query params from empty filter."""
        filter_obj = ListOptions()
        params = filter_obj.to_query_params()

        assert params == {}

    def test_to_query_params_with_filter_names(self):
        """Test generating query params with name filter."""
        filter_obj = ListOptions(filter_names=["dest1", "dest2", "dest3"])
        params = filter_obj.to_query_params()

        assert "$filter" in params
        assert "Name in" in params["$filter"]
        assert "dest1" in params["$filter"]
        assert "dest2" in params["$filter"]

    def test_to_query_params_with_pagination(self):
        """Test generating query params with pagination."""
        filter_obj = ListOptions(
            page=2,
            page_size=50,
            page_count=True,
            entity_count=True
        )
        params = filter_obj.to_query_params()

        assert params["$page"] == "2"
        assert params["$pageSize"] == "50"
        assert params["$pageCount"] == "true"
        assert params["$entityCount"] == "true"

    def test_page_cannot_combine_with_filter(self):
        """Test that $page cannot be combined with $filter."""
        filter_obj = ListOptions(
            page=1,
            filter_names=["dest1"]
        )

        with pytest.raises(DestinationOperationError) as exc_info:
            filter_obj.to_query_params()

        assert "$page cannot be combined with" in str(exc_info.value)

    def test_page_validation(self):
        """Test validation of page number."""
        filter_obj = ListOptions(page=0)

        with pytest.raises(DestinationOperationError) as exc_info:
            filter_obj.to_query_params()

        assert "page must be >= 1" in str(exc_info.value)

    def test_page_size_validation(self):
        """Test validation of page size."""
        # Too small
        filter_obj = ListOptions(page=1, page_size=0)
        with pytest.raises(DestinationOperationError) as exc_info:
            filter_obj.to_query_params()
        assert "page_size must be between 1 and 1000" in str(exc_info.value)

        # Too large
        filter_obj = ListOptions(page=1, page_size=1001)
        with pytest.raises(DestinationOperationError) as exc_info:
            filter_obj.to_query_params()
        assert "page_size must be between 1 and 1000" in str(exc_info.value)

    def test_list_options_with_page_count_only(self):
        """Test that page_count without page works correctly."""
        filter_obj = ListOptions(page_count=True)
        params = filter_obj.to_query_params()

        # page_count should not appear without page
        assert "$pageCount" not in params

    def test_list_options_with_entity_count_only(self):
        """Test that entity_count without page works correctly."""
        filter_obj = ListOptions(entity_count=True)
        params = filter_obj.to_query_params()

        # entity_count should not appear without page
        assert "$entityCount" not in params

    def test_list_options_with_all_pagination_params(self):
        """Test combining all pagination parameters."""
        filter_obj = ListOptions(
            page=1,
            page_size=100,
            page_count=True,
            entity_count=True
        )

        params = filter_obj.to_query_params()

        assert params["$page"] == "1"
        assert params["$pageSize"] == "100"
        assert params["$pageCount"] == "true"
        assert params["$entityCount"] == "true"

    def test_list_options_with_empty_filter_names(self):
        """Test that empty filter_names list works correctly."""
        filter_obj = ListOptions(filter_names=[])
        params = filter_obj.to_query_params()

        # Empty list should not create a filter
        assert "$filter" not in params


class TestTransparentProxyDestinationModel:
    """Tests for TransparentProxyDestination dataclass."""

    def test_transparent_proxy_destination_is_dataclass(self):
        """Test that TransparentProxyDestination is a dataclass."""
        from dataclasses import is_dataclass
        from sap_cloud_sdk.destination._models import TransparentProxyDestination
        assert is_dataclass(TransparentProxyDestination)

    def test_transparent_proxy_destination_creation(self):
        """Test creating a TransparentProxyDestination instance."""
        from sap_cloud_sdk.destination._models import TransparentProxyDestination

        dest = TransparentProxyDestination(
            name="my-dest",
            url="http://proxy.namespace",
            headers={"X-destination-name": "my-dest"}
        )

        assert dest.name == "my-dest"
        assert dest.url == "http://proxy.namespace"
        assert dest.headers["X-destination-name"] == "my-dest"

    def test_transparent_proxy_destination_from_proxy(self):
        """Test creating TransparentProxyDestination from TransparentProxy."""
        from sap_cloud_sdk.destination._models import TransparentProxyDestination, TransparentProxy

        proxy = TransparentProxy(proxy_name="connectivity-proxy", namespace="my-namespace")
        dest = TransparentProxyDestination.from_proxy("my-dest", proxy)

        assert dest.name == "my-dest"
        assert dest.url == "http://connectivity-proxy.my-namespace"
        assert dest.headers["X-destination-name"] == "my-dest"

    def test_transparent_proxy_destination_from_proxy_without_proxy_raises(self):
        """Test that from_proxy without proxy configuration raises error."""
        from sap_cloud_sdk.destination._models import TransparentProxyDestination

        with pytest.raises(DestinationOperationError) as exc_info:
            TransparentProxyDestination.from_proxy("my-dest", None)

        assert "transparent_proxy configuration is required but not provided" in str(exc_info.value)

    def test_transparent_proxy_destination_set_header(self):
        """Test setting a header using set_header method."""
        from sap_cloud_sdk.destination._models import (
            TransparentProxyDestination,
            TransparentProxy,
            TransparentProxyHeader
        )

        proxy = TransparentProxy(proxy_name="connectivity-proxy", namespace="my-namespace")
        dest = TransparentProxyDestination.from_proxy("my-dest", proxy)

        # Set SAP Connectivity Authentication header
        dest.set_header(TransparentProxyHeader.AUTHORIZATION, "Bearer token123")

        assert dest.headers["X-destination-name"] == "my-dest"
        assert dest.headers["Authorization"] == "Bearer token123"

    def test_transparent_proxy_destination_set_header_updates_existing(self):
        """Test that set_header updates existing header value."""
        from sap_cloud_sdk.destination._models import (
            TransparentProxyDestination,
            TransparentProxy,
            TransparentProxyHeader
        )

        proxy = TransparentProxy(proxy_name="connectivity-proxy", namespace="my-namespace")
        dest = TransparentProxyDestination.from_proxy("my-dest", proxy)

        # Set header first time
        dest.set_header(TransparentProxyHeader.AUTHORIZATION, "Bearer token123")
        assert dest.headers["Authorization"] == "Bearer token123"

        # Update header value
        dest.set_header(TransparentProxyHeader.AUTHORIZATION, "Bearer newtoken456")
        assert dest.headers["Authorization"] == "Bearer newtoken456"


class TestLabelModel:
    """Tests for Label dataclass."""

    def test_is_dataclass(self):
        assert is_dataclass(Label)

    def test_from_dict_basic(self):
        lbl = Label.from_dict({"key": "env", "values": ["prod", "staging"]})
        assert lbl.key == "env"
        assert lbl.values == ["prod", "staging"]

    def test_from_dict_single_value(self):
        lbl = Label.from_dict({"key": "team", "values": ["platform"]})
        assert lbl.key == "team"
        assert lbl.values == ["platform"]

    def test_from_dict_empty_values_list(self):
        lbl = Label.from_dict({"key": "region", "values": []})
        assert lbl.key == "region"
        assert lbl.values == []

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(DestinationOperationError, match="missing required field"):
            Label.from_dict({"values": ["v1"]})

    def test_from_dict_empty_key_raises(self):
        with pytest.raises(DestinationOperationError, match="missing required field"):
            Label.from_dict({"key": "", "values": ["v1"]})

    def test_from_dict_whitespace_only_key_raises(self):
        with pytest.raises(DestinationOperationError, match="missing required field"):
            Label.from_dict({"key": "   ", "values": ["v1"]})

    def test_from_dict_non_list_values_raises(self):
        with pytest.raises(DestinationOperationError, match="'values' must be a list"):
            Label.from_dict({"key": "env", "values": "prod"})

    def test_to_dict_round_trips(self):
        original = {"key": "env", "values": ["prod", "staging"]}
        assert Label.from_dict(original).to_dict() == original

    def test_to_dict_values_is_copy(self):
        lbl = Label(key="k", values=["v1", "v2"])
        d = lbl.to_dict()
        d["values"].append("extra")
        assert lbl.values == ["v1", "v2"]

    def test_from_dict_missing_values_defaults_to_empty(self):
        lbl = Label.from_dict({"key": "env"})
        assert lbl.values == []


class TestPatchLabelsModel:
    """Tests for PatchLabels dataclass."""

    def test_is_dataclass(self):
        assert is_dataclass(PatchLabels)

    def test_to_dict_add_action(self):
        patch = PatchLabels(
            action="ADD",
            labels=[Label(key="env", values=["prod"])],
        )
        result = patch.to_dict()
        assert result["action"] == "ADD"
        assert result["labels"] == [{"key": "env", "values": ["prod"]}]

    def test_to_dict_delete_action(self):
        patch = PatchLabels(
            action="DELETE",
            labels=[Label(key="env", values=["staging"])],
        )
        result = patch.to_dict()
        assert result["action"] == "DELETE"
        assert result["labels"][0]["key"] == "env"

    def test_to_dict_multiple_labels(self):
        patch = PatchLabels(
            action="ADD",
            labels=[
                Label(key="env", values=["prod"]),
                Label(key="team", values=["platform", "infra"]),
            ],
        )
        result = patch.to_dict()
        assert len(result["labels"]) == 2


class TestListOptionsLabelFilter:
    """Tests for ListOptions.filter_labels."""

    def test_single_label_single_value(self):
        opts = ListOptions(filter_labels=[Label(key="env", values=["prod"])])
        params = opts.to_query_params()
        assert params["$filter"] == "Label['env'] HAS ('prod')"

    def test_single_label_multiple_values(self):
        opts = ListOptions(filter_labels=[Label(key="env", values=["prod", "staging"])])
        params = opts.to_query_params()
        assert params["$filter"] == "Label['env'] HAS ('prod', 'staging')"

    def test_multiple_labels_joined_with_and(self):
        opts = ListOptions(filter_labels=[
            Label(key="env", values=["prod"]),
            Label(key="team", values=["platform"]),
        ])
        params = opts.to_query_params()
        assert params["$filter"] == "Label['env'] HAS ('prod') AND Label['team'] HAS ('platform')"

    def test_filter_labels_and_filter_names_raises(self):
        opts = ListOptions(
            filter_names=["dest1"],
            filter_labels=[Label(key="env", values=["prod"])],
        )
        with pytest.raises(DestinationOperationError):
            opts.to_query_params()

    def test_filter_labels_with_page_raises(self):
        opts = ListOptions(
            page=1,
            filter_labels=[Label(key="env", values=["prod"])],
        )
        with pytest.raises(DestinationOperationError, match=r"\$page cannot be combined with"):
            opts.to_query_params()

    def test_special_chars_in_key_are_encoded(self):
        opts = ListOptions(filter_labels=[Label(key="my key", values=["v1"])])
        params = opts.to_query_params()
        assert "my%20key" in params["$filter"]

    def test_special_chars_in_value_are_encoded(self):
        opts = ListOptions(filter_labels=[Label(key="env", values=["prod qa"])])
        params = opts.to_query_params()
        assert "prod%20qa" in params["$filter"]

    def test_empty_filter_labels_list_produces_no_filter(self):
        opts = ListOptions(filter_labels=[])
        params = opts.to_query_params()
        assert "$filter" not in params

    def test_transparent_proxy_destination_set_header_with_x_destination_name(self):
        """Test setting X-destination-name header explicitly."""
        from sap_cloud_sdk.destination._models import (
            TransparentProxyDestination,
            TransparentProxy,
            TransparentProxyHeader
        )

        proxy = TransparentProxy(proxy_name="connectivity-proxy", namespace="my-namespace")
        dest = TransparentProxyDestination.from_proxy("my-dest", proxy)

        # Update X-destination-name header
        dest.set_header(TransparentProxyHeader.X_DESTINATION_NAME, "updated-dest")

        assert dest.headers["X-destination-name"] == "updated-dest"

    def test_transparent_proxy_header_enum_values(self):
        """Test TransparentProxyHeader enum values."""
        from sap_cloud_sdk.destination._models import TransparentProxyHeader

        assert TransparentProxyHeader.X_DESTINATION_NAME.value == "X-destination-name"
        assert TransparentProxyHeader.AUTHORIZATION.value == "Authorization"


class TestCertificateModel:
    """Tests for Certificate dataclass."""

    def test_certificate_is_dataclass(self):
        """Test that Certificate is a dataclass."""
        from dataclasses import is_dataclass
        from sap_cloud_sdk.destination._models import Certificate
        assert is_dataclass(Certificate)

    def test_certificate_creation(self):
        """Test creating a Certificate instance."""
        from sap_cloud_sdk.destination._models import Certificate

        cert = Certificate(
            name="test-cert.pem",
            content="base64-encoded-content",
            type="PEM"
        )

        assert cert.name == "test-cert.pem"
        assert cert.content == "base64-encoded-content"
        assert cert.type == "PEM"
        assert cert.properties == {}

    def test_certificate_from_dict_basic(self):
        """Test parsing a basic certificate from dict."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "my-cert.pem",
            "Content": "base64-content",
            "Type": "PEM"
        }

        cert = Certificate.from_dict(data)

        assert cert.name == "my-cert.pem"
        assert cert.content == "base64-content"
        assert cert.type == "PEM"

    def test_certificate_from_dict_lowercase_keys(self):
        """Test parsing certificate with lowercase keys."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "name": "my-cert.jks",
            "content": "base64-jks-content",
            "type": "JKS"
        }

        cert = Certificate.from_dict(data)

        assert cert.name == "my-cert.jks"
        assert cert.content == "base64-jks-content"
        assert cert.type == "JKS"

    def test_certificate_from_dict_missing_name(self):
        """Test parsing certificate without name raises error."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Content": "base64-content"
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Certificate.from_dict(data)

        assert "certificate is missing required fields (Name/Content)" in str(exc_info.value)

    def test_certificate_from_dict_empty_name(self):
        """Test parsing certificate with empty name raises error."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "   ",
            "Content": "base64-content"
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Certificate.from_dict(data)

        assert "certificate is missing required fields (Name/Content)" in str(exc_info.value)

    def test_certificate_from_dict_missing_content(self):
        """Test parsing certificate without content raises error."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "my-cert.pem"
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Certificate.from_dict(data)

        assert "certificate is missing required fields (Name/Content)" in str(exc_info.value)

    def test_certificate_from_dict_empty_content(self):
        """Test parsing certificate with empty content raises error."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "my-cert.pem",
            "Content": "   "
        }

        with pytest.raises(DestinationOperationError) as exc_info:
            Certificate.from_dict(data)

        assert "certificate is missing required fields (Name/Content)" in str(exc_info.value)

    def test_certificate_from_dict_with_properties(self):
        """Test parsing certificate with additional properties."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "my-cert.pem",
            "Content": "base64-content",
            "Type": "PEM",
            "CustomProperty": "custom-value",
            "AnotherProp": "another-value"
        }

        cert = Certificate.from_dict(data)

        assert cert.name == "my-cert.pem"
        assert cert.content == "base64-content"
        assert cert.type == "PEM"
        assert cert.properties["CustomProperty"] == "custom-value"
        assert cert.properties["AnotherProp"] == "another-value"

    def test_certificate_from_dict_filters_non_string_properties(self):
        """Test that non-string properties are not captured."""
        from sap_cloud_sdk.destination._models import Certificate

        data = {
            "Name": "my-cert.pem",
            "Content": "base64-content",
            "Port": 8080,  # integer, should be filtered
            "Enabled": True,  # boolean, should be filtered
            "Config": {"key": "value"}  # dict, should be filtered
        }

        cert = Certificate.from_dict(data)

        assert cert.name == "my-cert.pem"
        assert cert.content == "base64-content"
        assert "Port" not in cert.properties
        assert "Enabled" not in cert.properties
        assert "Config" not in cert.properties

    def test_certificate_to_dict_basic(self):
        """Test serializing a certificate to dict."""
        from sap_cloud_sdk.destination._models import Certificate

        cert = Certificate(
            name="my-cert.pem",
            content="base64-content",
            type="PEM"
        )

        result = cert.to_dict()

        assert result["Name"] == "my-cert.pem"
        assert result["Content"] == "base64-content"
        assert result["Type"] == "PEM"

    def test_certificate_to_dict_without_type(self):
        """Test serializing a certificate without type."""
        from sap_cloud_sdk.destination._models import Certificate

        cert = Certificate(
            name="my-cert.pem",
            content="base64-content"
        )

        result = cert.to_dict()

        assert result["Name"] == "my-cert.pem"
        assert result["Content"] == "base64-content"
        assert "Type" not in result

    def test_certificate_to_dict_with_properties(self):
        """Test serializing certificate with additional properties."""
        from sap_cloud_sdk.destination._models import Certificate

        cert = Certificate(
            name="my-cert.pem",
            content="base64-content",
            type="PEM",
            properties={"CustomProp": "value1", "AnotherProp": "value2"}
        )

        result = cert.to_dict()

        assert result["Name"] == "my-cert.pem"
        assert result["Content"] == "base64-content"
        assert result["Type"] == "PEM"
        assert result["CustomProp"] == "value1"
        assert result["AnotherProp"] == "value2"

    def test_certificate_to_dict_properties_dont_override_known_fields(self):
        """Test that properties don't override known fields."""
        from sap_cloud_sdk.destination._models import Certificate

        cert = Certificate(
            name="my-cert.pem",
            content="base64-content",
            type="PEM",
            properties={"Name": "should-not-override", "CustomProp": "value"}
        )

        result = cert.to_dict()

        # Known fields should not be overridden
        assert result["Name"] == "my-cert.pem"
        assert result["Content"] == "base64-content"
        assert result["Type"] == "PEM"
        assert result["CustomProp"] == "value"

    def test_certificate_roundtrip(self):
        """Test that from_dict and to_dict are inverse operations."""
        from sap_cloud_sdk.destination._models import Certificate

        original_data = {
            "Name": "test-cert.pem",
            "Content": "base64-encoded-content",
            "Type": "PEM",
            "CustomProperty": "custom-value"
        }

        # Parse from dict
        cert = Certificate.from_dict(original_data)

        # Serialize back to dict
        result = cert.to_dict()

        # Should have same data
        assert result["Name"] == original_data["Name"]
        assert result["Content"] == original_data["Content"]
        assert result["Type"] == original_data["Type"]
        assert result["CustomProperty"] == original_data["CustomProperty"]
