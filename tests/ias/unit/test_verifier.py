"""Unit tests for sap_cloud_sdk.ias IASVerifier."""

import json
import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.ias import IASClaims, IASConfigError, IASTokenError, IASVerifier, VerifiedIASClaims


class TestIASVerifierFromEnv:
    def test_cf_vcap_services_identity_binding(self, monkeypatch):
        vcap = {"identity": [{"credentials": {"url": "https://ias.example.com", "clientid": "my-app"}}]}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.delenv("IAS_URL", raising=False)
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._ias_url == "https://ias.example.com"
        assert v._client_id == "my-app"

    def test_cf_vcap_services_strips_trailing_slash(self, monkeypatch):
        vcap = {"identity": [{"credentials": {"url": "https://ias.example.com/", "clientid": "cid"}}]}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.delenv("IAS_URL", raising=False)
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._ias_url == "https://ias.example.com"

    def test_cf_vcap_services_no_client_id(self, monkeypatch):
        vcap = {"identity": [{"credentials": {"url": "https://ias.example.com"}}]}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.delenv("IAS_URL", raising=False)
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._client_id is None

    def test_cf_vcap_services_xsuaa_fallback(self, monkeypatch):
        vcap = {"xsuaa": [{"credentials": {"url": "https://xsuaa.example.com", "clientid": "xc"}}]}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.delenv("IAS_URL", raising=False)
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._ias_url == "https://xsuaa.example.com"

    def test_k8s_env_vars(self, monkeypatch):
        monkeypatch.delenv("VCAP_SERVICES", raising=False)
        monkeypatch.setenv("IAS_URL", "https://k8s-ias.example.com")
        monkeypatch.setenv("IAS_CLIENT_ID", "k8s-client")
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._ias_url == "https://k8s-ias.example.com"
        assert v._client_id == "k8s-client"

    def test_k8s_env_vars_no_client_id(self, monkeypatch):
        monkeypatch.delenv("VCAP_SERVICES", raising=False)
        monkeypatch.setenv("IAS_URL", "https://k8s-ias.example.com")
        monkeypatch.delenv("IAS_CLIENT_ID", raising=False)
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._client_id is None

    def test_raises_when_nothing_configured(self, monkeypatch):
        monkeypatch.delenv("VCAP_SERVICES", raising=False)
        monkeypatch.delenv("IAS_URL", raising=False)
        monkeypatch.delenv("IAS_CLIENT_ID", raising=False)
        with pytest.raises(IASConfigError):
            IASVerifier.from_env()

    def test_raises_with_malformed_vcap(self, monkeypatch):
        monkeypatch.setenv("VCAP_SERVICES", "not-valid-json")
        monkeypatch.delenv("IAS_URL", raising=False)
        with pytest.raises(IASConfigError):
            IASVerifier.from_env()

    def test_raises_with_empty_bindings(self, monkeypatch):
        vcap = {"identity": [], "xsuaa": []}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.delenv("IAS_URL", raising=False)
        with pytest.raises(IASConfigError):
            IASVerifier.from_env()

    def test_vcap_takes_precedence_over_env_var(self, monkeypatch):
        vcap = {"identity": [{"credentials": {"url": "https://vcap-ias.example.com", "clientid": "vc"}}]}
        monkeypatch.setenv("VCAP_SERVICES", json.dumps(vcap))
        monkeypatch.setenv("IAS_URL", "https://env-ias.example.com")
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier.from_env()
        assert v._ias_url == "https://vcap-ias.example.com"


class TestIASVerifierCall:
    def _make_verifier(self, ias_url="https://ias.example.com", client_id=None):
        with patch("sap_cloud_sdk.ias._verifier.PyJWKClient"):
            v = IASVerifier(ias_url=ias_url, client_id=client_id)
        return v

    def _mock_jwk_key(self, verifier):
        mock_key = MagicMock()
        mock_key.key = "mock-signing-key"
        verifier._jwk_client.get_signing_key_from_jwt.return_value = mock_key
        return mock_key

    def test_returns_verified_ias_claims_on_success(self):
        import jwt as pyjwt
        verifier = self._make_verifier()
        raw_token = pyjwt.encode({"sap_gtid": "t1", "user_uuid": "u1"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {"sap_gtid": "t1", "user_uuid": "u1", "iss": "https://ias.example.com"}
            result = verifier(f"Bearer {raw_token}")
        assert isinstance(result, VerifiedIASClaims)
        assert result.claims.sap_gtid == "t1"

    def test_strips_bearer_prefix(self):
        import jwt as pyjwt
        verifier = self._make_verifier()
        raw_token = pyjwt.encode({"sub": "x"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            verifier(f"Bearer {raw_token}")
        call_args = verifier._jwk_client.get_signing_key_from_jwt.call_args[0][0]
        assert call_args == raw_token

    def test_raises_on_bad_signature(self):
        import jwt.exceptions
        verifier = self._make_verifier()
        verifier._jwk_client.get_signing_key_from_jwt.side_effect = jwt.exceptions.InvalidSignatureError("bad")
        with pytest.raises(IASTokenError, match="IAS JWT verification failed"):
            verifier("Bearer bad.token")

    def test_raises_on_expired_token(self):
        import jwt.exceptions
        verifier = self._make_verifier()
        verifier._jwk_client.get_signing_key_from_jwt.side_effect = jwt.exceptions.ExpiredSignatureError("exp")
        with pytest.raises(IASTokenError):
            verifier("Bearer expired")

    def test_raises_on_wrong_issuer(self):
        import jwt.exceptions
        verifier = self._make_verifier()
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.exceptions.InvalidIssuerError("iss")
            with pytest.raises(IASTokenError):
                verifier("Bearer tok")

    def test_raises_on_wrong_audience(self):
        import jwt.exceptions
        verifier = self._make_verifier(client_id="expected")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.exceptions.InvalidAudienceError("aud")
            with pytest.raises(IASTokenError):
                verifier("Bearer tok")

    def test_pins_asymmetric_algorithms_only(self):
        import jwt as pyjwt
        verifier = self._make_verifier()
        raw_token = pyjwt.encode({"sub": "x"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            verifier(f"Bearer {raw_token}")
        _, kwargs = mock_decode.call_args_list[0]
        assert kwargs["algorithms"] == ["RS256", "ES256"]
        assert "none" not in kwargs["algorithms"]
        assert "HS256" not in kwargs["algorithms"]

    def test_requires_exp_and_iss(self):
        import jwt as pyjwt
        verifier = self._make_verifier()
        raw_token = pyjwt.encode({"sub": "x"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            verifier(f"Bearer {raw_token}")
        _, kwargs = mock_decode.call_args_list[0]
        assert "exp" in kwargs["options"]["require"]
        assert "iss" in kwargs["options"]["require"]

    def test_includes_audience_when_client_id_set(self):
        import jwt as pyjwt
        verifier = self._make_verifier(client_id="my-client")
        raw_token = pyjwt.encode({"sub": "x"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            verifier(f"Bearer {raw_token}")
        _, kwargs = mock_decode.call_args_list[0]
        assert kwargs.get("audience") == "my-client"
        assert "aud" in kwargs["options"]["require"]

    def test_skips_audience_when_no_client_id(self):
        import jwt as pyjwt
        verifier = self._make_verifier(client_id=None)
        raw_token = pyjwt.encode({"sub": "x"}, key="s", algorithm="HS256")
        self._mock_jwk_key(verifier)
        with patch("sap_cloud_sdk.ias._verifier.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            verifier(f"Bearer {raw_token}")
        _, kwargs = mock_decode.call_args_list[0]
        assert "audience" not in kwargs
        assert kwargs["options"].get("verify_aud") is False
