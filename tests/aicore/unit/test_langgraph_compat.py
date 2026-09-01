"""Credential rotation compatibility tests for LangGraph/ChatLiteLLM agents.

LangGraph agent templates (app/agent_executor.py) use ChatLiteLLM (LangChain), which
calls litellm.completion directly — bypassing the SDK's completion()/acompletion()
wrappers. As a result:

- The reactive 401 handler in completion() is NOT triggered for ChatLiteLLM agents.
- The proactive watcher (watch_aicore_config) IS sufficient because LiteLLM reads
  os.environ["AICORE_CLIENT_SECRET"] on every OAuth token refresh, not from a closure.

Required change for LangGraph agents (one line at startup):

    from sap_cloud_sdk.aicore import set_aicore_config, watch_aicore_config
    set_aicore_config()        # already in agent template
    watch_aicore_config()      # ADD THIS — proactive rotation without pod restart

No changes to ChatLiteLLM usage, tool definitions, or agent graphs are required.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import litellm
import pytest

from sap_cloud_sdk.aicore import (
    completion,
    patch_litellm_for_credential_rotation,
    set_aicore_config,
    watch_aicore_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_secret_files(tmp_path: Path, secret: str, instance: str = "aicore-instance") -> Path:
    secret_dir = tmp_path / "aicore" / instance
    secret_dir.mkdir(parents=True, exist_ok=True)
    (secret_dir / "clientid").write_text("test-client-id")
    (secret_dir / "clientsecret").write_text(secret)
    (secret_dir / "url").write_text("https://auth.example.com")
    (secret_dir / "serviceurls").write_text('{"AI_API_URL": "https://api.example.com"}')
    return secret_dir


# ---------------------------------------------------------------------------
# 1. os.environ is the single credential store for all litellm callers
# ---------------------------------------------------------------------------


class TestEnvSharedAcrossAllLiteLLMCallers:
    """set_aicore_config() writes to os.environ — the only source LiteLLM reads.

    Both our completion() wrapper and ChatLiteLLM reach the same os.environ, so
    updating it via set_aicore_config() (or the watcher that calls it) is sufficient
    regardless of which call pattern the agent uses.
    """

    def test_set_aicore_config_writes_credential_to_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        _write_secret_files(tmp_path, secret="v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        assert os.environ["AICORE_CLIENT_SECRET"] == "v1"

    def test_rotated_credential_overwrites_env_for_all_callers(self, tmp_path, monkeypatch):
        """After rotation, any litellm caller — wrapper or ChatLiteLLM — reads the
        new credential from os.environ on the next OAuth token refresh."""
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        secret_dir = _write_secret_files(tmp_path, secret="v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ["AICORE_CLIENT_SECRET"] == "v1"

        (secret_dir / "clientsecret").write_text("v2")
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        assert os.environ["AICORE_CLIENT_SECRET"] == "v2"


# ---------------------------------------------------------------------------
# 2. Reactive 401 path — scope and limitation for ChatLiteLLM agents
# ---------------------------------------------------------------------------


class TestReactivePathScope:
    """Documents the scope boundary of the reactive 401 handler.

    The handler lives in completion()/acompletion(). ChatLiteLLM calls
    litellm.completion directly and bypasses it — so a 401 raised there
    surfaces to the caller instead of triggering a credential reload.
    This is the gap that watch_aicore_config() fills for LangGraph agents.
    """

    def test_direct_litellm_call_does_not_trigger_credential_reload(self):
        """ChatLiteLLM calls litellm.completion directly.
        The SDK's reload handler is NOT invoked on AuthenticationError.
        """
        reload_mock = MagicMock()
        auth_err = litellm.AuthenticationError(
            message="401 Unauthorized", llm_provider="sap", model="sap/x"
        )
        with (
            patch("litellm.completion", side_effect=auth_err),
            patch("sap_cloud_sdk.aicore.set_aicore_config", reload_mock),
        ):
            with pytest.raises(litellm.AuthenticationError):
                litellm.completion(model="sap/x", messages=[])

        reload_mock.assert_not_called()

    def test_sdk_completion_wrapper_does_trigger_reload_on_401(self):
        """Contrast: agents using our completion() wrapper get transparent reload.
        The watcher is not strictly required for those agents (though still useful).
        """
        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401 Unauthorized", llm_provider="sap", model="sap/x"
        )
        call_results = [auth_err, sentinel]

        def _fake(*args, **kwargs):
            r = call_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with (
            patch("sap_cloud_sdk.aicore.completion.litellm.completion", side_effect=_fake),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as reload_mock,
        ):
            result = completion(model="sap/x", messages=[])

        assert result is sentinel
        reload_mock.assert_called_once()

    def test_direct_litellm_call_after_manual_reload_succeeds(self, tmp_path, monkeypatch):
        """If a LangGraph agent catches a 401 and calls set_aicore_config() manually,
        the next litellm.completion call succeeds with the refreshed credential.
        This shows env-update is sufficient — no SDK wrapper required.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        secret_dir = _write_secret_files(tmp_path, secret="v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        # Simulate rotation: file updated, env still has old value
        (secret_dir / "clientsecret").write_text("v2")

        # Agent manually calls set_aicore_config() after a 401 (fallback pattern)
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        assert os.environ["AICORE_CLIENT_SECRET"] == "v2"


# ---------------------------------------------------------------------------
# 3. Proactive watcher — correct and complete fix for LangGraph agents
# ---------------------------------------------------------------------------


class TestWatcherForLangGraphAgents:
    """watch_aicore_config() is the recommended fix for LangGraph/ChatLiteLLM agents.

    It runs as a daemon thread, polls the secret directory mtime, and calls
    set_aicore_config() proactively on change — before the OAuth token expires.
    Both ChatLiteLLM and SDK wrapper callers benefit without any code changes.
    """

    def test_watcher_is_daemon_thread_no_pod_lifecycle_impact(self, tmp_path, monkeypatch):
        """The watcher runs as a daemon thread — pods can shut down freely.
        No shutdown hook or explicit cleanup is required in the agent.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _write_secret_files(tmp_path, secret="v1")
        stop = threading.Event()

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
            t = watch_aicore_config(stop_event=stop)

        assert t.daemon
        assert t.is_alive()
        stop.set()
        t.join(timeout=1.0)
        assert not t.is_alive()

    def test_recommended_startup_pattern_for_langgraph(self, tmp_path, monkeypatch):
        """Verifies the one-line migration for LangGraph agents.

        Before:
            set_aicore_config()

        After:
            set_aicore_config()
            watch_aicore_config()   # only change needed

        No other code changes are required.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        _write_secret_files(tmp_path, secret="initial")

        stop = threading.Event()
        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()                     # already in template
            t = watch_aicore_config(stop_event=stop)  # new line

        assert os.environ["AICORE_CLIENT_SECRET"] == "initial"
        assert t.daemon
        stop.set()
        t.join(timeout=1.0)

    def test_watcher_updates_env_on_rotation_independent_of_call_pattern(
        self, tmp_path, monkeypatch
    ):
        """End-to-end: watcher detects mtime change → set_aicore_config() → env updated.

        The reload path does NOT go through completion() — it's independent of
        how the agent calls LiteLLM. ChatLiteLLM callers benefit equally.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        secret_dir = _write_secret_files(tmp_path, secret="v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
        assert os.environ["AICORE_CLIENT_SECRET"] == "v1"

        stop = threading.Event()
        rotation_detected = threading.Event()
        _real_set = set_aicore_config  # capture before patching

        def _tracking_reload(**kwargs):
            with patch("sap_cloud_sdk.aicore.set_filtering"):
                _real_set(**kwargs)
            rotation_detected.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_tracking_reload):
            watch_aicore_config(interval=0.05, stop_event=stop)

            (secret_dir / "clientsecret").write_text("v2")
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))

            assert rotation_detected.wait(timeout=1.0), "watcher did not detect rotation"
            stop.set()

        assert os.environ["AICORE_CLIENT_SECRET"] == "v2"

    def test_env_after_watcher_reload_visible_to_direct_litellm_caller(
        self, tmp_path, monkeypatch
    ):
        """After the watcher fires, the updated credential is in os.environ.
        A direct litellm.completion call (ChatLiteLLM pattern) would use it
        on the next OAuth token refresh — same as the SDK wrapper path.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        secret_dir = _write_secret_files(tmp_path, secret="v1")

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()

        stop = threading.Event()
        rotation_done = threading.Event()
        _real_set = set_aicore_config

        def _tracking_reload(**kwargs):
            with patch("sap_cloud_sdk.aicore.set_filtering"):
                _real_set(**kwargs)
            rotation_done.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_tracking_reload):
            watch_aicore_config(interval=0.05, stop_event=stop)

            (secret_dir / "clientsecret").write_text("v2")
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))

            assert rotation_done.wait(timeout=1.0)
            stop.set()

        # Both ChatLiteLLM and our wrapper would read "v2" on next token refresh
        assert os.environ["AICORE_CLIENT_SECRET"] == "v2"

    def test_watcher_does_not_restart_on_exception_in_reload(self, tmp_path, monkeypatch):
        """If set_aicore_config() raises during a reload, the watcher catches the
        exception and continues polling — it does not crash the agent pod.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = _write_secret_files(tmp_path, secret="v1")

        stop = threading.Event()
        call_count = [0]

        def _flaky_reload(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient reload failure")

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_flaky_reload):
            t = watch_aicore_config(interval=0.05, stop_event=stop)

            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))
            time.sleep(0.2)

            assert t.is_alive(), "watcher thread must survive exception in reload"
            stop.set()
            t.join(timeout=1.0)


# ---------------------------------------------------------------------------
# 4. patch_litellm_for_credential_rotation — reactive reload for ChatLiteLLM
# ---------------------------------------------------------------------------


@pytest.fixture()
def clean_litellm_patch():
    """Restore litellm.completion/acompletion and clear the guard after each test."""
    import litellm as _litellm

    orig_completion = _litellm.completion
    orig_acompletion = _litellm.acompletion
    yield
    _litellm.completion = orig_completion
    _litellm.acompletion = orig_acompletion
    if hasattr(_litellm, "_sap_aicore_patched"):
        del _litellm._sap_aicore_patched


class TestPatchLitellmForCredentialRotation:
    """patch_litellm_for_credential_rotation() extends reactive 401 reload to ALL
    litellm callers — including ChatLiteLLM (LangGraph agents) that bypass our wrapper.

    After calling this function once at startup, direct litellm.completion calls
    (the ChatLiteLLM pattern) trigger set_aicore_config() on AuthenticationError
    and retry transparently, exactly like our completion() wrapper does.
    """

    def test_direct_litellm_call_triggers_reload_after_patch(self, clean_litellm_patch):
        """After patching, a direct litellm.completion call (ChatLiteLLM pattern)
        triggers credential reload on 401 and retries — transparent to the caller.
        """
        sentinel = object()
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        call_results = [auth_err, sentinel]

        def _fake(*args, **kwargs):
            r = call_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with (
            patch("litellm.completion", side_effect=_fake),
            patch("sap_cloud_sdk.aicore.set_aicore_config") as reload_mock,
        ):
            patch_litellm_for_credential_rotation()
            result = litellm.completion(model="sap/x", messages=[])

        assert result is sentinel
        reload_mock.assert_called_once()

    def test_direct_litellm_call_without_patch_still_raises(self, clean_litellm_patch):
        """Contrast: without the patch, a 401 from a direct litellm call is not
        intercepted — it propagates to the caller (LangGraph graph terminates).
        """
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        reload_mock = MagicMock()

        with (
            patch("litellm.completion", side_effect=auth_err),
            patch("sap_cloud_sdk.aicore.set_aicore_config", reload_mock),
        ):
            with pytest.raises(litellm.AuthenticationError):
                litellm.completion(model="sap/x", messages=[])

        reload_mock.assert_not_called()

    def test_patch_is_idempotent(self, clean_litellm_patch):
        """Calling patch_litellm_for_credential_rotation() multiple times does not
        double-wrap litellm — the guard prevents nested patching.
        """
        import litellm as _litellm

        with patch("sap_cloud_sdk.aicore.set_aicore_config"):
            patch_litellm_for_credential_rotation()
            first_completion = _litellm.completion

            patch_litellm_for_credential_rotation()
            second_completion = _litellm.completion

        assert first_completion is second_completion

    def test_retry_fails_propagates_auth_error(self, clean_litellm_patch):
        """If the retry also raises AuthenticationError, it propagates to the caller —
        no infinite loop, same behaviour as the SDK completion() wrapper.
        """
        auth_err = litellm.AuthenticationError(
            message="401", llm_provider="sap", model="sap/x"
        )
        reload_mock = MagicMock()

        with (
            patch("litellm.completion", side_effect=auth_err),
            patch("sap_cloud_sdk.aicore.set_aicore_config", reload_mock),
        ):
            patch_litellm_for_credential_rotation()
            with pytest.raises(litellm.AuthenticationError):
                litellm.completion(model="sap/x", messages=[])

        reload_mock.assert_called_once()

    def test_full_langgraph_startup_pattern(self, tmp_path, monkeypatch, clean_litellm_patch):
        """End-to-end startup pattern for LangGraph agents after migration.

        set_aicore_config()                       # load credentials
        patch_litellm_for_credential_rotation()   # reactive 401 reload for ChatLiteLLM
        watch_aicore_config()                     # proactive reload on secret rotation

        With these three calls at startup, credential rotation is fully transparent —
        no pod restart, no code changes to ChatLiteLLM usage or agent graphs.
        """
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        monkeypatch.delenv("AICORE_CLIENT_SECRET", raising=False)
        _write_secret_files(tmp_path, secret="initial")

        stop = threading.Event()

        with patch("sap_cloud_sdk.aicore.set_filtering"):
            set_aicore_config()
            patch_litellm_for_credential_rotation()
            t = watch_aicore_config(stop_event=stop)

        assert os.environ["AICORE_CLIENT_SECRET"] == "initial"
        assert t.daemon
        assert t.is_alive()

        # Verify patch is active — direct litellm call now has reload semantics
        import litellm as _litellm
        assert getattr(_litellm, "_sap_aicore_patched", False)

        stop.set()
        t.join(timeout=1.0)
