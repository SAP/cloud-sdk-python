"""Unit tests for IsolationStrategy and build_isolation_key."""

import hashlib

import pytest

from sap_cloud_sdk.cache._isolation import IsolationStrategy, build_isolation_key


class TestBuildIsolationKeyAutoSelect:
    def test_no_user_id_returns_tenant_id(self) -> None:
        key = build_isolation_key(tenant_id="tenant-abc")
        assert key == "tenant-abc"

    def test_empty_user_id_returns_tenant_id(self) -> None:
        key = build_isolation_key(tenant_id="tenant-abc", user_id="")
        assert key == "tenant-abc"

    def test_with_user_id_returns_sha256_hash(self) -> None:
        key = build_isolation_key(tenant_id="tenant-abc", user_id="user-123")
        expected = hashlib.sha256(b"tenant-abc|user-123").hexdigest()[:32]
        assert key == expected

    def test_hash_is_32_chars(self) -> None:
        key = build_isolation_key(tenant_id="t", user_id="u")
        assert len(key) == 32

    def test_different_users_produce_different_keys(self) -> None:
        k1 = build_isolation_key(tenant_id="t", user_id="user-1")
        k2 = build_isolation_key(tenant_id="t", user_id="user-2")
        assert k1 != k2

    def test_different_tenants_produce_different_keys(self) -> None:
        k1 = build_isolation_key(tenant_id="tenant-1", user_id="u")
        k2 = build_isolation_key(tenant_id="tenant-2", user_id="u")
        assert k1 != k2

    def test_same_inputs_produce_stable_hash(self) -> None:
        k1 = build_isolation_key(tenant_id="t", user_id="u")
        k2 = build_isolation_key(tenant_id="t", user_id="u")
        assert k1 == k2


class TestBuildIsolationKeyExplicitStrategy:
    def test_explicit_tenant_strategy_ignores_user_id(self) -> None:
        key = build_isolation_key(
            tenant_id="tenant-abc",
            user_id="user-123",
            strategy=IsolationStrategy.TENANT,
        )
        assert key == "tenant-abc"

    def test_explicit_tenant_user_strategy_with_user_id(self) -> None:
        key = build_isolation_key(
            tenant_id="t",
            user_id="u",
            strategy=IsolationStrategy.TENANT_USER,
        )
        expected = hashlib.sha256(b"t|u").hexdigest()[:32]
        assert key == expected

    def test_explicit_tenant_user_strategy_without_user_id_falls_back_to_tenant(
        self,
    ) -> None:
        key = build_isolation_key(
            tenant_id="tenant-abc",
            user_id=None,
            strategy=IsolationStrategy.TENANT_USER,
        )
        assert key == "tenant-abc"

    def test_downgrade_warning_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="sap_cloud_sdk.cache._isolation"):
            build_isolation_key(
                tenant_id="t",
                user_id="u",
                strategy=IsolationStrategy.TENANT,
            )
        assert any("cross-user" in record.message for record in caplog.records)
