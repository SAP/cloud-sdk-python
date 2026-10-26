"""Unit tests for IsolationStrategy and build_isolation_key."""

import logging

import pytest

from sap_cloud_sdk.cache._isolation import IsolationStrategy, build_isolation_key
from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, DWC_TENANT, USER_ID, RuntimeContext
from sap_cloud_sdk.core.runtime_context._context import sdk_context


def _ctx(tenant_id: str | None = None, user_id: str | None = None) -> RuntimeContext:
    values: dict = {}
    if tenant_id is not None:
        values[APP_TENANT_ID] = tenant_id
    if user_id is not None:
        values[USER_ID] = user_id
    return RuntimeContext(values)


def _dwc_ctx(dwc_tenant: str | None = None, user_id: str | None = None) -> RuntimeContext:
    values: dict = {}
    if dwc_tenant is not None:
        values[DWC_TENANT] = dwc_tenant
    if user_id is not None:
        values[USER_ID] = user_id
    return RuntimeContext(values)


class TestBuildIsolationKeyAutoSelect:
    def test_no_user_id_returns_tenant_key(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc")):
            assert build_isolation_key() == "tenant:tenant-abc"

    def test_empty_user_id_returns_tenant_key(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc", user_id="")):
            assert build_isolation_key() == "tenant:tenant-abc"

    def test_with_user_id_returns_tenant_user_key(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc", user_id="user-123")):
            assert build_isolation_key() == "tenant:tenant-abc:user:user-123"

    def test_different_users_produce_different_keys(self) -> None:
        with sdk_context(_ctx(tenant_id="t", user_id="user-1")):
            k1 = build_isolation_key()
        with sdk_context(_ctx(tenant_id="t", user_id="user-2")):
            k2 = build_isolation_key()
        assert k1 != k2

    def test_different_tenants_produce_different_keys(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-1", user_id="u")):
            k1 = build_isolation_key()
        with sdk_context(_ctx(tenant_id="tenant-2", user_id="u")):
            k2 = build_isolation_key()
        assert k1 != k2

    def test_same_inputs_produce_stable_key(self) -> None:
        with sdk_context(_ctx(tenant_id="t", user_id="u")):
            k1 = build_isolation_key()
            k2 = build_isolation_key()
        assert k1 == k2


class TestBuildIsolationKeyExplicitStrategy:
    def test_explicit_tenant_strategy_ignores_user_id(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc", user_id="user-123")):
            key = build_isolation_key(strategy=IsolationStrategy.TENANT)
        assert key == "tenant:tenant-abc"

    def test_explicit_tenant_user_strategy_with_user_id(self) -> None:
        with sdk_context(_ctx(tenant_id="t", user_id="u")):
            key = build_isolation_key(strategy=IsolationStrategy.TENANT_USER)
        assert key == "tenant:t:user:u"

    def test_explicit_tenant_user_strategy_without_user_id_falls_back_to_tenant(
        self,
    ) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc")):
            key = build_isolation_key(strategy=IsolationStrategy.TENANT_USER)
        assert key == "tenant:tenant-abc"

    def test_downgrade_warning_is_logged(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="sap_cloud_sdk.cache._isolation"):
            with sdk_context(_ctx(tenant_id="t", user_id="u")):
                build_isolation_key(strategy=IsolationStrategy.TENANT)
        assert any("cross-user" in record.message for record in caplog.records)


class TestBuildIsolationKeyProvider:
    def test_provider_strategy_returns_fixed_constant(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-abc", user_id="user-123")):
            key = build_isolation_key(strategy=IsolationStrategy.PROVIDER)
        assert key == "provider"

    def test_provider_strategy_ignores_empty_context(self) -> None:
        with sdk_context(RuntimeContext()):
            key = build_isolation_key(strategy=IsolationStrategy.PROVIDER)
        assert key == "provider"

    def test_provider_is_stable_across_tenants(self) -> None:
        with sdk_context(_ctx(tenant_id="tenant-1")):
            k1 = build_isolation_key(strategy=IsolationStrategy.PROVIDER)
        with sdk_context(_ctx(tenant_id="tenant-2")):
            k2 = build_isolation_key(strategy=IsolationStrategy.PROVIDER)
        assert k1 == k2 == "provider"


class TestBuildIsolationKeyNoContext:
    def test_empty_context_returns_empty_string(self) -> None:
        with sdk_context(RuntimeContext()):
            assert build_isolation_key() == ""


class TestBuildIsolationKeyDwcFallback:
    def test_dwc_tenant_used_when_app_tenant_id_absent(self) -> None:
        with sdk_context(_dwc_ctx(dwc_tenant="dwc-tenant-1")):
            assert build_isolation_key() == "tenant:dwc-tenant-1"

    def test_app_tenant_id_takes_precedence_over_dwc_tenant(self) -> None:
        values = {APP_TENANT_ID: "ias-tenant", DWC_TENANT: "dwc-tenant"}
        with sdk_context(RuntimeContext(values)):
            assert build_isolation_key() == "tenant:ias-tenant"

    def test_dwc_tenant_with_user_produces_tenant_user_key(self) -> None:
        with sdk_context(_dwc_ctx(dwc_tenant="dwc-tenant-1", user_id="user-abc")):
            assert build_isolation_key() == "tenant:dwc-tenant-1:user:user-abc"
