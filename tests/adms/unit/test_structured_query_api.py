"""Tests for the StructuredQuery path through ADMS API methods."""

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.adms._configuration_api import _ConfigurationApi
from sap_cloud_sdk.adms._document_api import _DocumentApi
from sap_cloud_sdk.adms._relation_api import _DocumentRelationApi
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._query import StructuredQuery


@pytest.fixture
def mock_http():
    http = MagicMock(spec=ODataHttpTransport)
    http.get.return_value = {"value": []}
    return http


class TestStructuredQueryInConfigApi:
    def test_get_all_allowed_domains_with_structured_query(self, mock_http):
        api = _ConfigurationApi(mock_http)
        q = StructuredQuery().top(5).skip(10)
        api.get_all_allowed_domains(q)
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"] == {"$top": "5", "$skip": "10"}

    def test_get_all_allowed_domains_no_options(self, mock_http):
        api = _ConfigurationApi(mock_http)
        api.get_all_allowed_domains()
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"] == {}

    def test_get_all_document_types_with_filter(self, mock_http):
        api = _ConfigurationApi(mock_http)
        q = StructuredQuery().filter(FilterExpression.field("DocumentTypeID").eq("INV"))
        api.get_all_document_types(q)
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"] == {"$filter": "DocumentTypeID eq 'INV'"}


class TestStructuredQueryInRelationApi:
    def test_get_all_with_structured_query(self, mock_http):
        api = _DocumentRelationApi(mock_http)
        q = StructuredQuery().top(20).select("DocumentRelationID", "IsActiveEntity")
        api.get_all(q)
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"]["$top"] == "20"
        assert kwargs["params"]["$select"] == "DocumentRelationID,IsActiveEntity"

    def test_get_change_logs_with_structured_query(self, mock_http):
        api = _DocumentRelationApi(mock_http)
        q = StructuredQuery().skip(5)
        api.get_change_logs(q)
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"] == {"$skip": "5"}

    def test_get_bo_node_change_logs_no_options(self, mock_http):
        api = _DocumentRelationApi(mock_http)
        api.get_bo_node_change_logs()
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"] == {}


class TestStructuredQueryInDocumentApi:
    def test_get_all_with_structured_query_appends_document_expand(self, mock_http):
        api = _DocumentApi(mock_http)
        q = StructuredQuery().top(10)
        api.get_all(q)
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"]["$top"] == "10"
        assert "Document" in kwargs["params"]["$expand"]

    def test_get_all_preserves_existing_expand(self, mock_http):
        api = _DocumentApi(mock_http)
        q = StructuredQuery().expand("Lock")
        api.get_all(q)
        _, kwargs = mock_http.get.call_args
        expand = kwargs["params"]["$expand"]
        assert "Lock" in expand
        assert "Document" in expand

    def test_get_all_no_options_adds_document_expand(self, mock_http):
        api = _DocumentApi(mock_http)
        api.get_all()
        _, kwargs = mock_http.get.call_args
        assert kwargs["params"]["$expand"] == "Document"
