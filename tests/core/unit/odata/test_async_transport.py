"""Unit tests for AsyncODataHttpTransport."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataConnectionError,
    ODataNotFoundError,
    ODataRequestError,
)


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,
    headers: dict | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = b'{"value": []}' if json_data is None else b"data"
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = httpx.Headers(headers or {})
    return resp


def _make_transport(client: httpx.AsyncClient, csrf_enabled: bool = False) -> AsyncODataHttpTransport:
    return AsyncODataHttpTransport(
        base_url="https://example.com/odata/v4/",
        client=client,
        csrf_enabled=csrf_enabled,
    )


@pytest.fixture
def client():
    c = MagicMock(spec=httpx.AsyncClient)
    c.request = AsyncMock()
    c.get = AsyncMock()
    c.aclose = AsyncMock()
    return c


# ---------------------------------------------------------------------------
# URL / params / headers
# ---------------------------------------------------------------------------


class TestRequest:
    @pytest.mark.asyncio
    async def test_builds_correct_url(self, client):
        client.request.return_value = _mock_response(200, {})
        transport = _make_transport(client)
        await transport.request("GET", "EntitySet")
        assert client.request.call_args[1]["url"] == "https://example.com/odata/v4/EntitySet"

    @pytest.mark.asyncio
    async def test_passes_params(self, client):
        client.request.return_value = _mock_response(200, {})
        transport = _make_transport(client)
        await transport.request("GET", "EntitySet", params={"$top": "5"})
        assert client.request.call_args[1]["params"] == {"$top": "5"}

    @pytest.mark.asyncio
    async def test_sets_accept_header(self, client):
        client.request.return_value = _mock_response(200, {})
        transport = _make_transport(client)
        await transport.request("GET", "EntitySet")
        assert client.request.call_args[1]["headers"]["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_returns_parsed_json(self, client):
        client.request.return_value = _mock_response(200, {"value": [{"ID": "1"}]})
        transport = _make_transport(client)
        result = await transport.request("GET", "EntitySet")
        assert result == {"value": [{"ID": "1"}]}

    @pytest.mark.asyncio
    async def test_204_returns_empty_dict(self, client):
        resp = _mock_response(204)
        resp.content = b""
        client.request.return_value = resp
        transport = _make_transport(client)
        assert await transport.request("GET", "EntitySet") == {}

    @pytest.mark.asyncio
    async def test_extra_headers_merged(self, client):
        client.request.return_value = _mock_response(200, {})
        transport = _make_transport(client)
        await transport.request("GET", "EntitySet", headers={"sap-language": "en"})
        assert client.request.call_args[1]["headers"]["sap-language"] == "en"


# ---------------------------------------------------------------------------
# Status-code exception mapping
# ---------------------------------------------------------------------------


class TestStatusCodeErrors:
    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, client):
        client.request.return_value = _mock_response(404)
        transport = _make_transport(client)
        with pytest.raises(ODataNotFoundError):
            await transport.request("GET", "EntitySet")

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, client):
        client.request.return_value = _mock_response(401)
        transport = _make_transport(client)
        with pytest.raises(ODataAuthError):
            await transport.request("GET", "EntitySet")

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self, client):
        client.request.return_value = _mock_response(403)
        transport = _make_transport(client)
        with pytest.raises(ODataAuthError):
            await transport.request("GET", "EntitySet")

    @pytest.mark.asyncio
    async def test_500_raises_request_error(self, client):
        client.request.return_value = _mock_response(500)
        transport = _make_transport(client)
        with pytest.raises(ODataRequestError):
            await transport.request("GET", "EntitySet")

    @pytest.mark.asyncio
    async def test_connection_error_raises_odata_connection_error(self, client):
        client.request.side_effect = httpx.RequestError("connection refused")
        transport = _make_transport(client)
        with pytest.raises(ODataConnectionError):
            await transport.request("GET", "EntitySet")


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


class TestCsrf:
    @pytest.mark.asyncio
    async def test_csrf_attached_on_post(self, client):
        csrf_resp = _mock_response(200, {}, headers={"X-CSRF-Token": "csrf-tok"})
        client.get.return_value = csrf_resp
        client.request.return_value = _mock_response(201, {"ID": "1"})

        transport = _make_transport(client, csrf_enabled=True)
        await transport.request("POST", "EntitySet", json={"Name": "X"})

        assert client.request.call_args[1]["headers"]["X-CSRF-Token"] == "csrf-tok"

    @pytest.mark.asyncio
    async def test_no_csrf_on_get(self, client):
        client.request.return_value = _mock_response(200, {})

        transport = _make_transport(client, csrf_enabled=True)
        await transport.request("GET", "EntitySet")

        assert "X-CSRF-Token" not in client.request.call_args[1]["headers"]
        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_csrf_token_cached(self, client):
        csrf_resp = _mock_response(200, {}, headers={"X-CSRF-Token": "tok"})
        client.get.return_value = csrf_resp
        client.request.return_value = _mock_response(201, {"ID": "1"})

        transport = _make_transport(client, csrf_enabled=True)
        await transport.request("POST", "EntitySet", json={"A": 1})
        await transport.request("POST", "EntitySet", json={"B": 2})

        assert client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_csrf_retry_on_403(self, client):
        csrf_resp1 = _mock_response(200, {}, headers={"X-CSRF-Token": "tok1"})
        csrf_resp2 = _mock_response(200, {}, headers={"X-CSRF-Token": "tok2"})
        client.get.side_effect = [csrf_resp1, csrf_resp2]
        client.request.side_effect = [_mock_response(403), _mock_response(201, {"ID": "1"})]

        transport = _make_transport(client, csrf_enabled=True)
        await transport.request("POST", "EntitySet", json={"Name": "X"})

        assert client.request.call_count == 2
        # Second call must use the fresh token
        assert client.request.call_args_list[1][1]["headers"]["X-CSRF-Token"] == "tok2"

    @pytest.mark.asyncio
    async def test_csrf_fetch_missing_token_raises(self, client):
        from sap_cloud_sdk.core.odata.exceptions import ODataCsrfError

        csrf_resp = _mock_response(200, {}, headers={})
        client.get.return_value = csrf_resp

        transport = _make_transport(client, csrf_enabled=True)
        with pytest.raises(ODataCsrfError):
            await transport.request("POST", "EntitySet", json={})

    @pytest.mark.asyncio
    async def test_csrf_network_error_raises(self, client):
        from sap_cloud_sdk.core.odata.exceptions import ODataCsrfError

        client.get.side_effect = httpx.RequestError("timeout")

        transport = _make_transport(client, csrf_enabled=True)
        with pytest.raises(ODataCsrfError):
            await transport.request("POST", "EntitySet", json={})


# ---------------------------------------------------------------------------
# absolute_url
# ---------------------------------------------------------------------------


class TestAbsoluteUrl:
    def test_builds_url_with_trailing_slash(self):
        t = AsyncODataHttpTransport("https://host/svc/", MagicMock(), csrf_enabled=False)
        assert t.absolute_url("EntitySet") == "https://host/svc/EntitySet"

    def test_strips_leading_slash_from_path(self):
        t = AsyncODataHttpTransport("https://host/svc", MagicMock(), csrf_enabled=False)
        assert t.absolute_url("/EntitySet") == "https://host/svc/EntitySet"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aclose_called_on_exit(self, client):
        transport = _make_transport(client)
        async with transport:
            pass
        client.aclose.assert_called_once()
