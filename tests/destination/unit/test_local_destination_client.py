"""Unit tests for LocalDevDestinationClient."""

import json

import pytest

from sap_cloud_sdk.destination.local_client import LocalDevDestinationClient
from sap_cloud_sdk.destination._local_client_base import DESTINATION_MOCK_FILE
from sap_cloud_sdk.destination._models import AccessStrategy, Destination, Level
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import DestinationOperationError, HttpError


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a LocalDevDestinationClient backed by a temp directory."""
    monkeypatch.setattr(
        "sap_cloud_sdk.destination._local_client_base.os.path.abspath",
        lambda _: str(tmp_path),
    )
    return LocalDevDestinationClient()


def _store_path(tmp_path):
    return tmp_path / "mocks" / DESTINATION_MOCK_FILE


def _write_store(client, data):
    client._write(data)


class TestInit:
    def test_creates_backing_file_on_init(self, client, tmp_path):
        assert _store_path(tmp_path).exists()

    def test_initial_store_has_empty_collections(self, client, tmp_path):
        data = json.loads(_store_path(tmp_path).read_text())
        assert data == {"subaccount": [], "instance": []}


class TestGetInstanceDestination:
    def test_returns_destination_when_found(self, client):
        _write_store(client, {"instance": [{"name": "destA", "type": "HTTP"}], "subaccount": []})
        result = client.get_instance_destination("destA")
        assert result is not None
        assert result.name == "destA"

    def test_returns_none_when_not_found(self, client):
        assert client.get_instance_destination("nonexistent") is None

    def test_finds_by_alt_name_field(self, client):
        _write_store(client, {"instance": [{"Name": "destB", "type": "HTTP"}], "subaccount": []})
        result = client.get_instance_destination("destB")
        assert result is not None
        assert result.name == "destB"

    def test_ignores_subaccount_collection(self, client):
        _write_store(client, {
            "instance": [],
            "subaccount": [{"name": "sub-dest", "type": "HTTP"}],
        })
        assert client.get_instance_destination("sub-dest") is None


class TestGetSubaccountDestination:
    def test_provider_only_returns_provider_destination(self, client):
        _write_store(client, {"subaccount": [{"name": "prov", "type": "HTTP"}], "instance": []})
        result = client.get_subaccount_destination("prov", AccessStrategy.PROVIDER_ONLY)
        assert result is not None
        assert result.name == "prov"

    def test_provider_only_skips_subscriber_entries(self, client):
        _write_store(client, {"subaccount": [{"name": "prov", "type": "HTTP", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_destination("prov", AccessStrategy.PROVIDER_ONLY) is None

    def test_subscriber_only_returns_matching_tenant(self, client):
        _write_store(client, {"subaccount": [{"name": "dest", "type": "HTTP", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_destination("dest", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert result is not None
        assert result.name == "dest"

    def test_subscriber_only_returns_none_for_wrong_tenant(self, client):
        _write_store(client, {"subaccount": [{"name": "dest", "type": "HTTP", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_destination("dest", AccessStrategy.SUBSCRIBER_ONLY, tenant="t2") is None

    def test_subscriber_first_returns_subscriber_when_present(self, client):
        _write_store(client, {"subaccount": [
            {"name": "dest", "type": "HTTP", "tenant": "t1"},
            {"name": "dest", "type": "HTTP"},
        ], "instance": []})
        result = client.get_subaccount_destination("dest", AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        # Should prefer subscriber entry (has tenant)
        assert result is not None

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [{"name": "prov", "type": "HTTP"}], "instance": []})
        result = client.get_subaccount_destination("prov", AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert result is not None
        assert result.name == "prov"

    def test_provider_first_returns_provider_when_present(self, client):
        _write_store(client, {"subaccount": [
            {"name": "dest", "type": "HTTP"},
            {"name": "dest", "type": "HTTP", "tenant": "t1"},
        ], "instance": []})
        result = client.get_subaccount_destination("dest", AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert result is not None

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [{"name": "sub", "type": "HTTP", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_destination("sub", AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert result is not None
        assert result.name == "sub"

    def test_returns_none_when_not_found(self, client):
        assert client.get_subaccount_destination("ghost", AccessStrategy.PROVIDER_ONLY) is None

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.get_subaccount_destination("d", strategy, tenant=None)

    def test_provider_only_does_not_require_tenant(self, client):
        # Should not raise even without tenant
        result = client.get_subaccount_destination("nonexistent", AccessStrategy.PROVIDER_ONLY)
        assert result is None


class TestListInstanceDestinations:
    def test_returns_paged_result(self, client):
        _write_store(client, {"instance": [
            {"name": "d1", "type": "HTTP"},
            {"name": "d2", "type": "HTTP"},
        ], "subaccount": []})
        result = client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 2
        assert all(isinstance(d, Destination) for d in result.items)

    def test_pagination_is_always_none(self, client):
        result = client.list_instance_destinations()
        assert result.pagination is None

    def test_returns_empty_for_empty_store(self, client):
        result = client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 0

    def test_filter_param_is_accepted_and_ignored(self, client):
        _write_store(client, {"instance": [{"name": "d1", "type": "HTTP"}], "subaccount": []})
        result = client.list_instance_destinations(_filter=object())
        assert len(result.items) == 1

    def test_does_not_include_subaccount_entries(self, client):
        _write_store(client, {
            "instance": [{"name": "inst", "type": "HTTP"}],
            "subaccount": [{"name": "sub", "type": "HTTP"}],
        })
        result = client.list_instance_destinations()
        assert len(result.items) == 1
        assert result.items[0].name == "inst"


class TestListSubaccountDestinations:
    def test_returns_paged_result(self, client):
        result = client.list_subaccount_destinations(AccessStrategy.PROVIDER_ONLY)
        assert isinstance(result, PagedResult)
        assert result.pagination is None

    def test_provider_only_returns_only_provider_entries(self, client):
        _write_store(client, {"subaccount": [
            {"name": "prov", "type": "HTTP"},
            {"name": "sub", "type": "HTTP", "tenant": "t1"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.PROVIDER_ONLY)
        assert len(result.items) == 1
        assert result.items[0].name == "prov"

    def test_subscriber_only_returns_only_matching_tenant(self, client):
        _write_store(client, {"subaccount": [
            {"name": "prov", "type": "HTTP"},
            {"name": "sub-t1", "type": "HTTP", "tenant": "t1"},
            {"name": "sub-t2", "type": "HTTP", "tenant": "t2"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert len(result.items) == 1
        assert result.items[0].name == "sub-t1"

    def test_subscriber_first_no_fallback_needed(self, client):
        _write_store(client, {"subaccount": [
            {"name": "sub", "type": "HTTP", "tenant": "t1"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert len(result.items) == 1
        assert result.items[0].name == "sub"

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [
            {"name": "prov", "type": "HTTP"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert len(result.items) == 1
        assert result.items[0].name == "prov"

    def test_provider_first_no_fallback_needed(self, client):
        _write_store(client, {"subaccount": [
            {"name": "prov", "type": "HTTP"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert len(result.items) == 1

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [
            {"name": "sub", "type": "HTTP", "tenant": "t1"},
        ], "instance": []})
        result = client.list_subaccount_destinations(AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert len(result.items) == 1
        assert result.items[0].name == "sub"

    def test_both_empty_returns_empty_paged_result(self, client):
        result = client.list_subaccount_destinations(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert isinstance(result, PagedResult)
        assert len(result.items) == 0

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.list_subaccount_destinations(strategy, tenant=None)


class TestCreateDestination:
    def test_create_instance_destination(self, client):
        client.create_destination(Destination(name="new", type="HTTP"), Level.SERVICE_INSTANCE)
        assert client.get_instance_destination("new") is not None

    def test_create_subaccount_destination(self, client):
        client.create_destination(Destination(name="new", type="HTTP"), Level.SUB_ACCOUNT)
        result = client.get_subaccount_destination("new", AccessStrategy.PROVIDER_ONLY)
        assert result is not None

    def test_default_level_is_subaccount(self, client):
        client.create_destination(Destination(name="default", type="HTTP"))
        assert client.get_subaccount_destination("default", AccessStrategy.PROVIDER_ONLY) is not None

    def test_create_duplicate_instance_raises_409(self, client):
        dest = Destination(name="dup", type="HTTP")
        client.create_destination(dest, Level.SERVICE_INSTANCE)
        with pytest.raises(HttpError) as exc_info:
            client.create_destination(dest, Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 409

    def test_create_duplicate_subaccount_raises_409(self, client):
        dest = Destination(name="dup", type="HTTP")
        client.create_destination(dest, Level.SUB_ACCOUNT)
        with pytest.raises(HttpError) as exc_info:
            client.create_destination(dest, Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 409

    def test_subaccount_entry_has_no_tenant_field(self, client):
        client.create_destination(Destination(name="prov", type="HTTP"), Level.SUB_ACCOUNT)
        # A subscriber-access read should not find it (no tenant attached)
        assert client.get_subaccount_destination("prov", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1") is None
        # But provider-access should find it
        assert client.get_subaccount_destination("prov", AccessStrategy.PROVIDER_ONLY) is not None


class TestUpdateDestination:
    def test_update_instance_destination(self, client):
        client.create_destination(Destination(name="dest", type="HTTP", description="v1"), Level.SERVICE_INSTANCE)
        client.update_destination(Destination(name="dest", type="HTTP", description="v2"), Level.SERVICE_INSTANCE)
        result = client.get_instance_destination("dest")
        assert result.description == "v2"

    def test_update_subaccount_destination(self, client):
        client.create_destination(Destination(name="dest", type="HTTP", description="v1"), Level.SUB_ACCOUNT)
        client.update_destination(Destination(name="dest", type="HTTP", description="v2"), Level.SUB_ACCOUNT)
        result = client.get_subaccount_destination("dest", AccessStrategy.PROVIDER_ONLY)
        assert result.description == "v2"

    def test_update_subaccount_preserves_tenant_field(self, client):
        _write_store(client, {"subaccount": [
            {"name": "dest", "type": "HTTP", "tenant": "t1", "description": "old"},
        ], "instance": []})
        client.update_destination(Destination(name="dest", type="HTTP", description="new"), Level.SUB_ACCOUNT)
        # Tenant was preserved — entry is still accessible as a subscriber destination
        result = client.get_subaccount_destination("dest", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert result is not None
        assert result.description == "new"

    def test_default_level_is_subaccount(self, client):
        client.create_destination(Destination(name="dest", type="HTTP", description="v1"))
        client.update_destination(Destination(name="dest", type="HTTP", description="v2"))
        result = client.get_subaccount_destination("dest", AccessStrategy.PROVIDER_ONLY)
        assert result.description == "v2"

    def test_update_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_destination(Destination(name="ghost", type="HTTP"), Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_update_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_destination(Destination(name="ghost", type="HTTP"), Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404


class TestDeleteDestination:
    def test_delete_instance_destination(self, client):
        client.create_destination(Destination(name="del", type="HTTP"), Level.SERVICE_INSTANCE)
        client.delete_destination("del", Level.SERVICE_INSTANCE)
        assert client.get_instance_destination("del") is None

    def test_delete_subaccount_provider_destination(self, client):
        client.create_destination(Destination(name="del", type="HTTP"), Level.SUB_ACCOUNT)
        client.delete_destination("del", Level.SUB_ACCOUNT)
        assert client.get_subaccount_destination("del", AccessStrategy.PROVIDER_ONLY) is None

    def test_delete_default_level_is_subaccount(self, client):
        client.create_destination(Destination(name="del", type="HTTP"))
        client.delete_destination("del")
        assert client.get_subaccount_destination("del", AccessStrategy.PROVIDER_ONLY) is None

    def test_delete_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_destination("ghost", Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_delete_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_destination("ghost", Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404

    def test_delete_subaccount_only_removes_provider_entry(self, client):
        _write_store(client, {"subaccount": [
            {"name": "dest", "type": "HTTP", "tenant": "t1"},  # subscriber
            {"name": "dest", "type": "HTTP"},                   # provider
        ], "instance": []})
        client.delete_destination("dest", Level.SUB_ACCOUNT)
        # Subscriber entry must remain
        assert client.get_subaccount_destination("dest", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1") is not None
        # Provider entry is gone
        assert client.get_subaccount_destination("dest", AccessStrategy.PROVIDER_ONLY) is None
