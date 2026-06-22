"""Unit tests for core HTTP — AsyncHttpClient."""

import pytest
import httpx

from unittest.mock import AsyncMock

from sap_cloud_sdk.adms._async_http import AsyncHttpClient, HttpError, NotFoundError


def _make_response(status: int, body: dict | str = "") -> httpx.Response:
    import json

    if isinstance(body, dict):
        content = json.dumps(body).encode()
        content_type = "application/json"
    else:
        content = body.encode()
        content_type = "text/plain"
    return httpx.Response(
        status, content=content, headers={"content-type": content_type}
    )


@pytest.fixture
def mock_httpx_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.aclose = AsyncMock()
    return client


class TestAsyncHttpClientInit:
    def test_base_url_trailing_slash_normalised(self):
        c = AsyncHttpClient(base_url="https://api.example.com/")
        assert c._base_url == "https://api.example.com"

    def test_no_token_getter_is_ok(self):
        c = AsyncHttpClient(base_url="https://api.example.com")
        assert c._get_token is None


class TestAsyncHttpClientContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self, mock_httpx_client):
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        async with c as ctx:
            assert ctx is c

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self, mock_httpx_client):
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        async with c:
            pass
        mock_httpx_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_closes_client_on_exception(self, mock_httpx_client):
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        with pytest.raises(RuntimeError, match="boom"):
            async with c:
                raise RuntimeError("boom")
        mock_httpx_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self):
        # Use a real httpx.AsyncClient — its aclose() must tolerate repeated calls
        # because the context-manager protocol can result in double-cleanup
        # (explicit aclose + __aexit__) in caller code.
        real_client = httpx.AsyncClient()
        c = AsyncHttpClient(base_url="https://api.example.com", client=real_client)
        async with c:
            pass
        # Second close after __aexit__ already ran — must not raise.
        await real_client.aclose()


class TestAsyncHttpClientGet:
    @pytest.mark.asyncio
    async def test_get_injects_bearer_token(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {"items": []})
        c = AsyncHttpClient(
            base_url="https://api.example.com",
            get_token=lambda: "my-token",
            client=mock_httpx_client,
        )
        await c.get("/items")
        headers = mock_httpx_client.request.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-token"

    @pytest.mark.asyncio
    async def test_get_no_token_no_auth_header(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.get("/items")
        headers = mock_httpx_client.request.call_args[1]["headers"]
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_get_constructs_correct_url(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.get("/v1/items")
        url = mock_httpx_client.request.call_args[1]["url"]
        assert url == "https://api.example.com/v1/items"

    @pytest.mark.asyncio
    async def test_get_passes_params(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.get("/items", params={"$top": "5"})
        params = mock_httpx_client.request.call_args[1]["params"]
        assert params == {"$top": "5"}

    @pytest.mark.asyncio
    async def test_404_raises_not_found_error(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(404, "not found")
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        with pytest.raises(NotFoundError):
            await c.get("/items/missing")

    @pytest.mark.asyncio
    async def test_500_raises_http_error(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(500, "server error")
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        with pytest.raises(HttpError) as exc_info:
            await c.get("/items")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_network_error_raises_http_error(self, mock_httpx_client):
        mock_httpx_client.request.side_effect = httpx.RequestError("connection refused")
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        with pytest.raises(HttpError, match="connection refused"):
            await c.get("/items")


class TestAsyncHttpClientPost:
    @pytest.mark.asyncio
    async def test_post_sends_json(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(201, {"id": "new"})
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.post("/items", json={"name": "test"})
        assert mock_httpx_client.request.call_args[1]["json"] == {"name": "test"}
        assert mock_httpx_client.request.call_args[1]["method"] == "POST"


class TestAsyncHttpClientPatch:
    @pytest.mark.asyncio
    async def test_patch_sends_json(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.patch("/items/1", json={"name": "updated"})
        assert mock_httpx_client.request.call_args[1]["method"] == "PATCH"


class TestAsyncHttpClientDelete:
    @pytest.mark.asyncio
    async def test_delete_request(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(204, "")
        c = AsyncHttpClient(
            base_url="https://api.example.com", client=mock_httpx_client
        )
        await c.delete("/items/1")
        assert mock_httpx_client.request.call_args[1]["method"] == "DELETE"


class TestAsyncHttpClientTokenResolution:
    @pytest.mark.asyncio
    async def test_async_get_token_is_awaited(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        token_called = []

        async def async_token():
            token_called.append(True)
            return "async-token"

        c = AsyncHttpClient(
            base_url="https://api.example.com",
            get_token=async_token,
            client=mock_httpx_client,
        )
        await c.get("/items")
        assert token_called == [True]
        headers = mock_httpx_client.request.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer async-token"

    @pytest.mark.asyncio
    async def test_default_headers_merged(self, mock_httpx_client):
        mock_httpx_client.request.return_value = _make_response(200, {})
        c = AsyncHttpClient(
            base_url="https://api.example.com",
            client=mock_httpx_client,
            default_headers={"X-Custom": "value"},
        )
        await c.get("/items")
        headers = mock_httpx_client.request.call_args[1]["headers"]
        assert headers["X-Custom"] == "value"
