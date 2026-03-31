"""Unit tests for LocalDevCertificateClient."""

import json

import pytest

from sap_cloud_sdk.destination.local_certificate_client import LocalDevCertificateClient
from sap_cloud_sdk.destination._models import AccessStrategy, Certificate, Level
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import DestinationOperationError, HttpError


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a LocalDevCertificateClient backed by a temp directory."""
    monkeypatch.setattr(
        "sap_cloud_sdk.destination._local_client_base.os.path.abspath",
        lambda _: str(tmp_path),
    )
    return LocalDevCertificateClient()


def _store_path(tmp_path):
    return tmp_path / "mocks" / "certificates.json"


def _write_store(client, data):
    client._write(data)


class TestInit:
    def test_creates_backing_file_on_init(self, client, tmp_path):
        assert _store_path(tmp_path).exists()

    def test_initial_store_has_empty_collections(self, client, tmp_path):
        data = json.loads(_store_path(tmp_path).read_text())
        assert data == {"subaccount": [], "instance": []}


class TestGetInstanceCertificate:
    def test_returns_certificate_when_found(self, client):
        _write_store(client, {"instance": [{"Name": "cert.pem", "Content": "abc", "Type": "PEM"}], "subaccount": []})
        result = client.get_instance_certificate("cert.pem")
        assert result is not None
        assert result.name == "cert.pem"

    def test_returns_none_when_not_found(self, client):
        assert client.get_instance_certificate("nonexistent") is None

    def test_finds_by_alt_name_field(self, client):
        # Certificates stored with lowercase "name" key (alt_name_field)
        _write_store(client, {"instance": [{"name": "cert.pem", "Content": "abc"}], "subaccount": []})
        result = client.get_instance_certificate("cert.pem")
        assert result is not None
        assert result.name == "cert.pem"

    def test_ignores_subaccount_collection(self, client):
        _write_store(client, {
            "instance": [],
            "subaccount": [{"Name": "sub-cert.pem", "Content": "abc"}],
        })
        assert client.get_instance_certificate("sub-cert.pem") is None


class TestGetSubaccountCertificate:
    def test_provider_only_returns_provider_certificate(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc"}], "instance": []})
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.PROVIDER_ONLY)
        assert result is not None
        assert result.name == "cert.pem"

    def test_provider_only_skips_subscriber_entries(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_certificate("cert.pem", AccessStrategy.PROVIDER_ONLY) is None

    def test_subscriber_only_returns_matching_tenant(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert result is not None

    def test_subscriber_only_returns_none_for_wrong_tenant(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc", "tenant": "t1"}], "instance": []})
        assert client.get_subaccount_certificate("cert.pem", AccessStrategy.SUBSCRIBER_ONLY, tenant="t2") is None

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc"}], "instance": []})
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert result is not None

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [{"Name": "cert.pem", "Content": "abc", "tenant": "t1"}], "instance": []})
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert result is not None

    def test_returns_none_when_not_found(self, client):
        assert client.get_subaccount_certificate("ghost", AccessStrategy.PROVIDER_ONLY) is None

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.get_subaccount_certificate("cert.pem", strategy, tenant=None)

    def test_provider_only_does_not_require_tenant(self, client):
        result = client.get_subaccount_certificate("nonexistent", AccessStrategy.PROVIDER_ONLY)
        assert result is None


class TestListInstanceCertificates:
    def test_returns_paged_result(self, client):
        _write_store(client, {"instance": [
            {"Name": "cert1.pem", "Content": "c1"},
            {"Name": "cert2.jks", "Content": "c2"},
        ], "subaccount": []})
        result = client.list_instance_certificates()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 2
        assert all(isinstance(c, Certificate) for c in result.items)

    def test_pagination_is_always_none(self, client):
        assert client.list_instance_certificates().pagination is None

    def test_returns_empty_for_empty_store(self, client):
        result = client.list_instance_certificates()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 0

    def test_filter_param_is_accepted_and_ignored(self, client):
        _write_store(client, {"instance": [{"Name": "cert.pem", "Content": "c1"}], "subaccount": []})
        result = client.list_instance_certificates(_filter=object())
        assert len(result.items) == 1

    def test_does_not_include_subaccount_entries(self, client):
        _write_store(client, {
            "instance": [{"Name": "inst.pem", "Content": "c1"}],
            "subaccount": [{"Name": "sub.pem", "Content": "c2"}],
        })
        result = client.list_instance_certificates()
        assert len(result.items) == 1
        assert result.items[0].name == "inst.pem"


class TestListSubaccountCertificates:
    def test_returns_paged_result(self, client):
        result = client.list_subaccount_certificates(AccessStrategy.PROVIDER_ONLY)
        assert isinstance(result, PagedResult)
        assert result.pagination is None

    def test_provider_only_returns_only_provider_entries(self, client):
        _write_store(client, {"subaccount": [
            {"Name": "prov.pem", "Content": "c1"},
            {"Name": "sub.pem", "Content": "c2", "tenant": "t1"},
        ], "instance": []})
        result = client.list_subaccount_certificates(AccessStrategy.PROVIDER_ONLY)
        assert len(result.items) == 1
        assert result.items[0].name == "prov.pem"

    def test_subscriber_only_returns_only_matching_tenant(self, client):
        _write_store(client, {"subaccount": [
            {"Name": "prov.pem", "Content": "c1"},
            {"Name": "sub-t1.pem", "Content": "c2", "tenant": "t1"},
            {"Name": "sub-t2.pem", "Content": "c3", "tenant": "t2"},
        ], "instance": []})
        result = client.list_subaccount_certificates(AccessStrategy.SUBSCRIBER_ONLY, tenant="t1")
        assert len(result.items) == 1
        assert result.items[0].name == "sub-t1.pem"

    def test_subscriber_first_falls_back_to_provider(self, client):
        _write_store(client, {"subaccount": [{"Name": "prov.pem", "Content": "c1"}], "instance": []})
        result = client.list_subaccount_certificates(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert len(result.items) == 1

    def test_provider_first_falls_back_to_subscriber(self, client):
        _write_store(client, {"subaccount": [{"Name": "sub.pem", "Content": "c1", "tenant": "t1"}], "instance": []})
        result = client.list_subaccount_certificates(AccessStrategy.PROVIDER_FIRST, tenant="t1")
        assert len(result.items) == 1

    def test_both_empty_returns_empty_paged_result(self, client):
        result = client.list_subaccount_certificates(AccessStrategy.SUBSCRIBER_FIRST, tenant="t1")
        assert isinstance(result, PagedResult)
        assert len(result.items) == 0

    @pytest.mark.parametrize("strategy", [
        AccessStrategy.SUBSCRIBER_ONLY,
        AccessStrategy.SUBSCRIBER_FIRST,
        AccessStrategy.PROVIDER_FIRST,
    ])
    def test_requires_tenant_for_subscriber_strategies(self, client, strategy):
        with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
            client.list_subaccount_certificates(strategy, tenant=None)


class TestCreateCertificate:
    def test_create_instance_certificate(self, client):
        cert = Certificate(name="new.pem", content="c1", type="PEM")
        client.create_certificate(cert, Level.SERVICE_INSTANCE)
        assert client.get_instance_certificate("new.pem") is not None

    def test_create_subaccount_certificate(self, client):
        cert = Certificate(name="new.pem", content="c1", type="PEM")
        client.create_certificate(cert, Level.SUB_ACCOUNT)
        result = client.get_subaccount_certificate("new.pem", AccessStrategy.PROVIDER_ONLY)
        assert result is not None

    def test_default_level_is_subaccount(self, client):
        client.create_certificate(Certificate(name="default.pem", content="c1"))
        assert client.get_subaccount_certificate("default.pem", AccessStrategy.PROVIDER_ONLY) is not None

    def test_create_duplicate_instance_raises_409(self, client):
        cert = Certificate(name="dup.pem", content="c1")
        client.create_certificate(cert, Level.SERVICE_INSTANCE)
        with pytest.raises(HttpError) as exc_info:
            client.create_certificate(cert, Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 409

    def test_create_duplicate_subaccount_raises_409(self, client):
        cert = Certificate(name="dup.pem", content="c1")
        client.create_certificate(cert, Level.SUB_ACCOUNT)
        with pytest.raises(HttpError) as exc_info:
            client.create_certificate(cert, Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 409


class TestUpdateCertificate:
    def test_update_instance_certificate(self, client):
        client.create_certificate(Certificate(name="cert.pem", content="v1"), Level.SERVICE_INSTANCE)
        client.update_certificate(Certificate(name="cert.pem", content="v2"), Level.SERVICE_INSTANCE)
        result = client.get_instance_certificate("cert.pem")
        assert result.content == "v2"

    def test_update_subaccount_certificate(self, client):
        client.create_certificate(Certificate(name="cert.pem", content="v1"), Level.SUB_ACCOUNT)
        client.update_certificate(Certificate(name="cert.pem", content="v2"), Level.SUB_ACCOUNT)
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.PROVIDER_ONLY)
        assert result.content == "v2"

    def test_default_level_is_subaccount(self, client):
        client.create_certificate(Certificate(name="cert.pem", content="v1"))
        client.update_certificate(Certificate(name="cert.pem", content="v2"))
        result = client.get_subaccount_certificate("cert.pem", AccessStrategy.PROVIDER_ONLY)
        assert result.content == "v2"

    def test_update_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_certificate(Certificate(name="ghost.pem", content="c"), Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_update_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.update_certificate(Certificate(name="ghost.pem", content="c"), Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404


class TestDeleteCertificate:
    def test_delete_instance_certificate(self, client):
        client.create_certificate(Certificate(name="del.pem", content="c"), Level.SERVICE_INSTANCE)
        client.delete_certificate("del.pem", Level.SERVICE_INSTANCE)
        assert client.get_instance_certificate("del.pem") is None

    def test_delete_subaccount_certificate(self, client):
        client.create_certificate(Certificate(name="del.pem", content="c"), Level.SUB_ACCOUNT)
        client.delete_certificate("del.pem", Level.SUB_ACCOUNT)
        assert client.get_subaccount_certificate("del.pem", AccessStrategy.PROVIDER_ONLY) is None

    def test_default_level_is_subaccount(self, client):
        client.create_certificate(Certificate(name="del.pem", content="c"))
        client.delete_certificate("del.pem")
        assert client.get_subaccount_certificate("del.pem", AccessStrategy.PROVIDER_ONLY) is None

    def test_delete_missing_instance_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_certificate("ghost.pem", Level.SERVICE_INSTANCE)
        assert exc_info.value.status_code == 404

    def test_delete_missing_subaccount_raises_404(self, client):
        with pytest.raises(HttpError) as exc_info:
            client.delete_certificate("ghost.pem", Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 404
