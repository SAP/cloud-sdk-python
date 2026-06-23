"""Unit tests for http_client_for_destination factory."""

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.core.http_client._client import HttpClient
from sap_cloud_sdk.core.http_client._factory import http_client_for_destination
from sap_cloud_sdk.destination._models import Destination, DestinationType


def _make_destination(
    url: str | None = "https://example.com",
    dest_type: DestinationType = DestinationType.HTTP,
    headers: dict | None = None,
) -> MagicMock:
    dest = MagicMock(spec=Destination)
    dest.type = dest_type
    dest.url = url
    dest.name = "TEST_DEST"
    dest.get_headers.return_value = headers or {"Authorization": "Bearer tok"}
    return dest


class TestHttpClientForDestination:
    def test_returns_http_client(self) -> None:
        dest = _make_destination()
        client = http_client_for_destination(dest)
        assert isinstance(client, HttpClient)

    def test_base_url_is_destination_url(self) -> None:
        dest = _make_destination(url="https://host.example.com")
        client = http_client_for_destination(dest)
        assert client._base_url == "https://host.example.com"

    def test_trailing_slash_stripped_from_destination_url(self) -> None:
        dest = _make_destination(url="https://host.example.com/")
        client = http_client_for_destination(dest)
        assert client._base_url == "https://host.example.com"

    def test_sub_path_appended_to_base_url(self) -> None:
        dest = _make_destination(url="https://host.example.com")
        client = http_client_for_destination(dest, sub_path="api/v1")
        assert client._base_url == "https://host.example.com/api/v1"

    def test_sub_path_leading_slash_stripped(self) -> None:
        dest = _make_destination(url="https://host.example.com")
        client = http_client_for_destination(dest, sub_path="/api/v1")
        assert client._base_url == "https://host.example.com/api/v1"

    def test_destination_headers_baked_into_session(self) -> None:
        dest = _make_destination(headers={"Authorization": "Bearer xyz", "sap-client": "100"})
        client = http_client_for_destination(dest)
        assert client._session.headers["Authorization"] == "Bearer xyz"
        assert client._session.headers["sap-client"] == "100"

    def test_raises_for_non_http_destination(self) -> None:
        dest = _make_destination(dest_type=DestinationType.RFC)
        with pytest.raises(ValueError, match="HTTP destinations"):
            http_client_for_destination(dest)

    def test_raises_when_destination_has_no_url(self) -> None:
        dest = _make_destination(url=None)
        with pytest.raises(ValueError, match="no URL"):
            http_client_for_destination(dest)
