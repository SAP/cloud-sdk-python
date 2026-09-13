"""Unit tests for CBC config resolution."""

from __future__ import annotations

import pytest

from sap_cloud_sdk.cbc.config import (
    ENV_CERT_PATH,
    ENV_KEY_PATH,
    ENV_URL,
    _read_env_path,
    load_from_env,
)
from sap_cloud_sdk.cbc.exceptions import CBCConfigError


# ---------------------------------------------------------------------------
# load_from_env
# ---------------------------------------------------------------------------


class TestLoadFromEnv:
    def test_raises_when_no_env_vars(self, monkeypatch):
        monkeypatch.delenv(ENV_URL, raising=False)
        monkeypatch.delenv(ENV_CERT_PATH, raising=False)
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        with pytest.raises(CBCConfigError):
            load_from_env()

    def test_returns_config_for_url_only(self, monkeypatch):
        monkeypatch.setenv(ENV_URL, "http://localhost:8001")
        monkeypatch.delenv(ENV_CERT_PATH, raising=False)
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        cfg = load_from_env()
        assert cfg.base_url == "http://localhost:8001"
        assert cfg.cert_path is None
        assert cfg.key_path is None

    def test_returns_config_with_cert_triplet(self, monkeypatch, tmp_path):
        cert = tmp_path / "tls.crt"
        key = tmp_path / "tls.key"
        cert.write_text("cert")
        key.write_text("key")
        monkeypatch.setenv(ENV_CERT_PATH, str(cert))
        monkeypatch.setenv(ENV_KEY_PATH, str(key))
        monkeypatch.setenv(ENV_URL, "https://cbc.example.ondemand.com")
        cfg = load_from_env()
        assert cfg.base_url == "https://cbc.example.ondemand.com"
        assert cfg.cert_path == cert
        assert cfg.key_path == key

    def test_raises_for_incomplete_triplet(self, monkeypatch, tmp_path):
        cert = tmp_path / "tls.crt"
        cert.write_text("cert")
        monkeypatch.setenv(ENV_CERT_PATH, str(cert))
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        monkeypatch.delenv(ENV_URL, raising=False)
        with pytest.raises(CBCConfigError, match="incomplete"):
            load_from_env()

    def test_raises_for_missing_cert_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV_CERT_PATH, str(tmp_path / "missing.crt"))
        with pytest.raises(CBCConfigError, match="does not exist"):
            load_from_env()


# ---------------------------------------------------------------------------
# _read_env_path
# ---------------------------------------------------------------------------


class TestReadEnvPath:
    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("MY_PATH", raising=False)
        assert _read_env_path("MY_PATH") is None

    def test_returns_path_when_file_exists(self, monkeypatch, tmp_path):
        p = tmp_path / "file.pem"
        p.write_text("x")
        monkeypatch.setenv("MY_PATH", str(p))
        assert _read_env_path("MY_PATH") == p

    def test_raises_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MY_PATH", str(tmp_path / "missing.pem"))
        with pytest.raises(CBCConfigError, match="does not exist"):
            _read_env_path("MY_PATH")
