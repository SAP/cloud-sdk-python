"""Unit tests for core auth — mTLSStrategy."""

import os
import ssl
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.core.auth._mtls import mTLSConfig, mTLSStrategy, _read_file, _require_env


# ---------------------------------------------------------------------------
# Helpers — minimal but valid self-signed PEM content for testing
# ---------------------------------------------------------------------------

_FAKE_CERT = """\
-----BEGIN CERTIFICATE-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0000000000000000000000
-----END CERTIFICATE-----
"""

_FAKE_KEY = """\
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC0000000000000000
-----END PRIVATE KEY-----
"""

_FAKE_CA = """\
-----BEGIN CERTIFICATE-----
MIIBsjANBgkqhkiG9w0BAQsFADA0000000000000000000000000000000000000000
-----END CERTIFICATE-----
"""


@pytest.fixture
def pem_files(tmp_path):
    """Write fake PEM content to temp files and return (cert_path, key_path, ca_path)."""
    cert = tmp_path / "tls.crt"
    key = tmp_path / "tls.key"
    ca = tmp_path / "ca.crt"
    cert.write_text(_FAKE_CERT)
    key.write_text(_FAKE_KEY)
    ca.write_text(_FAKE_CA)
    return str(cert), str(key), str(ca)


class TestmTLSConfigDataclass:
    def test_fields_stored(self):
        cfg = mTLSConfig(cert_pem=_FAKE_CERT, key_pem=_FAKE_KEY)
        assert cfg.cert_pem == _FAKE_CERT
        assert cfg.key_pem == _FAKE_KEY
        assert cfg.server_ca_pem is None

    def test_with_server_ca(self):
        cfg = mTLSConfig(cert_pem=_FAKE_CERT, key_pem=_FAKE_KEY, server_ca_pem=_FAKE_CA)
        assert cfg.server_ca_pem == _FAKE_CA

    def test_frozen(self):
        cfg = mTLSConfig(cert_pem=_FAKE_CERT, key_pem=_FAKE_KEY)
        with pytest.raises((AttributeError, TypeError)):
            cfg.cert_pem = "other"  # type: ignore[misc]


class TestmTLSStrategyFromPem:
    def test_from_pem_stores_config(self):
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY)
        assert s._config.cert_pem == _FAKE_CERT
        assert s._config.key_pem == _FAKE_KEY

    def test_from_pem_with_ca(self):
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY, server_ca_pem=_FAKE_CA)
        assert s._config.server_ca_pem == _FAKE_CA


class TestmTLSStrategyFromFiles:
    def test_loads_cert_and_key(self, pem_files):
        cert_path, key_path, _ = pem_files
        s = mTLSStrategy.from_files(cert_path, key_path)
        assert s._config.cert_pem == _FAKE_CERT
        assert s._config.key_pem == _FAKE_KEY
        assert s._config.server_ca_pem is None

    def test_loads_with_ca(self, pem_files):
        cert_path, key_path, ca_path = pem_files
        s = mTLSStrategy.from_files(cert_path, key_path, server_ca_path=ca_path)
        assert s._config.server_ca_pem == _FAKE_CA

    def test_missing_cert_raises(self, tmp_path, pem_files):
        _, key_path, _ = pem_files
        with pytest.raises(FileNotFoundError, match="certificate"):
            mTLSStrategy.from_files(str(tmp_path / "no.crt"), key_path)

    def test_missing_key_raises(self, tmp_path, pem_files):
        cert_path, _, _ = pem_files
        with pytest.raises(FileNotFoundError, match="private key"):
            mTLSStrategy.from_files(cert_path, str(tmp_path / "no.key"))


class TestmTLSStrategyFromBindingPath:
    def test_loads_certificate_and_key_files(self, tmp_path):
        (tmp_path / "certificate").write_text(_FAKE_CERT)
        (tmp_path / "key").write_text(_FAKE_KEY)
        s = mTLSStrategy.from_binding_path(str(tmp_path))
        assert s._config.cert_pem == _FAKE_CERT
        assert s._config.key_pem == _FAKE_KEY

    def test_custom_key_names(self, tmp_path):
        (tmp_path / "tls.crt").write_text(_FAKE_CERT)
        (tmp_path / "tls.key").write_text(_FAKE_KEY)
        s = mTLSStrategy.from_binding_path(
            str(tmp_path), cert_key="tls.crt", key_key="tls.key"
        )
        assert s._config.cert_pem == _FAKE_CERT

    def test_missing_cert_file_raises(self, tmp_path):
        (tmp_path / "key").write_text(_FAKE_KEY)
        with pytest.raises(FileNotFoundError):
            mTLSStrategy.from_binding_path(str(tmp_path))

    def test_optional_server_ca(self, tmp_path):
        (tmp_path / "certificate").write_text(_FAKE_CERT)
        (tmp_path / "key").write_text(_FAKE_KEY)
        (tmp_path / "ca.crt").write_text(_FAKE_CA)
        s = mTLSStrategy.from_binding_path(str(tmp_path), server_ca_key="ca.crt")
        assert s._config.server_ca_pem == _FAKE_CA


class TestmTLSStrategyFromEnv:
    def test_reads_env_vars(self, pem_files, monkeypatch):
        cert_path, key_path, _ = pem_files
        monkeypatch.setenv("MY_CERT", cert_path)
        monkeypatch.setenv("MY_KEY", key_path)
        s = mTLSStrategy.from_env("MY_CERT", "MY_KEY")
        assert s._config.cert_pem == _FAKE_CERT

    def test_missing_env_var_raises(self, monkeypatch):
        monkeypatch.delenv("MISSING_CERT", raising=False)
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with pytest.raises(ValueError, match="MISSING_CERT"):
            mTLSStrategy.from_env("MISSING_CERT", "MISSING_KEY")


class TestmTLSStrategyApplyToSession:
    def test_returns_session(self):
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY)
        import requests
        session = s.apply_to_session(requests.Session())
        assert session is not None
        # cert should be a (path, path) tuple
        assert isinstance(session.cert, tuple)
        assert len(session.cert) == 2

    def test_creates_new_session_when_none(self):
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY)
        session = s.apply_to_session()
        import requests
        assert isinstance(session, requests.Session)

    def test_temp_files_are_readable(self):
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY)
        session = s.apply_to_session()
        assert session.cert is not None
        cert_path, key_path = session.cert
        assert os.path.exists(cert_path)
        assert os.path.exists(key_path)
        # Mode should be owner-read-only
        assert oct(os.stat(cert_path).st_mode)[-3:] == "600"


class TestmTLSStrategyApplyToAsyncClient:
    def test_returns_async_client(self):
        import httpx
        from unittest.mock import patch, MagicMock
        import ssl
        s = mTLSStrategy.from_pem(_FAKE_CERT, _FAKE_KEY)
        # Avoid building a real SSL context from fake PEMs
        with patch.object(mTLSStrategy, "_build_ssl_context", return_value=ssl.create_default_context()):
            client = s.apply_to_async_client()
        assert isinstance(client, httpx.AsyncClient)


class TestHelpers:
    def test_read_file_raises_on_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="test label"):
            _read_file(str(tmp_path / "no_file.pem"), "test label")

    def test_require_env_raises_when_unset(self, monkeypatch):
        monkeypatch.delenv("UNSET_VAR", raising=False)
        with pytest.raises(ValueError, match="UNSET_VAR"):
            _require_env("UNSET_VAR")

    def test_require_env_returns_value(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "/some/path")
        assert _require_env("MY_VAR") == "/some/path"
