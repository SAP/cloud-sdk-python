"""Unit tests for AdmsClient, AsyncAdmsClient, and all API classes."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sap_cloud_sdk.adms import create_client, StructuredQuery
from sap_cloud_sdk.core.odata import FilterExpression
from sap_cloud_sdk.adms._ias_fetcher import IasTokenFetcher
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.adms._models import (
    AllowedDomain,
    BaseType,
    BusinessObjectNodeType,
    CreateAllowedDomainInput,
    CreateBusinessObjectNodeTypeInput,
    CreateDocumentInput,
    CreateDocumentRelationInput,
    CreateDocumentTypeBoTypeMapInput,
    CreateDocumentTypeInput,
    DeleteUserDataJobParameters,
    Document,
    DocumentRelation,
    DocumentType,
    DocumentTypeBusinessObjectTypeMap,
    DraftActivateInput,
    DraftInput,
    JobOutput,
    JobStatus,
    ScanStatus,
    UpdateDocumentInput,
    ZipDownloadJobParameters,
)
from sap_cloud_sdk.adms.client import (
    AdmsClient,
    AsyncAdmsClient,
    _AsyncConfigurationApi,
    _ConfigurationApi,
    _DocumentApi,
    _DocumentRelationApi,
    _JobApi,
    create_async_client,
)
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import (
    ConfigError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)


# ── Shared async helpers ──────────────────────────────────────────────────────


@pytest.fixture
def config() -> AdmsConfig:
    return AdmsConfig(
        service_url="https://adm.example.com",
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="csecret",
    )


def _make_httpx_response(
    status_code: int = 200,
    json_body: Any = None,
    headers: dict | None = None,
) -> httpx.Response:
    import json as _json

    body = _json.dumps(json_body or {}).encode()
    return httpx.Response(
        status_code=status_code,
        content=body,
        headers={"content-type": "application/json", **(headers or {})},
    )


def _make_token_fetcher(config: AdmsConfig) -> IasTokenFetcher:
    fetcher = IasTokenFetcher(config=config)
    fetcher.get_token = MagicMock(return_value="test-bearer-token")  # type: ignore[method-assign]
    fetcher.exchange_token = MagicMock(return_value="user-bearer-token")  # type: ignore[method-assign]
    return fetcher



# ── AdmsClient ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock(spec=ODataHttpTransport)


@pytest.fixture
def mock_admin_http() -> MagicMock:
    return MagicMock(spec=ODataHttpTransport)


@pytest.fixture
def mock_config() -> AdmsConfig:
    return AdmsConfig(
        service_url="https://adm.example.com",
        ias_url="https://ias.example.com",
        client_id="cid",
        client_secret="csecret",
    )


@pytest.fixture
def mock_token_fetcher(mock_config) -> IasTokenFetcher:
    fetcher = IasTokenFetcher(config=mock_config)
    fetcher.get_token = MagicMock(return_value="test-token")  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
    fetcher.exchange_token = MagicMock(return_value="user-token")  # type: ignore[method-assign]  # ty: ignore[invalid-assignment]
    return fetcher


class TestAdmsClientInit:
    def _make_client(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        import requests
        return AdmsClient(
            mock_http, mock_admin_http, mock_http,
            _config=mock_config,
            _session=requests.Session(),
            _token_fetcher=mock_token_fetcher,
        )

    def test_exposes_document_api(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        client = self._make_client(mock_http, mock_admin_http, mock_config, mock_token_fetcher)
        assert isinstance(client.documents, _DocumentApi)

    def test_exposes_relation_api(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        client = self._make_client(mock_http, mock_admin_http, mock_config, mock_token_fetcher)
        assert isinstance(client.relations, _DocumentRelationApi)

    def test_exposes_job_api(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        client = self._make_client(mock_http, mock_admin_http, mock_config, mock_token_fetcher)
        assert isinstance(client.jobs, _JobApi)

    def test_with_user_jwt_returns_new_instance(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        client = self._make_client(mock_http, mock_admin_http, mock_config, mock_token_fetcher)
        user_client = client.with_user_jwt("my-jwt")
        assert user_client is not client

    def test_with_user_jwt_calls_exchange_token(self, mock_http, mock_admin_http, mock_config, mock_token_fetcher):
        client = self._make_client(mock_http, mock_admin_http, mock_config, mock_token_fetcher)
        user_client = client.with_user_jwt("my-jwt")
        # The lambda is lazy — invoke the underlying transport's get_token to verify
        user_client.relations._http._get_token()
        mock_token_fetcher.exchange_token.assert_called_once_with("my-jwt")


class TestCreateClientFactory:
    def test_raises_config_error_on_missing_binding(self):
        with patch(
            "sap_cloud_sdk.adms.client.load_from_env_or_mount",
            side_effect=ConfigError("missing fields"),
        ):
            with pytest.raises(ConfigError, match="missing fields"):
                create_client(instance="nonexistent-instance")

    def test_unexpected_exception_propagates_as_is(self):
        """Real bugs (e.g. ``RuntimeError`` from internal logic) must surface
        as themselves rather than being silently wrapped — wrapping makes
        debugging harder and previously masked SDK programming errors as
        "client creation failed".
        """
        with patch(
            "sap_cloud_sdk.adms.client.load_from_env_or_mount",
            side_effect=RuntimeError("unexpected"),
        ):
            with pytest.raises(RuntimeError, match="unexpected"):
                create_client(instance="bad-instance")

    def test_returns_adms_client_on_success(self):
        mock_config = AdmsConfig(
            service_url="https://adm.example.com",
            ias_url="https://ias.example.com",
            client_id="cid",
            client_secret="cs",
        )
        with patch(
            "sap_cloud_sdk.adms.client.load_from_env_or_mount",
            return_value=mock_config,
        ):
            client = create_client()

        assert isinstance(client, AdmsClient)

    def test_accepts_explicit_config(self):
        mock_config = AdmsConfig(
            service_url="https://adm.example.com",
            ias_url="https://ias.example.com",
            client_id="cid",
            client_secret="cs",
        )
        with patch("sap_cloud_sdk.adms.client.load_from_env_or_mount") as mock_load:
            client = create_client(config=mock_config)

        mock_load.assert_not_called()
        assert isinstance(client, AdmsClient)



# ── AsyncAdmsClient ───────────────────────────────────────────────────────────


class TestAsyncAdmsClient:
    def _make_client(self, config, token_fetcher=None):
        mock_httpx = AsyncMock(spec=httpx.AsyncClient)
        mock_httpx.aclose = AsyncMock()
        fetcher = token_fetcher or _make_token_fetcher(config)
        doc = MagicMock(spec=AsyncODataHttpTransport)
        adm = MagicMock(spec=AsyncODataHttpTransport)
        cfg = MagicMock(spec=AsyncODataHttpTransport)
        return AsyncAdmsClient(
            doc, adm, cfg,
            _config=config,
            _httpx_client=mock_httpx,
            _token_fetcher=fetcher,
        )

    def test_exposes_api_attributes(self, config):
        from sap_cloud_sdk.adms._document_api import _AsyncDocumentApi as _AsyncDocumentApi
        from sap_cloud_sdk.adms._relation_api import _AsyncDocumentRelationApi as _AsyncDocumentRelationApi
        from sap_cloud_sdk.adms._job_api import _AsyncJobApi as _AsyncJobApi
        client = self._make_client(config)
        assert isinstance(client.documents, _AsyncDocumentApi)
        assert isinstance(client.relations, _AsyncDocumentRelationApi)
        assert isinstance(client.jobs, _AsyncJobApi)

    def test_with_user_jwt_returns_new_instance(self, config):
        client = self._make_client(config)
        new_client = client.with_user_jwt("my-jwt")
        assert new_client is not client
        assert new_client._owns_client is False

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        mock_httpx = AsyncMock(spec=httpx.AsyncClient)
        async with AsyncAdmsClient(
            _config=config,
            _httpx_client=mock_httpx,
            _token_fetcher=_make_token_fetcher(config),
        ) as client:
            assert client is not None
        mock_httpx.aclose.assert_called_once()


class TestCreateAsyncClient:
    def test_raises_config_error_when_no_binding(self):
        with patch(
            "sap_cloud_sdk.adms.client.load_from_env_or_mount",
            side_effect=ConfigError("no binding"),
        ):
            with pytest.raises(ConfigError):
                create_async_client(instance="missing")

    def test_returns_async_client(self, config):
        with patch(
            "sap_cloud_sdk.adms.client.load_from_env_or_mount",
            return_value=config,
        ):
            client = create_async_client()
        assert isinstance(client, AsyncAdmsClient)

    def test_accepts_explicit_config(self, config):
        with patch("sap_cloud_sdk.adms.client.load_from_env_or_mount") as mock_load:
            client = create_async_client(config=config)
        mock_load.assert_not_called()
        assert isinstance(client, AsyncAdmsClient)


# ── _AsyncDocumentApi ──────────────────────────────────────────────────────────


class TestAsyncDocumentApi:
    @pytest.mark.asyncio
    async def test_get_document(self, config):
        from sap_cloud_sdk.adms._document_api import _AsyncDocumentApi as _AsyncDocumentApi
        http = MagicMock(spec=AsyncODataHttpTransport)
        http.get = AsyncMock(return_value={
            "DocumentID": "doc-1",
            "DocumentName": "Invoice.pdf",
            "DocumentState": ScanStatus.CLEAN.value,
            "IsActiveEntity": True,
        })
        api = _AsyncDocumentApi(http)
        doc = await api.get("11111111-1111-1111-1111-111111111111")
        assert doc.document_id == "doc-1"
        assert doc.document_name == "Invoice.pdf"

    @pytest.mark.asyncio
    async def test_get_download_url_raises_when_not_clean(self, config):
        from sap_cloud_sdk.adms._document_api import _AsyncDocumentApi as _AsyncDocumentApi
        http = MagicMock(spec=AsyncODataHttpTransport)
        http.get = AsyncMock(return_value={
            "Document": {
                "DocumentID": "doc-1",
                "DocumentState": ScanStatus.PENDING.value,
            }
        })
        api = _AsyncDocumentApi(http)
        with pytest.raises(ScanNotCleanError):
            await api.get_download_url(
                "11111111-1111-1111-1111-111111111111", doc_content_version_id="1.0"
            )


# ── _AsyncDocumentRelationApi ──────────────────────────────────────────────────


class TestAsyncDocumentRelationApi:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self, config):
        from sap_cloud_sdk.adms._relation_api import _AsyncDocumentRelationApi as _AsyncDocumentRelationApi
        http = MagicMock(spec=AsyncODataHttpTransport)
        http.get = AsyncMock(return_value={"value": [{
            "DocumentRelationID": "11111111-1111-1111-1111-111111111111",
            "HostBusinessObjectNodeID": "PO-123",
            "BusinessObjectNodeTypeUniqueID": "PurchaseOrder",
            "IsActiveEntity": True,
        }]})
        api = _AsyncDocumentRelationApi(http)
        relations = await api.get_all()
        assert len(relations) == 1
        assert relations[0].document_relation_id == "11111111-1111-1111-1111-111111111111"


# ── _AsyncJobApi ───────────────────────────────────────────────────────────────


class TestAsyncJobApi:
    @pytest.mark.asyncio
    async def test_get_status(self, config):
        from sap_cloud_sdk.adms._job_api import _AsyncJobApi as _AsyncJobApi
        http = MagicMock(spec=AsyncODataHttpTransport)
        admin_http = MagicMock(spec=AsyncODataHttpTransport)
        http.get = AsyncMock(return_value={"JobID": "job-abc", "JobStatus": "IN_PROGRESS"})
        api = _AsyncJobApi(http, admin_http)
        output = await api.get_status("job-abc")
        assert output.job_id == "job-abc"
        assert output.job_status == JobStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_get_status_admin_service_uses_admin_transport(self, config):
        from sap_cloud_sdk.adms._job_api import _AsyncJobApi as _AsyncJobApi
        http = MagicMock(spec=AsyncODataHttpTransport)
        admin_http = MagicMock(spec=AsyncODataHttpTransport)
        admin_http.get = AsyncMock(return_value={"JobID": "job-del", "JobStatus": "COMPLETED"})
        api = _AsyncJobApi(http, admin_http)
        await api.get_status("job-del", use_admin_service=True)
        admin_http.get.assert_called_once()
        http.get.assert_not_called()

# ── _DocumentApi (sync) ────────────────────────────────────────────────────────


def _doc_http(get_data=None, post_data=None):
    http = MagicMock(spec=ODataHttpTransport)
    http.get.return_value = get_data or {}
    http.post.return_value = post_data or {}
    return http


_CLEAN_DOC = {
    "DocumentID": "doc-1",
    "IsActiveEntity": True,
    "DocumentName": "Invoice.pdf",
    "DocumentBaseType": "D",
    "DocumentTypeID": "INV",
    "DocumentState": "CLEAN",
}
_PENDING_DOC = {**_CLEAN_DOC, "DocumentState": "PENDING"}


class TestDocumentApiGet:
    def test_get_calls_correct_path(self):
        http = _doc_http(get_data=_CLEAN_DOC)
        api = _DocumentApi(http)
        doc = api.get("11111111-1111-1111-1111-111111111111")

        call_path = http.get.call_args[0][0]
        assert "DocumentRelation(" in call_path
        assert "11111111-1111-1111-1111-111111111111" in call_path
        assert "/Document" in call_path
        assert isinstance(doc, Document)

    def test_get_includes_is_active_entity(self):
        http = _doc_http(get_data=_CLEAN_DOC)
        api = _DocumentApi(http)
        api.get("11111111-1111-1111-1111-111111111111")

        call_path = http.get.call_args[0][0]
        assert "IsActiveEntity=true" in call_path

    def test_get_draft_uses_false_active_flag(self):
        http = _doc_http(get_data=_CLEAN_DOC)
        api = _DocumentApi(http)
        api.get("11111111-1111-1111-1111-111111111111", is_active_entity=False)

        call_path = http.get.call_args[0][0]
        assert "IsActiveEntity=false" in call_path


class TestDocumentApiDownloadUrl:
    def test_clean_document_returns_url(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.get.side_effect = [
            {"Document": _CLEAN_DOC},
            {"value": "https://s3.example.com/presigned-url"},
        ]
        api = _DocumentApi(http)
        url = api.get_download_url(
            "11111111-1111-1111-1111-111111111111", doc_content_version_id="1.0"
        )
        assert url == "https://s3.example.com/presigned-url"

    def test_pending_document_raises_scan_not_clean_error(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.get.return_value = {"Document": _PENDING_DOC}
        api = _DocumentApi(http)
        with pytest.raises(ScanNotCleanError, match="PENDING"):
            api.get_download_url(
                "11111111-1111-1111-1111-111111111111", doc_content_version_id="1.0"
            )

    def test_quarantined_document_raises_scan_not_clean_error(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.get.return_value = {"Document": {**_CLEAN_DOC, "DocumentState": "QUARANTINED"}}
        api = _DocumentApi(http)
        with pytest.raises(ScanNotCleanError, match="QUARANTINED"):
            api.get_download_url(
                "11111111-1111-1111-1111-111111111111", doc_content_version_id="1.0"
            )


class TestDocumentApiUpdate:
    def test_update_calls_bound_action(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.post.return_value = {}
        http.get.return_value = _CLEAN_DOC
        api = _DocumentApi(http)

        upd = UpdateDocumentInput(document_name="Renamed.pdf")
        doc = api.update("11111111-1111-1111-1111-111111111111", upd)

        call_path = http.post.call_args[0][0]
        assert "UpdateDocument" in call_path
        assert isinstance(doc, Document)

    def test_update_sends_only_set_fields(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.post.return_value = {}
        http.get.return_value = _CLEAN_DOC
        api = _DocumentApi(http)

        upd = UpdateDocumentInput(document_description="New desc")
        api.update("11111111-1111-1111-1111-111111111111", upd)

        payload = http.post.call_args[1]["json"]
        assert "DocumentDescription" in payload["Document"]
        assert "DocumentName" not in payload["Document"]


class TestDocumentApiVersionOps:
    def test_restore_content_version(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.post.return_value = _CLEAN_DOC
        api = _DocumentApi(http)

        doc = api.restore_content_version(
            "11111111-1111-1111-1111-111111111111", "1.0", comment="Revert"
        )

        call_path = http.post.call_args[0][0]
        assert "RestoreDocumentContentVersion" in call_path
        payload = http.post.call_args[1]["json"]
        assert payload["DocumentContentVersion"]["DocContentVersionID"] == "1.0"
        assert payload["DocumentContentVersion"]["DocContentVersionComment"] == "Revert"
        assert isinstance(doc, Document)

    def test_delete_content_version(self):
        http = MagicMock(spec=ODataHttpTransport)
        http.post.return_value = {}
        api = _DocumentApi(http)

        api.delete_content_version("11111111-1111-1111-1111-111111111111", "2.0")

        call_path = http.post.call_args[0][0]
        assert "DeleteDocumentContentVersion" in call_path
        assert http.post.call_args[1]["json"]["DocContentVersionID"] == "2.0"


class TestDocumentApiGetAll:
    def test_get_all_returns_list(self):
        http = _doc_http(get_data={"value": [{"Document": _CLEAN_DOC}]})
        api = _DocumentApi(http)
        result = api.get_all()

        assert len(result) == 1
        assert isinstance(result[0], Document)
        assert result[0].document_id == "doc-1"

    def test_get_all_empty_response(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        result = api.get_all()
        assert result == []

    def test_get_all_relations_without_document_skipped(self):
        # A relation whose Document navigation property is absent or null is skipped.
        http = _doc_http(
            get_data={"value": [{"Document": None}, {"Document": _CLEAN_DOC}]}
        )
        api = _DocumentApi(http)
        result = api.get_all()
        assert len(result) == 1
        assert result[0].document_id == "doc-1"

    def test_get_all_deduplicates_by_document_id(self):
        # Same document linked to two different relations must appear only once.
        http = _doc_http(
            get_data={"value": [{"Document": _CLEAN_DOC}, {"Document": _CLEAN_DOC}]}
        )
        api = _DocumentApi(http)
        result = api.get_all()
        assert len(result) == 1

    def test_get_all_always_expands_document(self):
        # $expand=Document must always be present, even with no options.
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all()

        _, kwargs = http.get.call_args
        assert "Document" in kwargs["params"]["$expand"]

    def test_get_all_no_params_other_than_expand_by_default(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all()

        _, kwargs = http.get.call_args
        assert set(kwargs["params"].keys()) == {"$expand"}

    def test_get_all_passes_filter(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all(StructuredQuery().filter(FilterExpression.field("DocumentTypeID").eq("INV")))

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$filter"] == "DocumentTypeID eq 'INV'"

    def test_get_all_passes_select(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all(StructuredQuery().select("DocumentID", "DocumentName"))

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$select"] == "DocumentID,DocumentName"

    def test_get_all_merges_caller_expand_with_document(self):
        # If the caller passes expand=["DocumentContentVersion"], the resulting
        # $expand must contain both that value AND "Document".
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all(StructuredQuery().expand("DocumentContentVersion"))

        _, kwargs = http.get.call_args
        expand_parts = kwargs["params"]["$expand"].split(",")
        assert "Document" in expand_parts
        assert "DocumentContentVersion" in expand_parts

    def test_get_all_passes_top_and_skip(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all(StructuredQuery().top(20).skip(10))

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$top"] == "20"
        assert kwargs["params"]["$skip"] == "10"

    def test_get_all_passes_orderby(self):
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all(StructuredQuery().custom("$orderby", "DocumentName asc"))

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$orderby"] == "DocumentName asc"

    def test_get_all_calls_document_relation_entity_set(self):
        # Must query DocumentRelation, not the Document collection directly.
        http = _doc_http(get_data={"value": []})
        api = _DocumentApi(http)
        api.get_all()

        args, _ = http.get.call_args
        assert args[0] == "DocumentRelation"


# ── _DocumentRelationApi (sync) ────────────────────────────────────────────────


def _rel_http(get_data=None, post_data=None):
    http = MagicMock(spec=ODataHttpTransport)
    http.get.return_value = get_data or {}
    http.post.return_value = post_data or {}
    http.delete.return_value = {}
    return http


def _rel_dict(rel_id="11111111-1111-1111-1111-111111111111"):
    return {
        "DocumentRelationID": rel_id,
        "BusinessObjectNodeTypeUniqueID": "PurchaseOrder",
        "HostBusinessObjectNodeID": "PO-001",
    }


class TestDocumentRelationApiGet:
    def test_get_all_no_params(self):
        data = {"value": [_rel_dict("r1"), _rel_dict("r2")]}
        http = _rel_http(get_data=data)
        api = _DocumentRelationApi(http)

        results = api.get_all()

        http.get.assert_called_once()
        assert len(results) == 2
        assert all(isinstance(r, DocumentRelation) for r in results)

    def test_get_all_with_filter_and_expand(self):
        data = {"value": [_rel_dict()]}
        http = _rel_http(get_data=data)
        api = _DocumentRelationApi(http)

        api.get_all(
            StructuredQuery()
            .filter(FilterExpression.field("HostBusinessObjectNodeID").eq("PO-001"))
            .expand("Document")
            .top(10)
        )

        params = http.get.call_args[1]["params"]
        assert params["$filter"] == "HostBusinessObjectNodeID eq 'PO-001'"
        assert params["$expand"] == "Document"
        assert params["$top"] == "10"

    def test_get_single_relation(self):
        http = _rel_http(get_data=_rel_dict("99999999-9999-9999-9999-999999999999"))
        api = _DocumentRelationApi(http)

        rel = api.get("99999999-9999-9999-9999-999999999999")

        call_path = http.get.call_args[0][0]
        assert "99999999-9999-9999-9999-999999999999" in call_path
        assert isinstance(rel, DocumentRelation)

    def test_get_draft_uses_false_flag(self):
        http = _rel_http(get_data=_rel_dict())
        api = _DocumentRelationApi(http)

        api.get("11111111-1111-1111-1111-111111111111", is_active_entity=False)

        call_path = http.get.call_args[0][0]
        assert "IsActiveEntity=false" in call_path


class TestDocumentRelationApiCreate:
    def test_create_calls_correct_action(self):
        http = _rel_http(post_data=_rel_dict())
        api = _DocumentRelationApi(http)

        inp = CreateDocumentRelationInput(
            business_object_node_type_unique_id="PurchaseOrder",
            host_business_object_node_id="PO-001",
            document=CreateDocumentInput(
                document_name="Invoice.pdf",
                document_base_type=BaseType.DOCUMENT,
            ),
        )
        rel = api.create(inp)

        call_path = http.post.call_args[0][0]
        assert call_path == "CreateDocumentWithRelation"
        assert isinstance(rel, DocumentRelation)

    def test_create_sends_correct_payload_structure(self):
        http = _rel_http(post_data=_rel_dict())
        api = _DocumentRelationApi(http)

        inp = CreateDocumentRelationInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
            document=CreateDocumentInput(document_name="f.pdf"),
        )
        api.create(inp)

        payload = http.post.call_args[1]["json"]
        assert "DocumentRelation" in payload
        dr = payload["DocumentRelation"]
        assert dr["BusinessObjectNodeTypeUniqueID"] == "PO"
        assert "Document" in dr


class TestDocumentRelationApiUploadUrls:
    def test_generate_upload_urls_calls_action(self):
        doc_data = {
            "DocumentID": "doc-1",
            "IsActiveEntity": True,
            "DocumentName": "file.pdf",
            "DocumentBaseType": "D",
            "DocumentTypeID": "INV",
            "DocumentState": "PENDING",
            "DocumentContentUploadURLs": ["https://s3.example.com/upload-url"],
        }
        http = _rel_http(post_data=doc_data)
        api = _DocumentRelationApi(http)

        doc = api.generate_upload_urls("11111111-1111-1111-1111-111111111111")

        call_path = http.post.call_args[0][0]
        assert "GenerateDocumentUploadURLs" in call_path
        assert doc.document_content_upload_urls == ["https://s3.example.com/upload-url"]

    def test_complete_multipart_upload(self):
        http = _rel_http()
        api = _DocumentRelationApi(http)

        api.complete_multipart_upload("11111111-1111-1111-1111-111111111111")

        call_path = http.post.call_args[0][0]
        assert "CompleteMultipartUpload" in call_path


class TestDocumentRelationApiLockDelete:
    def test_lock(self):
        http = _rel_http()
        api = _DocumentRelationApi(http)
        api.lock("11111111-1111-1111-1111-111111111111")
        assert "LockDocumentAndRelation" in http.post.call_args[0][0]

    def test_unlock(self):
        http = _rel_http()
        api = _DocumentRelationApi(http)
        api.unlock("11111111-1111-1111-1111-111111111111")
        assert "UnlockDocumentAndRelation" in http.post.call_args[0][0]

    def test_delete_calls_http_delete(self):
        http = _rel_http()
        api = _DocumentRelationApi(http)
        api.delete("11111111-1111-1111-1111-111111111111")
        http.delete.assert_called_once()
        call_path = http.delete.call_args[0][0]
        assert "11111111-1111-1111-1111-111111111111" in call_path


class TestDocumentRelationApiDraftLifecycle:
    def _draft_input(self):
        return DraftInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )

    def test_create_draft(self):
        http = _rel_http(post_data={"value": [_rel_dict()]})
        api = _DocumentRelationApi(http)
        results = api.create_draft(self._draft_input())

        call_path = http.post.call_args[0][0]
        assert call_path == "CreateBusinessObjNodeDraft"
        assert len(results) == 1

    def test_validate_draft(self):
        http = _rel_http(post_data={"value": [_rel_dict()]})
        api = _DocumentRelationApi(http)
        api.validate_draft(self._draft_input())

        assert http.post.call_args[0][0] == "ValidateBusinessObjNodeDraft"

    def test_activate_draft(self):
        http = _rel_http(post_data={"value": [_rel_dict()]})
        api = _DocumentRelationApi(http)

        activate = DraftActivateInput(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        api.activate_draft(activate)

        assert http.post.call_args[0][0] == "ActivateBusinessObjNodeDraft"

    def test_discard_draft(self):
        http = _rel_http()
        api = _DocumentRelationApi(http)
        api.discard_draft(self._draft_input())

        assert http.post.call_args[0][0] == "DiscardBusinessObjNodeDraft"


# ── _ConfigurationApi (sync + async) ──────────────────────────────────────────

_ALLOWED_DOMAIN_DICT = {
    "AllowedDomainID": "33333333-3333-3333-3333-333333333333",
    "AllowedDomainHostName": "storage.example.com",
    "AllowedDomainProtocol": "https",
}

_DOC_TYPE_DICT = {
    "DocumentTypeID": "INVOICE",
    "DocumentTypeName": "Invoice",
    "DocumentTypeDescription": "Vendor invoice documents",
}

_BO_NODE_TYPE_DICT = {
    "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
    "BusinessObjectNodeType": "PurchaseOrder",
    "BusinessObjectNodeTypeName": "Purchase Order",
    "BusinessObjectTypeID": None,
}

_MAPPING_DICT = {
    "DocumentTypeBOTypeMapID": "44444444-4444-4444-4444-444444444444",
    "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
    "DocumentTypeID": "INVOICE",
    "IsDefault": False,
}


def _cfg_sync_http(get_data=None, post_data=None):
    http = MagicMock(spec=ODataHttpTransport)
    http.get.return_value = get_data or {}
    http.post.return_value = post_data or {}
    http.patch.return_value = post_data or {}
    http.delete.return_value = {}
    return http


def _cfg_async_http(get_data=None, post_data=None):
    http = MagicMock(spec=AsyncODataHttpTransport)
    http.get = AsyncMock(return_value=get_data or {})
    http.post = AsyncMock(return_value=post_data or {})
    http.patch = AsyncMock(return_value=post_data or {})
    http.delete = AsyncMock(return_value={})
    return http


class TestConfigurationApiAllowedDomain:
    def test_get_all_returns_list(self):
        http = _cfg_sync_http(get_data={"value": [_ALLOWED_DOMAIN_DICT]})
        api = _ConfigurationApi(http)
        result = api.get_all_allowed_domains()

        assert len(result) == 1
        assert isinstance(result[0], AllowedDomain)
        assert result[0].allowed_domain_id == "33333333-3333-3333-3333-333333333333"
        assert result[0].allowed_domain_host_name == "storage.example.com"
        assert result[0].allowed_domain_protocol == "https"

    def test_get_all_passes_filter(self):
        http = _cfg_sync_http(get_data={"value": []})
        api = _ConfigurationApi(http)
        api.get_all_allowed_domains(
            StructuredQuery().filter(FilterExpression.field("AllowedDomainProtocol").eq("https"))
        )

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$filter"] == "AllowedDomainProtocol eq 'https'"

    def test_get_all_passes_top_and_skip(self):
        http = _cfg_sync_http(get_data={"value": []})
        api = _ConfigurationApi(http)
        api.get_all_allowed_domains(StructuredQuery().top(10).skip(5))

        _, kwargs = http.get.call_args
        assert kwargs["params"]["$top"] == "10"
        assert kwargs["params"]["$skip"] == "5"

    def test_get_all_empty_params_when_no_args(self):
        http = _cfg_sync_http(get_data={"value": []})
        api = _ConfigurationApi(http)
        api.get_all_allowed_domains()

        _, kwargs = http.get.call_args
        assert kwargs["params"] == {}

    def test_create_posts_to_correct_entity(self):
        http = _cfg_sync_http(post_data=_ALLOWED_DOMAIN_DICT)
        api = _ConfigurationApi(http)
        payload = CreateAllowedDomainInput(
            host_name="storage.example.com", protocol="https"
        )
        result = api.create_allowed_domain(payload)

        http.post.assert_called_once()
        args, kwargs = http.post.call_args
        assert args[0] == "AllowedDomain"
        assert kwargs["json"] == {
            "AllowedDomainHostName": "storage.example.com",
            "AllowedDomainProtocol": "https",
        }
        assert isinstance(result, AllowedDomain)

    def test_delete_calls_correct_path(self):
        http = _cfg_sync_http()
        api = _ConfigurationApi(http)
        api.delete_allowed_domain("33333333-3333-3333-3333-333333333333")

        http.delete.assert_called_once()
        call_path = http.delete.call_args[0][0]
        assert "AllowedDomain" in call_path
        assert "33333333-3333-3333-3333-333333333333" in call_path


class TestConfigurationApiDocumentType:
    def test_get_all_returns_list(self):
        http = _cfg_sync_http(get_data={"value": [_DOC_TYPE_DICT]})
        api = _ConfigurationApi(http)
        result = api.get_all_document_types()

        assert len(result) == 1
        assert isinstance(result[0], DocumentType)
        assert result[0].document_type_id == "INVOICE"
        assert result[0].document_type_name == "Invoice"
        assert result[0].document_type_description == "Vendor invoice documents"

    def test_get_all_description_is_optional(self):
        d = {**_DOC_TYPE_DICT, "DocumentTypeDescription": None}
        http = _cfg_sync_http(get_data={"value": [d]})
        api = _ConfigurationApi(http)
        result = api.get_all_document_types()
        assert result[0].document_type_description is None

    def test_create_posts_to_correct_entity(self):
        http = _cfg_sync_http(post_data=_DOC_TYPE_DICT)
        api = _ConfigurationApi(http)
        payload = CreateDocumentTypeInput(
            document_type_id="INVOICE",
            document_type_name="Invoice",
            document_type_description="Vendor invoice documents",
        )
        result = api.create_document_type(payload)

        http.post.assert_called_once()
        args, kwargs = http.post.call_args
        assert args[0] == "DocumentType"
        assert kwargs["json"]["DocumentTypeID"] == "INVOICE"
        assert kwargs["json"]["DocumentTypeName"] == "Invoice"
        assert kwargs["json"]["DocumentTypeDescription"] == "Vendor invoice documents"
        assert isinstance(result, DocumentType)

    def test_create_omits_description_when_none(self):
        http = _cfg_sync_http(post_data=_DOC_TYPE_DICT)
        api = _ConfigurationApi(http)
        payload = CreateDocumentTypeInput(
            document_type_id="INVOICE", document_type_name="Invoice"
        )
        api.create_document_type(payload)

        _, kwargs = http.post.call_args
        assert "DocumentTypeDescription" not in kwargs["json"]

    def test_delete_calls_correct_path(self):
        http = _cfg_sync_http()
        api = _ConfigurationApi(http)
        api.delete_document_type("INVOICE")

        http.delete.assert_called_once()
        call_path = http.delete.call_args[0][0]
        assert "DocumentType" in call_path
        assert "INVOICE" in call_path


class TestConfigurationApiBusinessObjectNodeType:
    def test_get_all_returns_list(self):
        http = _cfg_sync_http(get_data={"value": [_BO_NODE_TYPE_DICT]})
        api = _ConfigurationApi(http)
        result = api.get_all_business_object_types()

        assert len(result) == 1
        assert isinstance(result[0], BusinessObjectNodeType)
        assert result[0].business_object_node_type_unique_id == "bo-uuid-1"
        assert result[0].business_object_node_type == "PurchaseOrder"
        assert result[0].business_object_node_type_name == "Purchase Order"

    def test_create_posts_to_correct_entity(self):
        http = _cfg_sync_http(post_data=_BO_NODE_TYPE_DICT)
        api = _ConfigurationApi(http)
        payload = CreateBusinessObjectNodeTypeInput(
            business_object_node_type="PurchaseOrder",
            business_object_node_type_name="Purchase Order",
            application_tenant_id="tenant-uuid",
        )
        result = api.create_business_object_type(payload)

        http.post.assert_called_once()
        args, kwargs = http.post.call_args
        assert args[0] == "BusinessObjectNodeType"
        assert kwargs["json"]["BusinessObjectNodeType"] == "PurchaseOrder"
        assert kwargs["json"]["BusinessObjectNodeTypeName"] == "Purchase Order"
        assert kwargs["json"]["ApplicationTenantID"] == "tenant-uuid"
        assert isinstance(result, BusinessObjectNodeType)

    def test_delete_uses_unique_id_in_path(self):
        http = _cfg_sync_http()
        api = _ConfigurationApi(http)
        api.delete_business_object_type("bo-uuid-1")

        http.delete.assert_called_once()
        call_path = http.delete.call_args[0][0]
        assert "bo-uuid-1" in call_path


class TestConfigurationApiTypeMappings:
    def test_get_type_mappings_returns_list(self):
        http = _cfg_sync_http(get_data={"value": [_MAPPING_DICT]})
        api = _ConfigurationApi(http)
        result = api.get_type_mappings()

        assert len(result) == 1
        assert isinstance(result[0], DocumentTypeBusinessObjectTypeMap)
        assert (
            result[0].document_type_bo_type_map_id
            == "44444444-4444-4444-4444-444444444444"
        )
        assert result[0].business_object_node_type_unique_id == "bo-uuid-1"
        assert result[0].document_type_id == "INVOICE"
        assert result[0].is_default is False

    def test_create_mapping_posts_correct_payload(self):
        http = _cfg_sync_http(post_data=_MAPPING_DICT)
        api = _ConfigurationApi(http)
        payload = CreateDocumentTypeBoTypeMapInput(
            business_object_node_type_unique_id="bo-uuid-1",
            document_type_id="INVOICE",
            is_default=False,
        )
        result = api.create_type_mapping(payload)

        http.post.assert_called_once()
        args, kwargs = http.post.call_args
        assert args[0] == "DocumentTypeBusinessObjectTypeMap"
        assert kwargs["json"] == {
            "BusinessObjectNodeTypeUniqueID": "bo-uuid-1",
            "DocumentTypeID": "INVOICE",
            "IsDefault": False,
        }
        assert isinstance(result, DocumentTypeBusinessObjectTypeMap)

    def test_delete_mapping_uses_map_id(self):
        http = _cfg_sync_http()
        api = _ConfigurationApi(http)
        api.delete_type_mapping("44444444-4444-4444-4444-444444444444")

        http.delete.assert_called_once()
        call_path = http.delete.call_args[0][0]
        assert "44444444-4444-4444-4444-444444444444" in call_path


class TestAsyncConfigurationApiAllowedDomain:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        http = _cfg_async_http(get_data={"value": [_ALLOWED_DOMAIN_DICT]})
        api = _AsyncConfigurationApi(http)
        result = await api.get_all_allowed_domains()

        assert len(result) == 1
        assert isinstance(result[0], AllowedDomain)
        assert result[0].allowed_domain_id == "33333333-3333-3333-3333-333333333333"

    @pytest.mark.asyncio
    async def test_create_posts_to_correct_entity(self):
        http = _cfg_async_http(post_data=_ALLOWED_DOMAIN_DICT)
        api = _AsyncConfigurationApi(http)
        payload = CreateAllowedDomainInput(
            host_name="storage.example.com", protocol="https"
        )
        result = await api.create_allowed_domain(payload)

        http.post.assert_called_once()
        args, kwargs = http.post.call_args
        assert args[0] == "AllowedDomain"
        assert isinstance(result, AllowedDomain)

    @pytest.mark.asyncio
    async def test_delete_called(self):
        http = _cfg_async_http()
        api = _AsyncConfigurationApi(http)
        await api.delete_allowed_domain("33333333-3333-3333-3333-333333333333")
        http.delete.assert_called_once()


class TestAsyncConfigurationApiDocumentType:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        http = _cfg_async_http(get_data={"value": [_DOC_TYPE_DICT]})
        api = _AsyncConfigurationApi(http)
        result = await api.get_all_document_types()

        assert len(result) == 1
        assert isinstance(result[0], DocumentType)
        assert result[0].document_type_id == "INVOICE"

    @pytest.mark.asyncio
    async def test_create_posts_to_correct_entity(self):
        http = _cfg_async_http(post_data=_DOC_TYPE_DICT)
        api = _AsyncConfigurationApi(http)
        payload = CreateDocumentTypeInput(
            document_type_id="INVOICE", document_type_name="Invoice"
        )
        result = await api.create_document_type(payload)

        http.post.assert_called_once()
        assert isinstance(result, DocumentType)

    @pytest.mark.asyncio
    async def test_delete_called(self):
        http = _cfg_async_http()
        api = _AsyncConfigurationApi(http)
        await api.delete_document_type("INVOICE")
        http.delete.assert_called_once()


class TestAsyncConfigurationApiBusinessObjectNodeType:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        http = _cfg_async_http(get_data={"value": [_BO_NODE_TYPE_DICT]})
        api = _AsyncConfigurationApi(http)
        result = await api.get_all_business_object_types()

        assert len(result) == 1
        assert isinstance(result[0], BusinessObjectNodeType)
        assert result[0].business_object_node_type == "PurchaseOrder"

    @pytest.mark.asyncio
    async def test_create_posts(self):
        http = _cfg_async_http(post_data=_BO_NODE_TYPE_DICT)
        api = _AsyncConfigurationApi(http)
        payload = CreateBusinessObjectNodeTypeInput(
            business_object_node_type="PurchaseOrder",
            business_object_node_type_name="Purchase Order",
            application_tenant_id="tenant-uuid",
        )
        result = await api.create_business_object_type(payload)
        http.post.assert_called_once()
        assert isinstance(result, BusinessObjectNodeType)

    @pytest.mark.asyncio
    async def test_delete_called(self):
        http = _cfg_async_http()
        api = _AsyncConfigurationApi(http)
        await api.delete_business_object_type("bo-uuid-1")
        http.delete.assert_called_once()


class TestAsyncConfigurationApiTypeMappings:
    @pytest.mark.asyncio
    async def test_get_type_mappings_returns_list(self):
        http = _cfg_async_http(get_data={"value": [_MAPPING_DICT]})
        api = _AsyncConfigurationApi(http)
        result = await api.get_type_mappings()

        assert len(result) == 1
        assert isinstance(result[0], DocumentTypeBusinessObjectTypeMap)
        assert result[0].document_type_id == "INVOICE"

    @pytest.mark.asyncio
    async def test_create_mapping_posts(self):
        http = _cfg_async_http(post_data=_MAPPING_DICT)
        api = _AsyncConfigurationApi(http)
        payload = CreateDocumentTypeBoTypeMapInput(
            business_object_node_type_unique_id="bo-uuid-1",
            document_type_id="INVOICE",
        )
        result = await api.create_type_mapping(payload)
        http.post.assert_called_once()
        assert isinstance(result, DocumentTypeBusinessObjectTypeMap)

    @pytest.mark.asyncio
    async def test_delete_called(self):
        http = _cfg_async_http()
        api = _AsyncConfigurationApi(http)
        await api.delete_type_mapping("44444444-4444-4444-4444-444444444444")
        http.delete.assert_called_once()


# ── _JobApi (sync) ─────────────────────────────────────────────────────────────


def _job_http(post_data=None, get_data=None):
    http = MagicMock(spec=ODataHttpTransport)
    http.post.return_value = (
        post_data if post_data is not None else {"JobID": "job-1", "JobStatus": "IN_PROGRESS"}
    )
    http.get.return_value = (
        get_data if get_data is not None else {"JobID": "job-1", "JobStatus": "COMPLETED"}
    )
    return http


class TestJobApiStartZipDownload:
    def test_routes_to_document_service(self):
        http = _job_http()
        admin_http = MagicMock(spec=ODataHttpTransport)
        api = _JobApi(http, admin_http)

        params = ZipDownloadJobParameters(
            business_object_node_type_unique_id="PurchaseOrder",
            host_business_object_node_id="PO-001",
        )
        output = api.start_zip_download(params)

        http.post.assert_called_once()
        admin_http.post.assert_not_called()
        assert isinstance(output, JobOutput)

    def test_payload_has_zip_download_job_type(self):
        http = _job_http()
        api = _JobApi(http, MagicMock(spec=ODataHttpTransport))

        params = ZipDownloadJobParameters(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
            document_relation_ids=[
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222",
            ],
        )
        api.start_zip_download(params)

        payload = http.post.call_args[1]["json"]
        assert payload["JobInput"]["JobType"] == "ZIP_DOWNLOAD"
        assert payload["JobInput"]["JobParameters"]["DocumentRelationIDs"] == [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ]

    def test_returns_job_output(self):
        http = _job_http(post_data={"JobID": "job-42", "JobStatus": "NOT_STARTED"})
        api = _JobApi(http, MagicMock(spec=ODataHttpTransport))

        params = ZipDownloadJobParameters(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        output = api.start_zip_download(params)

        assert output.job_id == "job-42"
        assert output.job_status == JobStatus.NOT_STARTED


class TestJobApiStartDeleteUserData:
    def test_routes_to_admin_service(self):
        http = MagicMock(spec=ODataHttpTransport)
        admin_http = _job_http()
        api = _JobApi(http, admin_http)

        params = DeleteUserDataJobParameters(user_id="user-123")
        api.start_delete_user_data(params)

        admin_http.post.assert_called_once()
        http.post.assert_not_called()

    def test_payload_has_delete_user_data_job_type(self):
        admin_http = _job_http()
        api = _JobApi(MagicMock(spec=ODataHttpTransport), admin_http)

        params = DeleteUserDataJobParameters(user_id="user-456")
        api.start_delete_user_data(params)

        payload = admin_http.post.call_args[1]["json"]
        assert payload["JobInput"]["JobType"] == "DELETE_USER_DATA"
        assert payload["JobInput"]["JobParameters"]["UserID"] == "user-456"


class TestJobApiGetStatus:
    def test_routes_to_document_service_by_default(self):
        http = _job_http()
        admin_http = MagicMock(spec=ODataHttpTransport)
        api = _JobApi(http, admin_http)

        api.get_status("job-1")

        http.get.assert_called_once()
        admin_http.get.assert_not_called()

    def test_routes_to_admin_service_when_flag_set(self):
        http = MagicMock(spec=ODataHttpTransport)
        admin_http = _job_http()
        api = _JobApi(http, admin_http)

        api.get_status("job-1", use_admin_service=True)

        admin_http.get.assert_called_once()
        http.get.assert_not_called()

    def test_path_contains_job_id(self):
        http = _job_http()
        api = _JobApi(http, MagicMock(spec=ODataHttpTransport))

        api.get_status("job-99")

        call_path = http.get.call_args[0][0]
        assert "job-99" in call_path

    def test_returns_job_output(self):
        http = _job_http(
            get_data={
                "JobID": "job-1",
                "JobStatus": "COMPLETED",
                "JobProgressPercentage": 100,
            }
        )
        api = _JobApi(http, MagicMock(spec=ODataHttpTransport))

        output = api.get_status("job-1")

        assert output.job_id == "job-1"
        assert output.job_status == JobStatus.COMPLETED
        assert output.job_progress_percentage == 100


class TestJobPollingWorkflow:
    def test_poll_until_terminal(self):
        responses = [
            {"JobID": "j1", "JobStatus": "IN_PROGRESS"},
            {"JobID": "j1", "JobStatus": "IN_PROGRESS"},
            {"JobID": "j1", "JobStatus": "COMPLETED"},
        ]
        call_count = 0

        http = MagicMock(spec=ODataHttpTransport)
        http.post.return_value = {"JobID": "j1", "JobStatus": "IN_PROGRESS"}

        def side_effect(*args, **kwargs):
            nonlocal call_count
            result = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return result

        http.get.side_effect = side_effect

        api = _JobApi(http, MagicMock(spec=ODataHttpTransport))
        params = ZipDownloadJobParameters(
            business_object_node_type_unique_id="PO",
            host_business_object_node_id="PO-1",
        )
        output = api.start_zip_download(params)

        while not (output.job_status and output.job_status.is_terminal()):
            assert output.job_id is not None
            output = api.get_status(output.job_id)

        assert output.job_status == JobStatus.COMPLETED
        assert http.get.call_count == 3
