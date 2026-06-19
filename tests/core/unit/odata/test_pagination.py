"""Unit tests for ODataPageIterator."""

from typing import Any

import pytest

from sap_cloud_sdk.core.odata._pagination import ODataPageIterator
from sap_cloud_sdk.core.odata.exceptions import ODataDeserializationError


from dataclasses import dataclass


@dataclass
class _Item:
    id: str = ""
    name: str = ""


class TestODataPageIterator:
    def test_single_page_no_next_link(self):
        pages = [{"value": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]}]
        urls: list[str] = []

        def fetch(url: str) -> dict[str, Any]:
            urls.append(url)
            return pages.pop(0)

        iterator = ODataPageIterator(fetch, _Item, "https://host/svc/Items")
        result = list(iterator)

        assert len(result) == 1
        assert result[0] == [_Item(id="1", name="A"), _Item(id="2", name="B")]
        assert urls == ["https://host/svc/Items"]

    def test_multi_page_follows_next_link(self):
        responses = [
            {
                "value": [{"id": "1", "name": "A"}],
                "@odata.nextLink": "https://host/svc/Items?$skip=1",
            },
            {"value": [{"id": "2", "name": "B"}]},
        ]

        def fetch(url: str) -> dict[str, Any]:
            return responses.pop(0)

        iterator = ODataPageIterator(fetch, _Item, "https://host/svc/Items")
        pages = list(iterator)
        assert len(pages) == 2
        assert pages[0] == [_Item(id="1", name="A")]
        assert pages[1] == [_Item(id="2", name="B")]

    def test_entities_yields_individual_items(self):
        responses = [
            {
                "value": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
                "@odata.nextLink": "https://host/next",
            },
            {"value": [{"id": "3", "name": "C"}]},
        ]

        def fetch(url: str) -> dict[str, Any]:
            return responses.pop(0)

        iterator = ODataPageIterator(fetch, _Item, "https://host/svc/Items")
        entities = list(iterator.entities())
        assert entities == [
            _Item(id="1", name="A"),
            _Item(id="2", name="B"),
            _Item(id="3", name="C"),
        ]

    def test_empty_collection(self):
        def fetch(url: str) -> dict[str, Any]:
            return {"value": []}

        iterator = ODataPageIterator(fetch, _Item, "https://host/svc/Items")
        assert list(iterator) == [[]]
