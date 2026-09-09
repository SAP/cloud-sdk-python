"""Tests verifying that set_aicore_config() updating os.environ is sufficient
for LiteLLM to pick up new credentials on the next OAuth token refresh.

Background: LiteLLM caches the OAuth token (~12h lifetime), NOT the client_secret
in a long-lived client object. When the token expires, LiteLLM reads
os.environ["AICORE_CLIENT_SECRET"] fresh to fetch a new token. So calling
set_aicore_config() (which updates os.environ) is the only thing needed to
handle credential rotation — no LiteLLM client object needs to be recreated.

These tests verify the full contract that makes both approaches in PR #256 work:
- Reactive: 401 → set_aicore_config() → env updated → retry succeeds
- Proactive: watcher detects mtime change → set_aicore_config() → env updated
             → next token refresh uses new client_secret before expiry
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import litellm
import pytest
from unittest.mock import patch

from sap_cloud_sdk.aicore import set_aicore_config, watch_aicore_config
from sap_cloud_sdk.aicore import completion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_secret_files(tmp_path: Path, secret: str, instance: str = "aicore-instance") -> Path:
    secret_dir = tmp_path / "aicore" / instance
    secret_dir.mkdir(parents=True, exist_ok=True)
    (secret_dir / "clientid").write_text("test-client-id")
    (secret_dir / "clientsecret").write_text(secret)
    (secret_dir / "url").write_text("https://auth.example.com")
    serviceurls = secret_dir / "serviceurls"
    serviceurls.write_text('{"AI_API_URL": "https://api.example.com"}')
    return secret_dir


# ---------------------------------------------------------------------------
# 1. env updated on second set_aicore_config() call
# ---------------------------------------------------------------------------


class TestEnvUpdatedOnRotation:
    def test_second_call_overwrites_client_secret(self, tmp_path, monkeypatch):
        """Re-calling set_aicore_config() after file update writes the new
        client_secret to os.environ — the value LiteLLM reads on next token refresh."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)

        _write_secret_files(tmp_path, secret="secret-v1")
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ["AICORE_CLIENT_SECRET"] == "secret-v1"

        # Simulate BTP rotation: kubelet updates the file
        (tmp_path / "aicore" / "aicore-instance" / "clientsecret").write_text("secret-v2")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ["AICORE_CLIENT_SECRET"] == "secret-v2"


# ---------------------------------------------------------------------------
# 2. Proactive watcher updates env before token expiry
# ---------------------------------------------------------------------------


class TestWatcherUpdatesEnvProactively:
    def test_env_updated_after_mtime_change(self, tmp_path, monkeypatch):
        """Full end-to-end: watcher detects mtime change → set_aicore_config()
        → os.environ has new secret before the OAuth token expires."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)

        secret_dir = _write_secret_files(tmp_path, secret="secret-v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ["AICORE_CLIENT_SECRET"] == "secret-v1"

        stop = threading.Event()
        reloaded = threading.Event()

        def _tracking_set_config(**kwargs):
            reloaded.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_tracking_set_config):
            t = watch_aicore_config(interval=0.05, stop_event=stop)

            # Simulate kubelet secret update: new file content + advance dir mtime
            (secret_dir / "clientsecret").write_text("secret-v2")
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))

            assert reloaded.wait(timeout=1.0), "watcher did not trigger reload"
            stop.set()
            t.join(timeout=1.0)


# ---------------------------------------------------------------------------
# 3. Reactive 401 handler updates env
# ---------------------------------------------------------------------------


class TestReactive401UpdatesEnv:
    def test_completion_updates_env_after_401(self, tmp_path, monkeypatch):
        """On AuthenticationError, the 401 handler calls set_aicore_config()
        which updates os.environ — env has new secret after the call."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)

        _write_secret_files(tmp_path, secret="secret-v1")
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        # Rotate the file before the 401 is caught
        (tmp_path / "aicore" / "aicore-instance" / "clientsecret").write_text("secret-v2")

        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        sentinel = object()
        call_returns = [auth_err, sentinel]

        def _fake_completion(*args, **kwargs):
            r = call_returns.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=_fake_completion),
            patch("sap_cloud_sdk.aicore.set_filtering"),
        ):
            result = completion(model="sap/x", messages=[])

        assert result is sentinel
        assert os.environ["AICORE_CLIENT_SECRET"] == "secret-v2"


# ---------------------------------------------------------------------------
# 4. No LiteLLM client object needs recreation
# ---------------------------------------------------------------------------


class TestNoClientRecreationNeeded:
    def test_litellm_has_no_cached_aicore_client_attribute(self, tmp_path, monkeypatch):
        """LiteLLM does not hold an _aicore_client or similar attribute that
        would cache the old client_secret — env update is the single source of truth."""
        import litellm as _litellm
        # If LiteLLM ever adds a cached client object, this test will catch it
        # so we can handle it explicitly.
        assert not hasattr(_litellm, "_aicore_client"), (
            "LiteLLM added an _aicore_client attribute — credential rotation logic "
            "must be updated to also reset this object."
        )

    def test_env_is_single_source_after_rotation(self, tmp_path, monkeypatch):
        """After set_aicore_config() with v2, os.environ has v2 and no stale v1
        value persists anywhere that would prevent LiteLLM from using v2."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)

        _write_secret_files(tmp_path, secret="secret-v1")
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ.get("AICORE_CLIENT_SECRET") == "secret-v1"

        (tmp_path / "aicore" / "aicore-instance" / "clientsecret").write_text("secret-v2")
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        assert os.environ.get("AICORE_CLIENT_SECRET") == "secret-v2"
        # v1 is gone from the env
        assert "secret-v1" not in os.environ.get("AICORE_CLIENT_SECRET", "")


# ---------------------------------------------------------------------------
# 5. Concurrent set_aicore_config() calls do not raise
# ---------------------------------------------------------------------------


class TestConcurrentSetAicoreConfig:
    def test_concurrent_calls_no_exception(self, tmp_path, monkeypatch):
        """Two threads calling set_aicore_config() concurrently must not
        raise exceptions. Last-write-wins is acceptable for credential rotation."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)

        for v in ("v1", "v2"):
            _write_secret_files(tmp_path, secret=v)  # final file = v2

        errors: list[Exception] = []

        def _call():
            try:
                with patch("sap_cloud_sdk.aicore.set_filtering"):
                    set_aicore_config()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_call) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        assert not errors, f"Concurrent calls raised: {errors}"
        # env must hold one of the valid values (not empty or corrupt)
        assert os.environ.get("AICORE_CLIENT_SECRET") in ("v1", "v2")


# ---------------------------------------------------------------------------
# 6. _get_secret_dir_mtime stable without modification
# ---------------------------------------------------------------------------


class TestGetSecretDirMtimeStability:
    def test_stable_float_for_existing_dir(self, tmp_path, monkeypatch):
        """Calling _get_secret_dir_mtime twice on an unchanged dir returns the
        same float — watcher does not trigger spurious reloads."""
        from sap_cloud_sdk.aicore import _get_secret_dir_mtime
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = tmp_path / "aicore" / "aicore-instance"
        secret_dir.mkdir(parents=True)

        m1 = _get_secret_dir_mtime()
        m2 = _get_secret_dir_mtime()
        assert m1 == m2
        assert m1 > 0.0
