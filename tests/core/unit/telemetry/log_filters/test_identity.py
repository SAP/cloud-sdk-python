"""Tests for log_filters.identity."""

import logging
from unittest.mock import patch

import pytest

from sap_cloud_sdk.core.telemetry.log_filters.identity import (
    IdentityLogFilter,
    _resolve_log_attributes,
)
from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TENANT_ID, ATTR_USER_ID


def _make_record() -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)


class TestResolveLogAttributes:
    def test_returns_tenant_and_user_from_runtime_context(self):
        from sap_cloud_sdk.core.runtime_context.providers._ias import GLOBAL_TENANT_ID, USER_ID
        from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, sdk_context

        ctx = RuntimeContext({GLOBAL_TENANT_ID: "t-1", USER_ID: "u-1"})
        with sdk_context(ctx):
            attrs = _resolve_log_attributes()

        assert attrs == {ATTR_SAP_TENANT_ID: "t-1", ATTR_USER_ID: "u-1"}

    def test_falls_back_to_auth_context(self):
        from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, sdk_context
        from sap_cloud_sdk.ias._context import _auth_context_var
        from sap_cloud_sdk.ias._token import IASClaims

        claims = IASClaims(sap_gtid="gtid-1", user_uuid="uuid-1")
        token = _auth_context_var.set(claims)
        try:
            with sdk_context(RuntimeContext()):
                attrs = _resolve_log_attributes()
        finally:
            _auth_context_var.reset(token)

        assert attrs == {ATTR_SAP_TENANT_ID: "gtid-1", ATTR_USER_ID: "uuid-1"}

    def test_returns_empty_when_nothing_set(self):
        from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, sdk_context

        with sdk_context(RuntimeContext()):
            assert _resolve_log_attributes() == {}

    def test_returns_empty_on_exception(self):
        with patch("sap_cloud_sdk.core.runtime_context.get_context", side_effect=Exception("boom")):
            assert _resolve_log_attributes() == {}


class TestIdentityLogFilter:
    def test_stamps_all_resolved_attributes(self):
        from sap_cloud_sdk.core.runtime_context.providers._ias import GLOBAL_TENANT_ID, USER_ID
        from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, sdk_context

        ctx = RuntimeContext({GLOBAL_TENANT_ID: "t-1", USER_ID: "u-1"})
        record = _make_record()
        filt = IdentityLogFilter()

        with sdk_context(ctx):
            result = filt.filter(record)

        assert result is True
        assert getattr(record, ATTR_SAP_TENANT_ID) == "t-1"
        assert getattr(record, ATTR_USER_ID) == "u-1"

    def test_skips_attributes_when_nothing_set(self):
        from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, sdk_context

        record = _make_record()
        filt = IdentityLogFilter()

        with sdk_context(RuntimeContext()):
            result = filt.filter(record)

        assert result is True
        assert not hasattr(record, ATTR_SAP_TENANT_ID)
        assert not hasattr(record, ATTR_USER_ID)

    def test_always_returns_true(self):
        record = _make_record()
        filt = IdentityLogFilter()
        with patch("sap_cloud_sdk.core.telemetry.log_filters.identity._resolve_log_attributes", return_value={}):
            assert filt.filter(record) is True
