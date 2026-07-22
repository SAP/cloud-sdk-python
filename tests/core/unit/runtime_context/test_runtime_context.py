"""Tests for sap_cloud_sdk.core.runtime_context."""

import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.core.runtime_context import (
    ContextKey,
    ContextProvider,
    HeaderContextProvider,
    IASContextProvider,
    RuntimeContext,
    RequestEnvelope,
    TRIGGER_TYPE,
    async_sdk_context,
    get_context,
    sdk_context,
    set_context,
)
from sap_cloud_sdk.core.runtime_context.providers._ias import (
    IAS_CLAIMS,
    TENANT_ID,
    USER_ID,
)
from sap_cloud_sdk.core.runtime_context.starlette import _merge

_PATCH_PARSE = "sap_cloud_sdk.core.runtime_context.providers._ias.parse_token"


# ---------------------------------------------------------------------------
# ContextKey
# ---------------------------------------------------------------------------


class TestContextKey:
    def test_repr(self):
        key = ContextKey[str]("my_key")
        assert repr(key) == "ContextKey('my_key')"

    def test_different_instances_are_different_keys(self):
        a = ContextKey[str]("x")
        b = ContextKey[str]("x")
        ctx = RuntimeContext({a: "from-a"})
        assert ctx.get(a) == "from-a"
        assert ctx.get(b) is None


# ---------------------------------------------------------------------------
# RuntimeContext
# ---------------------------------------------------------------------------


class TestRuntimeContext:
    def test_empty_by_default(self):
        ctx = RuntimeContext()
        key = ContextKey[str]("k")
        assert ctx.get(key) is None

    def test_get_returns_set_value(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "v"})
        assert ctx.get(key) == "v"

    def test_with_value_returns_new_instance(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext()
        ctx2 = ctx.with_value(key, "v")
        assert ctx2 is not ctx
        assert ctx.get(key) is None
        assert ctx2.get(key) == "v"

    def test_immutable_original_unaffected_by_with_value(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "original"})
        ctx.with_value(key, "new")
        assert ctx.get(key) == "original"

    def test_repr(self):
        key = ContextKey[str]("tenant_id")
        ctx = RuntimeContext({key: "t-1"})
        assert "tenant_id" in repr(ctx)
        assert "t-1" in repr(ctx)


# ---------------------------------------------------------------------------
# RequestEnvelope
# ---------------------------------------------------------------------------


class TestRequestEnvelope:
    def test_defaults(self):
        env = RequestEnvelope()
        assert env.headers == {}
        assert env.body is None
        assert env.metadata == {}

    def test_headers_independent_per_instance(self):
        a = RequestEnvelope()
        b = RequestEnvelope()
        a.headers["x"] = "1"
        assert "x" not in b.headers


# ---------------------------------------------------------------------------
# get_context / set_context
# ---------------------------------------------------------------------------


class TestGetSetContext:
    def test_get_returns_empty_by_default(self):
        key = ContextKey[str]("k")
        assert get_context().get(key) is None

    def test_set_then_get_returns_same_object(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "v"})
        set_context(ctx)
        assert get_context() is ctx

    def teardown_method(self):
        set_context(RuntimeContext())


# ---------------------------------------------------------------------------
# sdk_context (sync)
# ---------------------------------------------------------------------------


class TestSdkContext:
    def test_sets_context_inside_block(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "inside"})
        with sdk_context(ctx):
            assert get_context().get(key) == "inside"

    def test_restores_previous_context_after_block(self):
        key = ContextKey[str]("k")
        outer = RuntimeContext({key: "outer"})
        set_context(outer)
        with sdk_context(RuntimeContext({key: "inner"})):
            pass
        assert get_context().get(key) == "outer"

    def test_restores_on_exception(self):
        key = ContextKey[str]("k")
        outer = RuntimeContext({key: "outer"})
        set_context(outer)
        with pytest.raises(ValueError):
            with sdk_context(RuntimeContext({key: "inner"})):
                raise ValueError("boom")
        assert get_context().get(key) == "outer"

    def test_yields_the_context(self):
        ctx = RuntimeContext()
        with sdk_context(ctx) as yielded:
            assert yielded is ctx

    def teardown_method(self):
        set_context(RuntimeContext())


# ---------------------------------------------------------------------------
# async_sdk_context
# ---------------------------------------------------------------------------


class TestAsyncSdkContext:
    @pytest.mark.anyio
    async def test_sets_context_inside_async_block(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "async-value"})
        async with async_sdk_context(ctx):
            assert get_context().get(key) == "async-value"

    @pytest.mark.anyio
    async def test_restores_after_async_block(self):
        key = ContextKey[str]("k")
        outer = RuntimeContext({key: "outer"})
        set_context(outer)
        async with async_sdk_context(RuntimeContext({key: "inner"})):
            pass
        assert get_context().get(key) == "outer"

    @pytest.mark.anyio
    async def test_restores_on_async_exception(self):
        key = ContextKey[str]("k")
        outer = RuntimeContext({key: "outer"})
        set_context(outer)
        with pytest.raises(RuntimeError):
            async with async_sdk_context(RuntimeContext({key: "inner"})):
                raise RuntimeError("boom")
        assert get_context().get(key) == "outer"

    def teardown_method(self):
        set_context(RuntimeContext())


# ---------------------------------------------------------------------------
# ContextProvider protocol
# ---------------------------------------------------------------------------


class TestContextProviderProtocol:
    def test_custom_class_satisfies_protocol(self):
        class MyProvider:
            def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
                return RuntimeContext()

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


def _make_envelope(headers: dict) -> RequestEnvelope:
    return RequestEnvelope(headers=headers)


class TestIASContextProvider:
    def test_extracts_tenant_and_user(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        envelope = _make_envelope({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(envelope)
        assert ctx.get(TENANT_ID) == "t-1"
        assert ctx.get(USER_ID) == "u-1"

    def test_does_not_set_trigger_type(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        envelope = _make_envelope(
            {"authorization": "Bearer tok", "x-sap-origin": "ui5"}
        )
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(envelope)
        assert ctx.get(TRIGGER_TYPE) is None

    def test_stores_full_claims(self):
        claims = _make_claims(app_tid="t-1", user_uuid="u-1")
        envelope = _make_envelope({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(envelope)
        assert ctx.get(IAS_CLAIMS) is claims

    def test_returns_empty_context_when_no_auth_header(self):
        envelope = _make_envelope({})
        ctx = IASContextProvider().extract(envelope)
        assert ctx.get(TENANT_ID) is None
        assert ctx.get(USER_ID) is None
        assert ctx.get(IAS_CLAIMS) is None

    def test_returns_empty_context_on_parse_error(self):
        envelope = _make_envelope({"authorization": "Bearer bad"})
        with patch(_PATCH_PARSE, side_effect=ValueError("bad")):
            ctx = IASContextProvider().extract(envelope)
        assert ctx.get(TENANT_ID) is None
        assert ctx.get(USER_ID) is None

    def test_tenant_id_none_when_claim_absent(self):
        claims = _make_claims(app_tid=None, user_uuid="u-1")
        envelope = _make_envelope({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            ctx = IASContextProvider().extract(envelope)
        assert ctx.get(TENANT_ID) is None
        assert ctx.get(USER_ID) == "u-1"

    def test_satisfies_context_provider_protocol(self):
        assert isinstance(IASContextProvider(), ContextProvider)


# ---------------------------------------------------------------------------
# HeaderContextProvider
# ---------------------------------------------------------------------------


class TestHeaderContextProvider:
    def test_extracts_trigger_type(self):
        envelope = _make_envelope({"x-sap-origin": "ui5"})
        ctx = HeaderContextProvider().extract(envelope)
        assert ctx.get(TRIGGER_TYPE) == "ui5"

    def test_trigger_type_none_when_header_absent(self):
        envelope = _make_envelope({})
        ctx = HeaderContextProvider().extract(envelope)
        assert ctx.get(TRIGGER_TYPE) is None

    def test_satisfies_context_provider_protocol(self):
        assert isinstance(HeaderContextProvider(), ContextProvider)


# ---------------------------------------------------------------------------
# _merge
# ---------------------------------------------------------------------------


class TestMerge:
    def test_first_writer_wins_per_key(self):
        key = ContextKey[str]("k")
        a = RuntimeContext({key: "from-a"})
        b = RuntimeContext({key: "from-b"})
        merged = _merge([a, b])
        assert merged.get(key) == "from-a"

    def test_second_fills_missing_from_first(self):
        k1 = ContextKey[str]("k1")
        k2 = ContextKey[str]("k2")
        a = RuntimeContext({k1: "v1"})
        b = RuntimeContext({k2: "v2"})
        merged = _merge([a, b])
        assert merged.get(k1) == "v1"
        assert merged.get(k2) == "v2"

    def test_empty_list_returns_empty_context(self):
        key = ContextKey[str]("k")
        merged = _merge([])
        assert merged.get(key) is None

    def test_single_context_passthrough(self):
        key = ContextKey[str]("k")
        ctx = RuntimeContext({key: "v"})
        merged = _merge([ctx])
        assert merged.get(key) == "v"
