"""Tests for StarletteIASTelemetryMiddleware."""

import logging
import pytest
from unittest.mock import MagicMock, AsyncMock

from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TRIGGER_TYPE, ATTR_SAP_TENANT_ID, ATTR_USER_ID
from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
    StarletteIASTelemetryMiddleware,
    _extract_ias_attrs,
)
from sap_cloud_sdk.ias import IASClaims, IASTokenError, VerifiedIASClaims


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
    """Returns a verifier that always succeeds with the given claim values."""
    def verify(token: str) -> VerifiedIASClaims:
        return _make_verified(sap_gtid=sap_gtid, user_uuid=user_uuid)
    return verify


def _failing_verifier(exc=None):
    """Returns a verifier that always raises (simulates invalid token)."""
    def verify(token: str) -> VerifiedIASClaims:
        raise (exc or IASTokenError("verification failed"))
    return verify


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

    def test_no_verifier_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=None)
        assert any("token_verifier" in r.message for r in caplog.records)

    def test_verifier_provided_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            StarletteIASTelemetryMiddleware(app=MagicMock(), token_verifier=_passing_verifier())
        assert not any("token_verifier" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _extract_ias_attrs: core security behaviour
# ---------------------------------------------------------------------------

class TestExtractIasAttrs:

    # --- fail-closed default (no verifier) ---

    def test_no_verifier_stamps_nothing(self):
        request = _make_request({"authorization": "Bearer some.jwt.token"})
        result = _extract_ias_attrs(request, None)
        assert ATTR_SAP_TENANT_ID not in result
        assert ATTR_USER_ID not in result

    def test_no_verifier_with_auth_returns_empty(self):
        request = _make_request({"authorization": "Bearer tok"})
        assert _extract_ias_attrs(request, None) == {}

    # --- origin header is independent of verification ---

    def test_origin_stamped_when_no_verifier(self):
        request = _make_request({"authorization": "Bearer tok", "x-sap-origin": "ui5"})
        result = _extract_ias_attrs(request, None)
        assert result == {ATTR_SAP_TRIGGER_TYPE: "ui5"}
        assert ATTR_SAP_TENANT_ID not in result

    def test_origin_stamped_when_verifier_raises(self):
        request = _make_request({
            "authorization": "Bearer forged.jwt",
            "x-sap-origin": "job",
        })
        result = _extract_ias_attrs(request, _failing_verifier())
        assert result == {ATTR_SAP_TRIGGER_TYPE: "job"}
        assert ATTR_SAP_TENANT_ID not in result
        assert ATTR_USER_ID not in result

    def test_origin_stamped_on_verified_path(self):
        request = _make_request({
            "authorization": "Bearer tok",
            "x-sap-origin": "ui5",
        })
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1", user_uuid="u1"))
        assert result[ATTR_SAP_TRIGGER_TYPE] == "ui5"
        assert result[ATTR_SAP_TENANT_ID] == "t1"
        assert result[ATTR_USER_ID] == "u1"

    def test_origin_omitted_when_absent(self):
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1"))
        assert ATTR_SAP_TRIGGER_TYPE not in result

    # --- verified path stamps identity ---

    def test_verified_token_stamps_tenant_and_user(self):
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1", user_uuid="u1"))
        assert result[ATTR_SAP_TENANT_ID] == "t1"
        assert result[ATTR_USER_ID] == "u1"

    def test_omits_missing_tenant_on_verified_path(self):
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid=None, user_uuid="u1"))
        assert result == {ATTR_USER_ID: "u1"}
        assert ATTR_SAP_TENANT_ID not in result

    def test_omits_missing_user_on_verified_path(self):
        request = _make_request({"authorization": "Bearer tok"})
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1", user_uuid=None))
        assert result == {ATTR_SAP_TENANT_ID: "t1"}
        assert ATTR_USER_ID not in result

    # --- regression: forged / invalid tokens must not stamp identity ---

    def test_forged_attacker_token_stamps_nothing(self):
        """Attacker-signed token with victim tenant/user must not populate identity attrs."""
        request = _make_request({"authorization": "Bearer attacker.signed.jwt"})
        result = _extract_ias_attrs(request, _failing_verifier(IASTokenError("bad signature")))
        assert ATTR_SAP_TENANT_ID not in result
        assert ATTR_USER_ID not in result

    def test_verification_failure_does_not_inherit_victim_identity(self):
        """Even if the token carries victim-named claims, a failed verifier means no stamp."""
        request = _make_request({"authorization": "Bearer victim.claimed.token"})
        result = _extract_ias_attrs(request, _failing_verifier(IASTokenError("alg=none rejected")))
        assert result == {}  # no spillover of any kind

    @pytest.mark.parametrize("exc_msg", [
        "alg=none rejected",
        "HS256 confusion attack",
        "unknown kid",
        "wrong issuer",
        "wrong audience",
        "token expired",
        "token not yet valid",
        "signature verification failed",
    ])
    def test_invalid_token_variants_stamp_nothing(self, exc_msg):
        request = _make_request({"authorization": "Bearer bad.token"})
        result = _extract_ias_attrs(request, _failing_verifier(IASTokenError(exc_msg)))
        assert ATTR_SAP_TENANT_ID not in result
        assert ATTR_USER_ID not in result

    # --- no auth header ---

    def test_returns_empty_when_no_auth_header(self):
        request = _make_request({})
        assert _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1")) == {}

    def test_no_auth_header_origin_still_stamped(self):
        request = _make_request({"x-sap-origin": "ui5"})
        result = _extract_ias_attrs(request, _passing_verifier(sap_gtid="t1"))
        assert result == {ATTR_SAP_TRIGGER_TYPE: "ui5"}
        assert ATTR_SAP_TENANT_ID not in result


# ---------------------------------------------------------------------------
# Inner middleware dispatch
# ---------------------------------------------------------------------------

class TestInnerMiddlewareDispatch:
    def _get_inner_class_and_kwargs(self, mw: StarletteIASTelemetryMiddleware):
        app = MagicMock()
        mw.app = app
        mw.register()
        args, kwargs = app.add_middleware.call_args
        return args[0], kwargs

    @pytest.mark.anyio
    async def test_sets_attrs_in_context_var_during_request(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="tenant-1", user_uuid="user-1"),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)

        request = _make_request({"authorization": "Bearer tok"})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, call_next)

        assert captured == {ATTR_SAP_TENANT_ID: "tenant-1", ATTR_USER_ID: "user-1"}

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
            token_verifier=_passing_verifier(sap_gtid="t1", user_uuid="u1"),
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
    async def test_no_auth_header_sets_empty_attrs(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_passing_verifier(sap_gtid="t1"),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)

        request = _make_request({})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, call_next)

        assert captured == {}

    @pytest.mark.anyio
    async def test_forged_token_sets_empty_attrs_during_dispatch(self):
        mw = StarletteIASTelemetryMiddleware(
            app=MagicMock(),
            token_verifier=_failing_verifier(IASTokenError("bad sig")),
        )
        inner_cls, kwargs = self._get_inner_class_and_kwargs(mw)

        request = _make_request({"authorization": "Bearer attacker.jwt"})
        captured = {}

        async def call_next(req):
            captured.update(mw._attrs_var.get())
            return MagicMock()

        inner = inner_cls(app=MagicMock(), **kwargs)
        await inner.dispatch(request, call_next)

        assert ATTR_SAP_TENANT_ID not in captured
        assert ATTR_USER_ID not in captured

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
