"""Unit tests for watch_aicore_config() — proactive credential reload on secret mount change.

The watcher polls the AI Core secret directory mtime every N seconds. When the mtime
changes (Kubernetes projected volume atomic symlink swap on rotation), it calls
set_aicore_config() proactively — before LiteLLM's cached OAuth token expires.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.aicore import _get_secret_dir_mtime, watch_aicore_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_secret_dir(tmp_path: Path, instance_name: str = "aicore-instance") -> Path:
    secret_dir = tmp_path / "aicore" / instance_name
    secret_dir.mkdir(parents=True)
    (secret_dir / "clientsecret").write_text("secret-v1")
    return secret_dir


# ---------------------------------------------------------------------------
# _get_secret_dir_mtime
# ---------------------------------------------------------------------------


class TestGetSecretDirMtime:
    def test_returns_float_for_existing_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _make_secret_dir(tmp_path)
        mtime = _get_secret_dir_mtime()
        assert isinstance(mtime, float)
        assert mtime > 0.0

    def test_returns_zero_for_missing_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        # Do not create the secret dir
        assert _get_secret_dir_mtime() == 0.0

    def test_stable_without_modification(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _make_secret_dir(tmp_path)
        m1 = _get_secret_dir_mtime()
        m2 = _get_secret_dir_mtime()
        assert m1 == m2


# ---------------------------------------------------------------------------
# watch_aicore_config
# ---------------------------------------------------------------------------


class TestWatchAicoreConfig:
    def test_thread_is_daemon(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _make_secret_dir(tmp_path)
        stop = threading.Event()
        with patch("sap_cloud_sdk.aicore.set_aicore_config"):
            t = watch_aicore_config(interval=60.0, stop_event=stop)
        stop.set()
        assert t.daemon is True

    def test_no_reload_when_mtime_unchanged(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _make_secret_dir(tmp_path)
        stop = threading.Event()
        with patch("sap_cloud_sdk.aicore.set_aicore_config") as mock_reload:
            t = watch_aicore_config(interval=0.05, stop_event=stop)
            time.sleep(0.2)
            stop.set()
            t.join(timeout=1.0)
        mock_reload.assert_not_called()

    def test_reloads_on_directory_mtime_change(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = _make_secret_dir(tmp_path)
        stop = threading.Event()
        reloaded = threading.Event()

        def _fake_reload(**kwargs):
            reloaded.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_fake_reload):
            t = watch_aicore_config(interval=0.05, stop_event=stop)
            # Advance directory mtime to simulate kubelet secret rotation
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))
            assert reloaded.wait(timeout=1.0), "reload was not triggered after mtime change"
            stop.set()
            t.join(timeout=1.0)

    def test_logs_info_on_reload(self, tmp_path, monkeypatch, caplog):
        import logging
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = _make_secret_dir(tmp_path)
        stop = threading.Event()
        reloaded = threading.Event()

        def _fake_reload(**kwargs):
            reloaded.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_fake_reload):
            with caplog.at_level(logging.INFO, logger="sap_cloud_sdk.aicore"):
                t = watch_aicore_config(interval=0.05, stop_event=stop)
                new_time = time.time() + 10
                os.utime(secret_dir, (new_time, new_time))
                reloaded.wait(timeout=1.0)
                stop.set()
                t.join(timeout=1.0)

        assert any(
            "proactively reloading credentials" in r.message for r in caplog.records
        )

    def test_exception_in_set_aicore_config_does_not_crash_thread(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = _make_secret_dir(tmp_path)
        stop = threading.Event()
        errored = threading.Event()

        def _boom(**kwargs):
            errored.set()
            raise RuntimeError("simulated reload failure")

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_boom):
            t = watch_aicore_config(interval=0.05, stop_event=stop)
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))
            assert errored.wait(timeout=1.0)
            # Thread must still be alive after the exception
            assert t.is_alive()
            stop.set()
            t.join(timeout=1.0)

    def test_stop_event_exits_loop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        _make_secret_dir(tmp_path)
        stop = threading.Event()
        with patch("sap_cloud_sdk.aicore.set_aicore_config"):
            t = watch_aicore_config(interval=0.05, stop_event=stop)
            stop.set()
            t.join(timeout=1.0)
        assert not t.is_alive()

    def test_custom_instance_name_forwarded_to_set_aicore_config(
        self, tmp_path, monkeypatch
    ):
        custom = "my-aicore"
        monkeypatch.setenv("SERVICE_BINDING_ROOT", str(tmp_path))
        secret_dir = tmp_path / "aicore" / custom
        secret_dir.mkdir(parents=True)
        (secret_dir / "clientsecret").write_text("v1")
        stop = threading.Event()
        reloaded = threading.Event()
        captured_kwargs: list = []

        def _fake_reload(**kwargs):
            captured_kwargs.append(kwargs)
            reloaded.set()

        with patch("sap_cloud_sdk.aicore.set_aicore_config", side_effect=_fake_reload):
            t = watch_aicore_config(
                instance_name=custom, interval=0.05, stop_event=stop
            )
            new_time = time.time() + 10
            os.utime(secret_dir, (new_time, new_time))
            assert reloaded.wait(timeout=1.0)
            stop.set()
            t.join(timeout=1.0)

        assert captured_kwargs[0].get("instance_name") == custom
