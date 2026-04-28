"""Tests for StarletteIASTelemetryMiddleware."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
    StarletteIASTelemetryMiddleware,
    _extract_ias_attrs,
    _ATTR_TENANT_ID,
    _ATTR_USER_ID,
)


def _make_claims(app_tid=None, user_uuid=None):
    claims = MagicMock()
    claims.app_tid = app_tid
    claims.user_uuid = user_uuid
    return claims


def _make_request(headers: dict):
    request = MagicMock()
    request.headers = headers
    return request


class TestStarletteIASTelemetryMiddleware:
    def test_register_calls_add_middleware_on_self_app(self):
        app = MagicMock()
        mw = StarletteIASTelemetryMiddleware(app=app)
        mw.register(None)
        app.add_middleware.assert_called_once()

    def test_register_ignores_app_argument(self):
        app = MagicMock()
        other = MagicMock()
        mw = StarletteIASTelemetryMiddleware(app=app)
        mw.register(other)
        app.add_middleware.assert_called_once()
        other.add_middleware.assert_not_called()

    def test_get_attributes_returns_empty_outside_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        assert mw.get_attributes() == {}

    def test_each_instance_has_independent_context_var(self):
        mw1 = StarletteIASTelemetryMiddleware(app=MagicMock())
        mw2 = StarletteIASTelemetryMiddleware(app=MagicMock())
        assert mw1._attrs_var is not mw2._attrs_var

    def test_two_instances_do_not_interfere(self):
        mw1 = StarletteIASTelemetryMiddleware(app=MagicMock())
        mw2 = StarletteIASTelemetryMiddleware(app=MagicMock())

        t1 = mw1._attrs_var.set({_ATTR_TENANT_ID: "tenant-a"})
        t2 = mw2._attrs_var.set({_ATTR_USER_ID: "user-b"})
        try:
            assert mw1.get_attributes() == {_ATTR_TENANT_ID: "tenant-a"}
            assert mw2.get_attributes() == {_ATTR_USER_ID: "user-b"}
        finally:
            mw1._attrs_var.reset(t1)
            mw2._attrs_var.reset(t2)


class TestExtractIasAttrs:
    def _parse(self, claims):
        return lambda token: claims

    def test_extracts_tenant_and_user(self):
        claims = _make_claims(app_tid="t1", user_uuid="u1")
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, self._parse(claims))
        assert result == {_ATTR_TENANT_ID: "t1", _ATTR_USER_ID: "u1"}

    def test_omits_missing_tenant(self):
        claims = _make_claims(app_tid=None, user_uuid="u1")
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, self._parse(claims))
        assert result == {_ATTR_USER_ID: "u1"}
        assert _ATTR_TENANT_ID not in result

    def test_omits_missing_user(self):
        claims = _make_claims(app_tid="t1", user_uuid=None)
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, self._parse(claims))
        assert result == {_ATTR_TENANT_ID: "t1"}
        assert _ATTR_USER_ID not in result

    def test_returns_empty_when_no_auth_header(self):
        request = _make_request({})
        result = _extract_ias_attrs(request, self._parse(_make_claims()))
        assert result == {}

    def test_returns_empty_on_parse_error(self):
        def failing_parse(token):
            raise ValueError("bad token")

        request = _make_request({"authorization": "Bearer bad"})
        result = _extract_ias_attrs(request, failing_parse)
        assert result == {}

    def test_returns_empty_when_both_claims_absent(self):
        claims = _make_claims(app_tid=None, user_uuid=None)
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, self._parse(claims))
        assert result == {}


class TestInnerMiddlewareDispatch:
    def _get_inner_class(self, mw: StarletteIASTelemetryMiddleware):
        app = MagicMock()
        mw.app = app
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.parse_token" if False else "sap_cloud_sdk.ias._token.parse_token"):
            mw.register(None)
        return app.add_middleware.call_args[0][0]

    def _get_inner_class_with_parse(self, mw, parse_fn):
        app = MagicMock()
        mw.app = app
        with patch("sap_cloud_sdk.ias._token.parse_token", parse_fn):
            mw.register(None)
        return app.add_middleware.call_args[0][0]

    @pytest.mark.anyio
    async def test_sets_attrs_in_context_var_during_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(app_tid="tenant-1", user_uuid="user-1")
        inner_cls = self._get_inner_class_with_parse(mw, lambda t: claims)

        request = _make_request({"authorization": "Bearer tok"})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock())
        await inner.dispatch(request, call_next)

        assert captured == {_ATTR_TENANT_ID: "tenant-1", _ATTR_USER_ID: "user-1"}

    @pytest.mark.anyio
    async def test_context_var_reset_after_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(app_tid="t1", user_uuid="u1")
        inner_cls = self._get_inner_class_with_parse(mw, lambda t: claims)

        request = _make_request({"authorization": "Bearer tok"})
        inner = inner_cls(app=MagicMock())
        await inner.dispatch(request, AsyncMock(return_value=MagicMock()))

        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_context_var_reset_on_exception(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(app_tid="t1", user_uuid="u1")
        inner_cls = self._get_inner_class_with_parse(mw, lambda t: claims)

        request = _make_request({"authorization": "Bearer tok"})

        async def raises(req):
            raise RuntimeError("downstream")

        inner = inner_cls(app=MagicMock())
        with pytest.raises(RuntimeError):
            await inner.dispatch(request, raises)

        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_no_auth_header_sets_empty_attrs(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        inner_cls = self._get_inner_class_with_parse(mw, lambda t: _make_claims())

        request = _make_request({})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock())
        await inner.dispatch(request, call_next)

        assert captured == {}

    @pytest.mark.anyio
    async def test_two_instances_independent_during_dispatch(self):
        mw1 = StarletteIASTelemetryMiddleware(app=MagicMock())
        mw2 = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims1 = _make_claims(app_tid="tenant-1", user_uuid=None)
        claims2 = _make_claims(app_tid=None, user_uuid="user-2")
        inner1 = self._get_inner_class_with_parse(mw1, lambda t: claims1)(app=MagicMock())
        inner2 = self._get_inner_class_with_parse(mw2, lambda t: claims2)(app=MagicMock())

        req = _make_request({"authorization": "Bearer tok"})
        captured1, captured2 = {}, {}

        async def next1(r):
            captured1.update(mw1._attrs_var.get())
            return MagicMock()

        async def next2(r):
            captured2.update(mw2._attrs_var.get())
            return MagicMock()

        await inner1.dispatch(req, next1)
        await inner2.dispatch(req, next2)

        assert captured1 == {_ATTR_TENANT_ID: "tenant-1"}
        assert captured2 == {_ATTR_USER_ID: "user-2"}
