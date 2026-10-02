"""Tests for StarletteIASTelemetryMiddleware."""

import logging
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TRIGGER_TYPE, ATTR_SAP_TENANT_ID, ATTR_USER_ID
from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
    StarletteIASTelemetryMiddleware,
    _auto_configure_verifier,
    _verify_and_extract,
)
from sap_cloud_sdk.ias import IASClaims, IASConfigError, IASTokenError, IASVerifier, VerifiedIASClaims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_verified(sap_gtid=None, user_uuid=None) -> VerifiedIASClaims:
    return VerifiedIASClaims(claims=IASClaims(sap_gtid=sap_gtid, user_uuid=user_uuid))


def _make_request(headers: dict):
    request = MagicMock()
    request.headers = headers
    return request


def _passing_verifier(sap_gtid=None, user_uuid=None):
    def verify(token: str) -> VerifiedIASClaims:
        return _make_verified(sap_gtid=sap_gtid, user_uuid=user_uuid)
    return verify


def _failing_verifier(exc=None):
    def verify(token: str) -> VerifiedIASClaims:
        raise (exc or IASTokenError("verification failed"))
    return verify


# ---------------------------------------------------------------------------
# _auto_configure_verifier
# ---------------------------------------------------------------------------

class TestAutoConfigureVerifier:
    def test_returns_verifier_when_env_configured(self):
        mock_verifier = MagicMock(spec=IASVerifier)
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.return_value = mock_verifier
            result = _auto_configure_verifier()
        assert result is mock_verifier

    def test_returns_none_when_config_missing(self):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.side_effect = IASConfigError("no binding found")
            result = _auto_configure_verifier()
        assert result is None

    def test_logs_warning_when_config_missing(self, caplog):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.side_effect = IASConfigError("no IAS binding")
            with caplog.at_level(logging.WARNING):
                _auto_configure_verifier()
        assert any("NOT be stamped" in r.message for r in caplog.records)

    def test_no_warning_when_configured(self, caplog):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.return_value = MagicMock(spec=IASVerifier)
            with caplog.at_level(logging.WARNING):
                _auto_configure_verifier()
        assert not any("NOT be stamped" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# StarletteIASTelemetryMiddleware construction
# ---------------------------------------------------------------------------

class TestStarletteIASTelemetryMiddleware:
    def test_register_calls_add_middleware_on_self_app(self):
        app = MagicMock()
        mw = StarletteIASTelemetryMiddleware(app=app, token_verifier=_passing_verifier())
        mw.register()
        app.add_middleware.assert_called_once()

    def test_get_attributes_returns_empty_outside_request(self):
        mw = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        assert mw.get_attributes() == {}

    def test_each_instance_has_independent_context_var(self):
        mw1 = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        mw2 = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        assert mw1._attrs_var is not mw2._attrs_var

    def test_two_instances_do_not_interfere(self):
        mw1 = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        mw2 = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        t1 = mw1._attrs_var.set({ATTR_SAP_TENANT_ID: "tenant-a"})
        t2 = mw2._attrs_var.set({ATTR_USER_ID: "user-b"})
        try:
            assert mw1.get_attributes() == {ATTR_SAP_TENANT_ID: "tenant-a"}
            assert mw2.get_attributes() == {ATTR_USER_ID: "user-b"}
        finally:
            mw1._attrs_var.reset(t1)
            mw2._attrs_var.reset(t2)

    def test_auto_configure_called_when_no_verifier_given(self):
        mock_verifier = MagicMock(spec=IASVerifier)
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.return_value = mock_verifier
            mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        assert mw._token_verifier is mock_verifier

    def test_auto_configure_failure_sets_none_verifier(self):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.side_effect = IASConfigError("no binding")
            mw = StarletteIASTelemetryMiddleware(app=MagicMock())
        assert mw._token_verifier is None

    def test_no_binding_logs_warning(self, caplog):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            MockV.from_env.side_effect = IASConfigError("no binding")
            with caplog.at_level(logging.WARNING):
                StarletteIASTelemetryMiddleware(app=MagicMock())
        assert any("NOT be stamped" in r.message for r in caplog.records)

    def test_explicit_verifier_bypasses_auto_configure(self):
        with patch("sap_cloud_sdk.core.telemetry.middleware.starlette_a2a.IASVerifier") as MockV:
            explicit = _passing_verifier()
            mw = StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=explicit)
        MockV.from_env.assert_not_called()
        assert mw._token_verifier is explicit

    def test_explicit_verifier_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        assert not any("NOT be stamped" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _verify_and_extract: core security behaviour
# ---------------------------------------------------------------------------

class TestVerifyAndExtract:

    def test_no_verifier_returns_none_claims_and_empty_attrs(self):
        request = _make_request({"authorization": "Bearer tok"})
        claims, attrs = _verify_and_extract(request, None)
        assert claims is None
        assert ATTR_SAP_TENANT_ID not in attrs
        assert ATTR_USER_ID not in attrs

    def test_verified_token_returns_claims_and_stamps_identity(self):
        request = _make_request({"authorization": "Bearer tok"})
        claims, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid="t1", user_uuid="u1"))
        assert claims is not None
        assert claims.sap_gtid == "t1"
        assert attrs[ATTR_SAP_TENANT_ID] == "t1"
        assert attrs[ATTR_USER_ID] == "u1"

    def test_forged_token_returns_none_claims_and_empty_identity(self):
        request = _make_request({"authorization": "Bearer forged"})
        claims, attrs = _verify_and_extract(request, _failing_verifier(IASTokenError("bad sig")))
        assert claims is None
        assert ATTR_SAP_TENANT_ID not in attrs
        assert ATTR_USER_ID not in attrs

    def test_origin_stamped_when_no_verifier(self):
        request = _make_request({"authorization": "Bearer tok", "x-sap-origin": "ui5"})
        _, attrs = _verify_and_extract(request, None)
        assert attrs == {ATTR_SAP_TRIGGER_TYPE: "ui5"}

    def test_origin_stamped_when_verifier_raises(self):
        request = _make_request({"authorization": "Bearer bad", "x-sap-origin": "job"})
        _, attrs = _verify_and_extract(request, _failing_verifier())
        assert attrs[ATTR_SAP_TRIGGER_TYPE] == "job"
        assert ATTR_SAP_TENANT_ID not in attrs

    def test_origin_stamped_on_verified_path(self):
        request = _make_request({"authorization": "Bearer tok", "x-sap-origin": "ui5"})
        _, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid="t1", user_uuid="u1"))
        assert attrs[ATTR_SAP_TRIGGER_TYPE] == "ui5"
        assert attrs[ATTR_SAP_TENANT_ID] == "t1"

    def test_no_auth_header_returns_none_claims(self):
        request = _make_request({})
        claims, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid="t1"))
        assert claims is None
        assert attrs == {}

    def test_no_auth_header_origin_still_stamped(self):
        request = _make_request({"x-sap-origin": "ui5"})
        _, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid="t1"))
        assert attrs == {ATTR_SAP_TRIGGER_TYPE: "ui5"}

    def test_omits_missing_tenant(self):
        request = _make_request({"authorization": "Bearer tok"})
        _, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid=None, user_uuid="u1"))
        assert ATTR_SAP_TENANT_ID not in attrs
        assert attrs[ATTR_USER_ID] == "u1"

    def test_omits_missing_user(self):
        request = _make_request({"authorization": "Bearer tok"})
        _, attrs = _verify_and_extract(request, _passing_verifier(sap_gtid="t1", user_uuid=None))
        assert ATTR_USER_ID not in attrs
        assert attrs[ATTR_SAP_TENANT_ID] == "t1"

    @pytest.mark.parametrize("exc_msg", [
        "alg=none rejected", "HS256 confusion", "unknown kid",
        "wrong issuer", "wrong audience", "token expired", "not yet valid",
    ])
    def test_invalid_token_variants_stamp_nothing(self, exc_msg):
        request = _make_request({"authorization": "Bearer bad"})
        claims, attrs = _verify_and_extract(request, _failing_verifier(IASTokenError(exc_msg)))
        assert claims is None
        assert ATTR_SAP_TENANT_ID not in attrs
        assert ATTR_USER_ID not in attrs


# ---------------------------------------------------------------------------
# Inner middleware dispatch — set_auth_context integration
# ---------------------------------------------------------------------------

class TestInnerMiddlewareDispatch:
    def _get_inner_class_and_kwargs(self, mw: StarletteIASTelemetryMiddleware):
        app = MagicMock()
        mw.app = app
        mw.register()
        args, kwargs = app.add_middleware.call_args
        return args[0], kwargs

    @pytest.mark.anyio
    async def test_sets_attrs_and_auth_context_on_verified_token(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="t1", user_uuid="u1"),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)
        request = _make_request({"authorization": "Bearer tok"})
        captured_attrs = {}
        captured_context = {}

        from sap_cloud_sdk.ias import get_auth_context

        async def call_next(req):
            captured_attrs.update(mw._attrs_var.get())
            ctx = get_auth_context()
            if ctx:
                captured_context["sap_gtid"] = ctx.sap_gtid
            return MagicMock()

        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, call_next)

        assert captured_attrs[ATTR_SAP_TENANT_ID] == "t1"
        assert captured_context.get("sap_gtid") == "t1"

    @pytest.mark.anyio
    async def test_forged_token_clears_auth_context(self):
        from sap_cloud_sdk.ias import get_auth_context, set_auth_context

        set_auth_context(IASClaims(sap_gtid="stale"))
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_failing_verifier(IASTokenError("forged")),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)
        request = _make_request({"authorization": "Bearer forged"})
        captured = {}

        async def call_next(req):
            captured["ctx"] = get_auth_context()
            return MagicMock()

        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, call_next)

        assert captured["ctx"] is None

    @pytest.mark.anyio
    async def test_context_var_reset_after_request(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="t1", user_uuid="u1"),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)
        request = _make_request({"authorization": "Bearer tok"})
        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, AsyncMock(return_value=MagicMock()))
        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_context_var_reset_on_exception(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="t1"),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)
        request = _make_request({"authorization": "Bearer tok"})

        async def raises(req):
            raise RuntimeError("downstream")

        inner = inner_cls(app=MagicMock(), **kwargs)
        with pytest.raises(RuntimeError):
            await inner.dispatch(request, raises)
        assert mw._attrs_var.get() == {}

    @pytest.mark.anyio
    async def test_two_instances_independent_during_dispatch(self):
        mw1 = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="tenant-1", user_uuid=None),
        )
        mw2 = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid=None, user_uuid="user-2"),
        )
        inner1_cls, kwargs1 = self._get_inner_class_and_kwargs(mw1)
        inner2_cls, kwargs2 = self._get_inner_class_and_kwargs(mw2)
        inner1 = inner1_cls(app=MagicMock(), **kwargs1)
        inner2 = inner2_cls(app=MagicMock(), **kwargs2)

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

        assert captured1 == {ATTR_SAP_TENANT_ID: "tenant-1"}
        assert captured2 == {ATTR_USER_ID: "user-2"}
