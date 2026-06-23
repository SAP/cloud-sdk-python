"""Unit tests for EntityKey."""

from __future__ import annotations

import uuid

import pytest

from sap_cloud_sdk.core.odata._entity_key import EntityKey

_GUID = "a1b2c3d4-e5f6-4789-ab12-fedcba987654"
_UUID = uuid.UUID(_GUID)


class TestEntityKeyConstruction:
    def test_single_string_key(self):
        assert (
            str(EntityKey("DocumentType", DocumentTypeID="INVOICE"))
            == "DocumentType('INVOICE')"
        )

    def test_single_guid_key_unquoted(self):
        result = str(EntityKey("AllowedDomain", AllowedDomainID=_UUID))
        assert result == f"AllowedDomain({_GUID})"
        assert "'" not in result

    def test_single_bool_key(self):
        assert str(EntityKey("Entity", Active=True)) == "Entity(true)"
        assert str(EntityKey("Entity", Active=False)) == "Entity(false)"

    def test_compound_key(self):
        result = str(
            EntityKey("DocumentRelation", DocumentRelationID=_UUID, IsActiveEntity=True)
        )
        assert (
            result
            == f"DocumentRelation(DocumentRelationID={_GUID},IsActiveEntity=true)"
        )

    def test_string_escapes_embedded_quote(self):
        result = str(EntityKey("E", ID="O'Brien"))
        assert result == "E('O''Brien')"

    def test_repr(self):
        key = EntityKey("Foo", ID="bar")
        assert repr(key) == "EntityKey(\"Foo('bar')\")"


class TestEntityKeyDivOperator:
    def test_append_navigation_property(self):
        key = EntityKey(
            "DocumentRelation", DocumentRelationID=_UUID, IsActiveEntity=True
        )
        result = str(key / "Document")
        assert (
            result
            == f"DocumentRelation(DocumentRelationID={_GUID},IsActiveEntity=true)/Document"
        )

    def test_chain_multiple_segments(self):
        key = EntityKey("Parent", ID="x")
        result = str(key / "Nav" / "Action")
        assert result == "Parent('x')/Nav/Action"

    def test_div_returns_new_entity_key(self):
        key = EntityKey("E", ID="x")
        nav = key / "Nav"
        assert isinstance(nav, EntityKey)
        assert str(key) == "E('x')"  # original unchanged

    def test_div_strips_leading_slash_from_segment(self):
        key = EntityKey("E", ID="x")
        assert str(key / "/Nav") == "E('x')/Nav"


class TestEntityKeySegment:
    def test_segment_single_string(self):
        assert EntityKey.segment(DocContentVersionID="1.0") == "('1.0')"

    def test_segment_single_guid(self):
        result = EntityKey.segment(ID=_UUID)
        assert result == f"({_GUID})"

    def test_segment_used_as_function_suffix(self):
        key = EntityKey(
            "DocumentRelation", DocumentRelationID=_UUID, IsActiveEntity=True
        )
        result = str(key / "DownloadDocument") + EntityKey.segment(
            DocContentVersionID="1.0"
        )
        assert result == (
            f"DocumentRelation(DocumentRelationID={_GUID},IsActiveEntity=true)"
            "/DownloadDocument('1.0')"
        )


class TestEntityKeyEquality:
    def test_equal_keys(self):
        a = EntityKey("E", ID="x")
        b = EntityKey("E", ID="x")
        assert a == b

    def test_unequal_keys(self):
        assert EntityKey("E", ID="x") != EntityKey("E", ID="y")

    def test_hashable(self):
        key = EntityKey("E", ID="x")
        assert hash(key) == hash(EntityKey("E", ID="x"))
        s = {key}
        assert EntityKey("E", ID="x") in s
