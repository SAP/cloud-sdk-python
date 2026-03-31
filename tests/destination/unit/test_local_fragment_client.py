"""Unit tests for LocalDevFragmentClient."""

import json

import pytest

from sap_cloud_sdk.destination.local_fragment_client import LocalDevFragmentClient
from sap_cloud_sdk.destination._local_client_base import FRAGMENT_MOCK_FILE
from sap_cloud_sdk.destination._models import AccessStrategy, Fragment, Level
from sap_cloud_sdk.destination.exceptions import DestinationOperationError, HttpError


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a LocalDevFragmentClient backed by a temp directory."""
    monkeypatch.setattr(
        "sap_cloud_sdk.destination._local_client_base.os.path.abspath",
        lambda _: str(tmp_path),
    )
    return LocalDevFragmentClient()


def _store_path(tmp_path):
    return tmp_path / "mocks" / FRAGMENT_MOCK_FILE


def _write_store(client, data):
    client._write(data)


class TestInit:
    def test_creates_backing_file_on_init(self, client, tmp_path):
        assert _store_path(tmp_path).exists()

    def test_initial_store_has_empty_collections(self, client, tmp_path):
        data = json.loads(_store_path(tmp_path).read_text())
        assert data == {"subaccount": [], "instance": []}


class TestGetInstanceFragment:
    def test_returns_fragment_when_found(self, client):
        _write_store(client, {"instance": [{"FragmentName": "fragA", "URL": "https://example.com"}], "subaccount": []})
        result = client.get_instance_fragment("fragA")
        assert result is not None
        assert result.name == "fragA"

    def test_returns_none_when_not_found(self, client):
        assert client.get_instance_fragment("nonexistent") is None

    def test_finds_by_alt_name_field(self, client):
        # Fragments can be stored with lowercase "fragmentName" (alt_name_field)
        _write_store(client, {"instance": [{"fragmentName": "fragB", "URL": "https://example.com"}], "subaccount": []})
        result = client.get_instance_fragment("fragB")
        assert result is not None
        assert result.name == "fragB"

    def test_ignores_subaccount_collection(self, client):
        _write_store(client, {
            "instance": [],
            "subaccount": [{"FragmentName": "sub-frag", "URL": "https://example.com"}],
        })
        assert client.get_instance_fragment("sub-frag") is None

    def test_returns_fragment_properties(self, client):
        _write_store(client, {"instance": [
            {"FragmentName": "fragA", "URL": "https://example.com", "Authentication": "NoAuthentication"},
        ], "subaccount": []})
        result = client.get_instance_fragment("fragA")
        assert result.properties["URL"] == "https://example.com"
        assert result.properties["Authentication"] == "NoAuthentication"


class TestGetSubaccountFragment:
    def test_provider_only_returns_provider_fragment(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "prov", "URL": "https://example.com"}], "instance": []})
        result = client.get_subaccount_fragment("prov", AccessStrategy.PROVIDER_ONLY)
        assert result is not None
        assert result.name == "prov"

    def test_provider_only_skips_subscriber_entries(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "frag", "URL": "https://x.com", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_fragment("frag", AccessStrategy.PROVIDER_ONLY) is None

    def test_subscriber_only_returns_matching_tenant(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "frag", "URL": "https://x.com", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_fragment("frag", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert result is not None

    def test_subscriber_only_returns_none_for_wrong_tenant(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "frag", "URL": "https://x.com", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_fragment("frag", AccessStrategy.SUBSCRIBER_ONLY, tenant="t2") is None

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "prov", "URL": "https://x.com"}], "instance": []})
        result = client.get_subaccount_fragment("prov", AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert result is not None

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "sub", "URL": "https://x.com", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_fragment("sub", AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert result is not None

    def test_returns_none_when_not_found(self, client):
        assert client.get_subaccount_fragment("ghost", AccessStrategy.PROVIDER_ONLY) is None

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.get_subaccount_fragment("frag", strategy, tenant=None)

    def test_provider_only_does_not_require_tenant(self, client):
        result = client.get_subaccount_fragment("nonexistent", AccessStrategy.PROVIDER_ONLY)
        assert result is None


class TestListInstanceFragments:
    def test_returns_list_of_fragments(self, client):
        _write_store(client, {"instance": [
            {"FragmentName": "f1", "URL": "https://a.com"},
            {"FragmentName": "f2", "URL": "https://b.com"},
        ], "subaccount": []})
        result = client.list_instance_fragments()
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(f, Fragment) for f in result)

    def test_returns_empty_list_for_empty_store(self, client):
        result = client.list_instance_fragments()
        assert result == []

    def test_does_not_include_subaccount_entries(self, client):
        _write_store(client, {
            "instance": [{"FragmentName": "inst", "URL": "https://a.com"}],
            "subaccount": [{"FragmentName": "sub", "URL": "https://b.com"}],
        })
        result = client.list_instance_fragments()
        assert len(result) == 1
        assert result[0].name == "inst"


class TestListSubaccountFragments:
    def test_returns_list_of_fragments(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "f1", "URL": "https://a.com"}], "instance": []})
        result = client.list_subaccount_fragments(AccessStrategy.PROVIDER_ONLY)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_provider_only_returns_only_provider_entries(self, client):
        _write_store(client, {"subaccount": [
            {"FragmentName": "prov", "URL": "https://a.com"},
            {"FragmentName": "sub", "URL": "https://b.com", "tenant": "t1"},
        ], "instance": []})
        result = client.list_subaccount_fragments(AccessStrategy.PROVIDER_ONLY)
        assert len(result) == 1
        assert result[0].name == "prov"

    def test_subscriber_only_returns_only_matching_tenant(self, client):
        _write_store(client, {"subaccount": [
            {"FragmentName": "prov", "URL": "https://a.com"},
            {"FragmentName": "sub-t1", "URL": "https://b.com", "tenant": "t1"},
            {"FragmentName": "sub-t2", "URL": "https://c.com", "tenant": "t2"},
        ], "instance": []})
        result = client.list_subaccount_fragments(AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert len(result) == 1
        assert result[0].name == "sub-t1"

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "prov", "URL": "https://a.com"}], "instance": []})
        result = client.list_subaccount_fragments(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert len(result) == 1

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [{"FragmentName": "sub", "URL": "https://a.com", "tenant": "t1"}], "instance": []})
        result = client.list_subaccount_fragments(AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert len(result) == 1

    def test_both_empty_returns_empty_list(self, client):
        result = client.list_subaccount_fragments(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert result == []

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.list_subaccount_fragments(strategy, tenant=None)


class TestCreateFragment:
    def test_create_instance_fragment(self, client):
        frag = Fragment(name="new", properties={"URL": "https://example.com"})
        client.create_fragment(frag, Level.SERVICE_INSTANCE)
        assert client.get_instance_fragment("new") is not None

    def test_create_subaccount_fragment(self, client):
        frag = Fragment(name="new", properties={"URL": "https://example.com"})
        client.create_fragment(frag, Level.SUB_ACCOUNT)
        result = client.get_subaccount_fragment("new", AccessStrategy.PROVIDER_ONLY)
        assert result is not None

    def test_default_level_is_subaccount(self, client):
        client.create_fragment(Fragment(name="default", properties={}))
        assert client.get_subaccount_fragment("default", AccessStrategy.PROVIDER_ONLY) is not None

    def test_create_duplicate_instance_raises_409(self, client):
        frag = Fragment(name="dup", properties={})
        client.create_fragment(frag, Level.SERVICE_INSTANCE)
        with pytest.raises(HttpError) as exc_info:
            client.create_fragment(frag, Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 409

    def test_create_duplicate_subaccount_raises_409(self, client):
        frag = Fragment(name="dup", properties={})
        client.create_fragment(frag, Level.SUB_ACCOUNT)
        with pytest.raises(HttpError) as exc_info:
            client.create_fragment(frag, Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 409


class TestUpdateFragment:
    def test_update_instance_fragment(self, client):
        client.create_fragment(Fragment(name="frag", properties={"URL": "https://old.com"}), Level.SERVICE_INSTANCE)
        client.update_fragment(Fragment(name="frag", properties={"URL": "https://new.com"}), Level.SERVICE_INSTANCE)
        result = client.get_instance_fragment("frag")
        assert result.properties["URL"] == "https://new.com"

    def test_update_subaccount_fragment(self, client):
        client.create_fragment(Fragment(name="frag", properties={"URL": "https://old.com"}), Level.SUB_ACCOUNT)
        client.update_fragment(Fragment(name="frag", properties={"URL": "https://new.com"}), Level.SUB_ACCOUNT)
        result = client.get_subaccount_fragment("frag", AccessStrategy.PROVIDER_ONLY)
        assert result.properties["URL"] == "https://new.com"

    def test_default_level_is_subaccount(self, client):
        client.create_fragment(Fragment(name="frag", properties={"URL": "https://old.com"}))
        client.update_fragment(Fragment(name="frag", properties={"URL": "https://new.com"}))
        result = client.get_subaccount_fragment("frag", AccessStrategy.PROVIDER_ONLY)
        assert result.properties["URL"] == "https://new.com"

    def test_update_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_fragment(Fragment(name="ghost", properties={}), Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_update_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_fragment(Fragment(name="ghost", properties={}), Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404


class TestDeleteFragment:
    def test_delete_instance_fragment(self, client):
        client.create_fragment(Fragment(name="del", properties={}), Level.SERVICE_INSTANCE)
        client.delete_fragment("del", Level.SERVICE_INSTANCE)
        assert client.get_instance_fragment("del") is None

    def test_delete_subaccount_fragment(self, client):
        client.create_fragment(Fragment(name="del", properties={}), Level.SUB_ACCOUNT)
        client.delete_fragment("del", Level.SUB_ACCOUNT)
        assert client.get_subaccount_fragment("del", AccessStrategy.PROVIDER_ONLY) is None

    def test_default_level_is_subaccount(self, client):
        client.create_fragment(Fragment(name="del", properties={}))
        client.delete_fragment("del")
        assert client.get_subaccount_fragment("del", AccessStrategy.PROVIDER_ONLY) is None

    def test_delete_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_fragment("ghost", Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_delete_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_fragment("ghost", Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404
