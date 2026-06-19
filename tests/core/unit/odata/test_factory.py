"""Unit tests for odata_transport_from_destination factory."""

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.core.odata._factory import odata_transport_from_destination
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.destination._models import Destination, DestinationType


def _make_destination(
    url: str = "https://s4hana.example.com",
    type_: DestinationType = DestinationType.HTTP,
    headers: dict | None = None,
) -> Destination:
    dest = MagicMock(spec=Destination)
    dest.url = url
    dest.type = type_
    dest.name = "test-destination"
    dest.get_headers.return_value = headers or {"Authorization": "Bearer tok"}
    return dest


class TestOdataTransportFromDestination:
    def test_returns_odata_http_transport(self):
        transport = odata_transport_from_destination(_make_destination())
        assert isinstance(transport, ODataHttpTransport)

    def test_base_url_is_destination_url(self):
        transport = odata_transport_from_destination(
            _make_destination(url="https://host.example.com")
        )
        assert transport._base_url == "https://host.example.com"

    def test_odata_path_appended_to_base_url(self):
        transport = odata_transport_from_destination(
            _make_destination(url="https://host.example.com"),
            odata_path="sap/opu/odata4/svc",
        )
        assert transport._base_url == "https://host.example.com/sap/opu/odata4/svc"

    def test_trailing_slash_stripped_from_destination_url(self):
        transport = odata_transport_from_destination(
            _make_destination(url="https://host.example.com/")
        )
        assert transport._base_url == "https://host.example.com"

    def test_destination_headers_baked_into_session(self):
        dest = _make_destination(headers={"Authorization": "Bearer abc", "sap-client": "100"})
        transport = odata_transport_from_destination(dest)
        assert transport._session.headers["Authorization"] == "Bearer abc"
        assert transport._session.headers["sap-client"] == "100"

    def test_csrf_enabled_by_default(self):
        transport = odata_transport_from_destination(_make_destination())
        assert transport._csrf is not None

    def test_csrf_disabled_when_requested(self):
        transport = odata_transport_from_destination(
            _make_destination(), csrf_enabled=False
        )
        assert transport._csrf is None

    def test_raises_for_non_http_destination(self):
        dest = _make_destination(type_=DestinationType.RFC)
        with pytest.raises(ValueError, match="HTTP destinations"):
            odata_transport_from_destination(dest)

    def test_raises_when_destination_has_no_url(self):
        dest = _make_destination(url="")
        dest.url = None
        with pytest.raises(ValueError, match="no URL"):
            odata_transport_from_destination(dest)
