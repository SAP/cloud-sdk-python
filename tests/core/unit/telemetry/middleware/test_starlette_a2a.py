"""Tests for StarletteIASTelemetryMiddleware."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TENANT_ID, ATTR_USER_ID
from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
    StarletteIASTelemetryMiddleware,
    _extract_ias_attrs,
)

_PATCH_PARSE = "sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.parse_token"


def _make_claims(sap_gtid=None, user_uuid=None):
    claims = MagicMock()
    claims.sap_gtid = sap_gtid
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
        mw.register()
        app.add_middleware.assert_called_once()

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

        t1 = mw1._attrs_var.set({ATTR_SAP_TENANT_ID: "tenant-a"})
        t2 = mw2._attrs_var.set({ATTR_USER_ID: "user-b"})
        try:
            assert mw1.get_attributes() == {ATTR_SAP_TENANT_ID: "tenant-a"}
            assert mw2.get_attributes() == {ATTR_USER_ID: "user-b"}
        finally:
            mw1._attrs_var.reset(t1)
            mw2._attrs_var.reset(t2)


class TestExtractIasAttrs:
    def test_extracts_tenant_and_user(self):
        claims = _make_claims(sap_gtid="t1", user_uuid="u1")
        request = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            result = _extract_ias_attrs(request)
        assert result == {ATTR_SAP_TENANT_ID: "t1", ATTR_USER_ID: "u1"}

    def test_omits_missing_tenant(self):
        claims = _make_claims(sap_gtid=None, user_uuid="u1")
        request = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            result = _extract_ias_attrs(request)
        assert result == {ATTR_USER_ID: "u1"}
        assert ATTR_SAP_TENANT_ID not in result

    def test_omits_missing_user(self):
        claims = _make_claims(sap_gtid="t1", user_uuid=None)
        request = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            result = _extract_ias_attrs(request)
        assert result == {ATTR_SAP_TENANT_ID: "t1"}
        assert ATTR_USER_ID not in result

    def test_returns_empty_when_no_auth_header(self):
        request = _make_request({})
        with patch(_PATCH_PARSE) as mock_parse:
            result = _extract_ias_attrs(request)
        mock_parse.assert_not_called()
        assert result == {}

    def test_returns_empty_on_parse_error(self):
        request = _make_request({"authorization": "Bearer bad"})
        with patch(_PATCH_PARSE, side_effect=ValueError("bad token")):
            result = _extract_ias_attrs(request)
        assert result == {}

    def test_returns_empty_when_both_claims_absent(self):
        claims = _make_claims(sap_gtid=None, user_uuid=None)
        request = _make_request({"authorization": "Bearer tok"})
        with patch(_PATCH_PARSE, return_value=claims):
            result = _extract_ias_attrs(request)
        assert result == {}


class TestInnerMiddlewareDispatch:
    def _get_inner_class(self, mw: StarletteIASTelemetryMiddleware):
        app = MagicMock()
        mw.app = app
        mw.register()
        return app.add_middleware.call_args[0][0]

    @pytest.mark.anyio
    async def test_sets_attrs_in_context_var_during_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(sap_gtid="tenant-1", user_uuid="user-1")
        inner_cls = self._get_inner_class(mw)

        request = _make_request({"authorization": "Bearer tok"})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock())
        with patch(_PATCH_PARSE, lambda t: claims):
            await inner.dispatch(request, call_next)

        assert captured == {ATTR_SAP_TENANT_ID: "tenant-1", ATTR_USER_ID: "user-1"}

    @pytest.mark.anyio
    async def test_context_var_reset_after_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(sap_gtid="t1", user_uuid="u1")
        inner_cls = self._get_inner_class(mw)

        request = _make_request({"authorization": "Bearer tok"})
        inner = inner_cls(app=MagicMock())
        with patch(_PATCH_PARSE, lambda t: claims):
            await inner.dispatch(request, AsyncMock(return_value=MagicMock()))

        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_context_var_reset_on_exception(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        claims = _make_claims(sap_gtid="t1", user_uuid="u1")
        inner_cls = self._get_inner_class(mw)

        request = _make_request({"authorization": "Bearer tok"})

        async def raises(req):
            raise RuntimeError("downstream")

        inner = inner_cls(app=MagicMock())
        with patch(_PATCH_PARSE, lambda t: claims):
            with pytest.raises(RuntimeError):
                await inner.dispatch(request, raises)

        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_no_auth_header_sets_empty_attrs(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        inner_cls = self._get_inner_class(mw)

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
        claims1 = _make_claims(sap_gtid="tenant-1", user_uuid=None)
        claims2 = _make_claims(sap_gtid=None, user_uuid="user-2")
        inner1 = self._get_inner_class(mw1)(app=MagicMock())
        inner2 = self._get_inner_class(mw2)(app=MagicMock())

        req = _make_request({"authorization": "Bearer tok"})
        captured1, captured2 = {}, {}

        async def next1(r):
            captured1.update(mw1._attrs_var.get())
            return MagicMock()

        async def next2(r):
            captured2.update(mw2._attrs_var.get())
            return MagicMock()

        with patch(_PATCH_PARSE, lambda t: claims1):
            await inner1.dispatch(req, next1)
        with patch(_PATCH_PARSE, lambda t: claims2):
            await inner2.dispatch(req, next2)

        assert captured1 == {ATTR_SAP_TENANT_ID: "tenant-1"}
        assert captured2 == {ATTR_USER_ID: "user-2"}
