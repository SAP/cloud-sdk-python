"""Unit tests for OData response deserialization."""

from dataclasses import dataclass
from typing import ClassVar

import pytest

from sap_cloud_sdk.core.odata._models import ODataEntity
from sap_cloud_sdk.core.odata._response import (
    deserialize_collection,
    deserialize_single,
    next_link,
)
from sap_cloud_sdk.core.odata.exceptions import ODataDeserializationError


@dataclass
class _Partner(ODataEntity):
    _entity_set: ClassVar[str] = "BusinessPartnerSet"
    _key_fields: ClassVar[list[str]] = ["PartnerID"]

    PartnerID: str = ""
    Name: str = ""


# ---------------------------------------------------------------------------
# deserialize_single
# ---------------------------------------------------------------------------


class TestDeserializeSingle:
    def test_basic_dict(self):
        result = deserialize_single({"PartnerID": "1", "Name": "Acme"}, _Partner)
        assert result == _Partner(PartnerID="1", Name="Acme")

    def test_unknown_fields_ignored(self):
        result = deserialize_single(
            {"PartnerID": "1", "Name": "Acme", "@odata.etag": '"W/123"', "extra": "x"},
            _Partner,
        )
        assert result == _Partner(PartnerID="1", Name="Acme")

    def test_partial_fields_use_defaults(self):
        result = deserialize_single({"PartnerID": "42"}, _Partner)
        assert result == _Partner(PartnerID="42", Name="")

    def test_odata_envelope_unwrapped(self):
        # {"value": {entity}} envelope — single entity wrapped in value key
        result = deserialize_single(
            {"value": {"PartnerID": "7", "Name": "SAP"}}, _Partner
        )
        assert result == _Partner(PartnerID="7", Name="SAP")

    def test_empty_dict_uses_all_defaults(self):
        result = deserialize_single({}, _Partner)
        assert result == _Partner()

    def test_non_dataclass_raises(self):
        class NotADataclass:
            pass

        with pytest.raises(ODataDeserializationError, match="not a dataclass"):
            deserialize_single({"x": 1}, NotADataclass)

    def test_deserialization_error_on_bad_data(self):
        @dataclass
        class _RequiredArg:
            ID: str

        # No default and no value provided → TypeError in __init__
        with pytest.raises(ODataDeserializationError):
            deserialize_single({}, _RequiredArg)


# ---------------------------------------------------------------------------
# deserialize_collection
# ---------------------------------------------------------------------------


class TestDeserializeCollection:
    def test_basic_collection(self):
        data = {
            "value": [
                {"PartnerID": "1", "Name": "A"},
                {"PartnerID": "2", "Name": "B"},
            ]
        }
        result = deserialize_collection(data, _Partner)
        assert result == [
            _Partner(PartnerID="1", Name="A"),
            _Partner(PartnerID="2", Name="B"),
        ]

    def test_empty_value_list(self):
        assert deserialize_collection({"value": []}, _Partner) == []

    def test_missing_value_key_returns_empty(self):
        assert deserialize_collection({}, _Partner) == []

    def test_unknown_fields_ignored_in_items(self):
        data = {"value": [{"PartnerID": "1", "Name": "A", "@odata.type": "#Partner"}]}
        result = deserialize_collection(data, _Partner)
        assert result == [_Partner(PartnerID="1", Name="A")]

    def test_non_dataclass_raises(self):
        class NotADataclass:
            pass

        with pytest.raises(ODataDeserializationError, match="not a dataclass"):
            deserialize_collection({"value": [{}]}, NotADataclass)

    def test_single_item_collection(self):
        data = {"value": [{"PartnerID": "only", "Name": "One"}]}
        result = deserialize_collection(data, _Partner)
        assert result == [_Partner(PartnerID="only", Name="One")]


# ---------------------------------------------------------------------------
# next_link
# ---------------------------------------------------------------------------


class TestNextLink:
    def test_returns_next_link_when_present(self):
        data = {
            "value": [],
            "@odata.nextLink": "https://host/svc/Items?$skip=50",
        }
        assert next_link(data) == "https://host/svc/Items?$skip=50"

    def test_returns_none_when_absent(self):
        assert next_link({"value": []}) is None

    def test_returns_none_for_empty_dict(self):
        assert next_link({}) is None
