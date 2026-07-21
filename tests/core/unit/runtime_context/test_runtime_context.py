"""Tests for sap_cloud_sdk.core.runtime_context."""

import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.core.runtime_context import (
    ContextProvider,
    IASContextProvider,
    RequestContext,
    async_sdk_context,
    get_context,
    sdk_context,
    set_context,
)

_PATCH_PARSE = "sap_cloud_sdk.core.runtime_context._providers.parse_token"


# ---------------------------------------------------------------------------
# RequestContext
# ---------------------------------------------------------------------------

class TestRequestContext:
    def test_defaults_are_none(self):
        ctx = RequestContext()
        assert ctx.tenant_id is None
        assert ctx.user_id is None
        assert ctx.trigger_type is None
        assert ctx.extras == {}

    def test_fields_are_settable(self):
        ctx = RequestContext(tenant_id="t1", user_id="u1", trigger_type="ui5")
        assert ctx.tenant_id == "t1"
        assert ctx.user_id == "u1"
        assert ctx.trigger_type == "ui5"

    def test_extras_are_independent_per_instance(self):
        a = RequestContext()
        b = RequestContext()
        a.extras["x"] = 1
        assert "x" not in b.extras


# ---------------------------------------------------------------------------
# get_context / set_context
# ---------------------------------------------------------------------------

class TestGetSetContext:
    def test_get_returns_empty_by_default(self):
        ctx = get_context()
        assert ctx.tenant_id is None
        assert ctx.user_id is None

    def test_set_then_get_returns_same_object(self):
        ctx = RequestContext(tenant_id="abc")
        set_context(ctx)
        assert get_context() is ctx

    def teardown_method(self):
        set_context(RequestContext())


# ---------------------------------------------------------------------------
# sdk_context (sync)
# ---------------------------------------------------------------------------

class TestSdkContext:
    def test_sets_context_inside_block(self):
        ctx = RequestContext(tenant_id="inside")
        with sdk_context(ctx):
            assert get_context().tenant_id == "inside"

    def test_restores_previous_context_after_block(self):
        outer = RequestContext(tenant_id="outer")
        set_context(outer)
        with sdk_context(RequestContext(tenant_id="inner")):
            pass
        assert get_context().tenant_id == "outer"

    def test_restores_on_exception(self):
        outer = RequestContext(tenant_id="outer")
        set_context(outer)
        with pytest.raises(ValueError):
            with sdk_context(RequestContext(tenant_id="inner")):
                raise ValueError("boom")
        assert get_context().tenant_id == "outer"

    def test_yields_the_context(self):
        ctx = RequestContext(tenant_id="t1")
        with sdk_context(ctx) as yielded:
            assert yielded is ctx

    def teardown_method(self):
        set_context(RequestContext())


# ---------------------------------------------------------------------------
# async_sdk_context
# ---------------------------------------------------------------------------

class TestAsyncSdkContext:
    @pytest.mark.anyio
    async def test_sets_context_inside_async_block(self):
        ctx = RequestContext(tenant_id="async-tenant")
        async with async_sdk_context(ctx):
            assert get_context().tenant_id == "async-tenant"

    @pytest.mark.anyio
    async def test_restores_after_async_block(self):
        outer = RequestContext(tenant_id="outer")
        set_context(outer)
        async with async_sdk_context(RequestContext(tenant_id="inner")):
            pass
        assert get_context().tenant_id == "outer"

    @pytest.mark.anyio
    async def test_restores_on_async_exception(self):
        outer = RequestContext(tenant_id="outer")
        set_context(outer)
        with pytest.raises(RuntimeError):
            async with async_sdk_context(RequestContext(tenant_id="inner")):
                raise RuntimeError("boom")
        assert get_context().tenant_id == "outer"

    def teardown_method(self):
        set_context(RequestContext())


# ---------------------------------------------------------------------------
# ContextProvider protocol
# ---------------------------------------------------------------------------

class TestContextProviderProtocol:
    def test_custom_class_satisfies_protocol(self):
        class MyProvider:
            def extract(self, request) -> RequestContext:
                return RequestContext(tenant_id="custom")

        assert isinstance(MyProvider(), ContextProvider)

    def test_class_without_extract_does_not_satisfy_protocol(self):
        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), ContextProvider)


# ---------------------------------------------------------------------------
# IASContextProvider
# ---------------------------------------------------------------------------

def _make_claims(app_tid=None, user_uuid=None):
    claims = MagicMock()
    claims.app_tid = app_tid
    claims.user_uuid = user_uuid
    return claims


def _make_request(headers: dict):
    req = MagicMock()
    req.headers = headers
    return req


class TestIASContextProvider:
    def test_extracts_tenant_and_user(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        req = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(req)
        assert ctx.tenant_id == "t-1"
        assert ctx.user_id == "u-1"

    def test_extracts_trigger_type_from_origin_header(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        req = _make_request({"authorization": "Bearer tok", "x-sap-origin": "ui5"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(req)
        assert ctx.trigger_type == "ui5"

    def test_trigger_type_none_when_header_absent(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        req = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(req)
        assert ctx.trigger_type is None

    def test_stores_full_claims_in_extras(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        req = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(req)
        assert ctx.extras.get("ias.claims") is claims

    def test_returns_empty_context_when_no_auth_header(self):
        req = _make_request({})
        ctx = IASContextProvider().extract(req)
        assert ctx.tenant_id is None
        assert ctx.user_id is None
        assert ctx.extras == {}

    def test_returns_empty_context_on_parse_error(self):
        req = _make_request({"authorization": "Bearer bad"})
        with patch(_PATCH_PARSE, side_effect=ValueError("bad")):
            ctx = IASContextProvider().extract(req)
        assert ctx.tenant_id is None
        assert ctx.user_id is None

    def test_tenant_id_none_when_claim_absent(self):
        claims = _make_claims(app_tid=None, user_uuid="u-1")
        req = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(req)
        assert ctx.tenant_id is None
        assert ctx.user_id == "u-1"

    def test_satisfies_context_provider_protocol(self):
        assert isinstance(IASContextProvider(), ContextProvider)
