"""Unit tests for CRUD request builders."""

from dataclasses import dataclass
from typing import Any, ClassVar
from unittest.mock import MagicMock

import pytest
import requests

from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._models import ODataEntity
from sap_cloud_sdk.core.odata._request_builders import (
    CreateRequestBuilder,
    DeleteRequestBuilder,
    GetAllRequestBuilder,
    GetByKeyRequestBuilder,
    UpdateRequestBuilder,
    _build_key_segment,
    _entity_set_path,
)
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _Partner(ODataEntity):
    _entity_set: ClassVar[str] = "BusinessPartnerSet"
    _key_fields: ClassVar[list[str]] = ["PartnerID"]

    PartnerID: str = ""
    Name: str = ""


def _make_transport(session: requests.Session) -> ODataHttpTransport:
    return ODataHttpTransport(
        base_url="https://host/svc",
        session=session,
        csrf_enabled=False,
    )


def _mock_response(status_code: int = 200, json_data: Any = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.content = b"data"
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# Helpers tests
# ---------------------------------------------------------------------------


class TestBuildKeySegment:
    def test_single_string_key(self):
        assert _build_key_segment({"ID": "x"}) == "('x')"

    def test_single_int_key(self):
        assert _build_key_segment({"ID": 1}) == "(1)"

    def test_composite_key(self):
        seg = _build_key_segment({"ID": "x", "Ver": 1})
        assert seg == "(ID='x',Ver=1)"


class TestEntitySetPath:
    def test_reads_entity_set_classvar(self):
        assert _entity_set_path(_Partner) == "BusinessPartnerSet"

    def test_falls_back_to_class_name(self):
        @dataclass
        class NoMeta:
            ID: str = ""

        assert _entity_set_path(NoMeta) == "NoMeta"


# ---------------------------------------------------------------------------
# GetAllRequestBuilder
# ---------------------------------------------------------------------------


class TestGetAllRequestBuilder:
    def test_execute_calls_correct_path(self):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _mock_response(200, {"value": [{"PartnerID": "1", "Name": "A"}]})
        transport = _make_transport(session)

        results = GetAllRequestBuilder(transport, _Partner).execute()

        url = session.request.call_args[1]["url"]
        assert "BusinessPartnerSet" in url
        assert results == [_Partner(PartnerID="1", Name="A")]

    def test_execute_passes_query_params(self):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _mock_response(200, {"value": []})
        transport = _make_transport(session)

        (
            GetAllRequestBuilder(transport, _Partner)
            .select("PartnerID")
            .top(5)
            .filter(FilterExpression.field("Name").eq("Acme"))
            .execute()
        )

        params = session.request.call_args[1]["params"]
        assert params["$select"] == "PartnerID"
        assert params["$top"] == "5"
        assert params["$filter"] == "Name eq 'Acme'"


# ---------------------------------------------------------------------------
# GetByKeyRequestBuilder
# ---------------------------------------------------------------------------


class TestGetByKeyRequestBuilder:
    def test_execute_builds_key_in_path(self):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _mock_response(200, {"PartnerID": "42", "Name": "X"})
        transport = _make_transport(session)

        result = GetByKeyRequestBuilder(
            transport, _Partner, {"PartnerID": "42"}
        ).execute()

        url = session.request.call_args[1]["url"]
        assert "BusinessPartnerSet" in url
        assert "'42'" in url
        assert result == _Partner(PartnerID="42", Name="X")


# ---------------------------------------------------------------------------
# CreateRequestBuilder
# ---------------------------------------------------------------------------


class TestCreateRequestBuilder:
    def test_execute_posts_entity_and_returns_result(self):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _mock_response(201, {"PartnerID": "new", "Name": "New"})
        transport = _make_transport(session)

        entity = _Partner(PartnerID="new", Name="New")
        result = CreateRequestBuilder(transport, entity).execute()

        assert session.request.call_args[1]["method"] == "POST"
        assert result == _Partner(PartnerID="new", Name="New")


# ---------------------------------------------------------------------------
# UpdateRequestBuilder
# ---------------------------------------------------------------------------


class TestUpdateRequestBuilder:
    def test_execute_patches_by_default(self):
        session = MagicMock(spec=requests.Session)
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        transport = _make_transport(session)

        entity = _Partner(PartnerID="1", Name="Updated")
        UpdateRequestBuilder(transport, entity).execute()

        assert session.request.call_args[1]["method"] == "PATCH"

    def test_replace_uses_put(self):
        session = MagicMock(spec=requests.Session)
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        transport = _make_transport(session)

        entity = _Partner(PartnerID="1", Name="Updated")
        UpdateRequestBuilder(transport, entity).replace().execute()

        assert session.request.call_args[1]["method"] == "PUT"

    def test_etag_sent_in_if_match_header(self):
        session = MagicMock(spec=requests.Session)
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        transport = _make_transport(session)

        entity = _Partner(PartnerID="1", Name="X")
        UpdateRequestBuilder(transport, entity, etag='"W/123"').execute()

        headers = session.request.call_args[1]["headers"]
        assert headers["If-Match"] == '"W/123"'


# ---------------------------------------------------------------------------
# DeleteRequestBuilder
# ---------------------------------------------------------------------------


class TestDeleteRequestBuilder:
    def test_execute_sends_delete(self):
        session = MagicMock(spec=requests.Session)
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        transport = _make_transport(session)

        DeleteRequestBuilder(transport, _Partner, {"PartnerID": "1"}).execute()

        assert session.request.call_args[1]["method"] == "DELETE"
        url = session.request.call_args[1]["url"]
        assert "BusinessPartnerSet" in url
