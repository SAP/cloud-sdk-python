"""Unit tests for sap_cloud_sdk.ias token parsing."""

import pytest
import jwt as pyjwt

from sap_cloud_sdk.ias import parse_token, IASClaims, IASTokenError


def _make_token(payload: dict) -> str:
    """Encode a JWT with a dummy secret (signature verification is disabled)."""
    return pyjwt.encode(payload, key="secret", algorithm="HS256")


class TestParseToken:
    def test_all_claims_mapped(self):
        payload = {
            "app_tid": "tenant-abc",
            "at_hash": "abc123hash",
            "aud": "client-id",
            "auth_time": 1700000000,
            "azp": "authorized-party",
            "email": "user@example.com",
            "email_verified": True,
            "exp": 1700003600,
            "family_name": "Doe",
            "given_name": "Jane",
            "groups": ["admins", "users"],
            "ias_apis": ["api-group-1"],
            "ias_iss": "https://tenant.accounts.ondemand.com",
            "iat": 1700000000,
            "iss": "https://tenant.accounts.ondemand.com",
            "jti": "unique-jwt-id",
            "middle_name": "Marie",
            "name": "Jane Marie Doe",
            "nonce": "random-nonce",
            "preferred_username": "jane.doe",
            "sap_gtid": "app-gtid-value",
            "sap_id_type": "user",
            "scim_id": "scim-user-id-xyz",
            "sid": "session-id-123",
            "sub": "subject-unique-id",
            "user_uuid": "global-user-id-xyz",
        }
        claims = parse_token(_make_token(payload))

        assert claims.app_tid == "tenant-abc"
        assert claims.at_hash == "abc123hash"
        assert claims.aud == "client-id"
        assert claims.auth_time == 1700000000
        assert claims.azp == "authorized-party"
        assert claims.email == "user@example.com"
        assert claims.email_verified is True
        assert claims.exp == 1700003600
        assert claims.family_name == "Doe"
        assert claims.given_name == "Jane"
        assert claims.groups == ["admins", "users"]
        assert claims.ias_apis == ["api-group-1"]
        assert claims.ias_iss == "https://tenant.accounts.ondemand.com"
        assert claims.iat == 1700000000
        assert claims.iss == "https://tenant.accounts.ondemand.com"
        assert claims.jti == "unique-jwt-id"
        assert claims.middle_name == "Marie"
        assert claims.name == "Jane Marie Doe"
        assert claims.nonce == "random-nonce"
        assert claims.preferred_username == "jane.doe"
        assert claims.sap_gtid == "app-gtid-value"
        assert claims.sap_id_type == "user"
        assert claims.scim_id == "scim-user-id-xyz"
        assert claims.sid == "session-id-123"
        assert claims.sub == "subject-unique-id"
        assert claims.user_uuid == "global-user-id-xyz"
        assert claims.custom_attributes == {}

    def test_missing_optional_claims_are_none(self):
        claims = parse_token(_make_token({"sub": "only-sub"}))

        assert claims.sub == "only-sub"
        assert claims.app_tid is None
        assert claims.email is None
        assert claims.scim_id is None
        assert claims.groups is None
        assert claims.user_uuid is None
        assert claims.custom_attributes == {}

    def test_empty_payload_returns_all_none(self):
        claims = parse_token(_make_token({}))
        assert isinstance(claims, IASClaims)
        for f in IASClaims.__dataclass_fields__:
            if f == "custom_attributes":
                assert getattr(claims, f) == {}
            else:
                assert getattr(claims, f) is None

    def test_bearer_prefix_stripped(self):
        token = _make_token({"sub": "user-1", "app_tid": "tid-1"})
        claims = parse_token(f"Bearer {token}")

        assert claims.sub == "user-1"
        assert claims.app_tid == "tid-1"

    def test_bearer_prefix_lowercase_stripped(self):
        token = _make_token({"sub": "user-1", "app_tid": "tid-1"})
        claims = parse_token(f"bearer {token}")

        assert claims.sub == "user-1"
        assert claims.app_tid == "tid-1"

    def test_aud_as_list(self):
        claims = parse_token(_make_token({"aud": ["client-a", "client-b"]}))
        assert claims.aud == ["client-a", "client-b"]

    def test_aud_as_string(self):
        claims = parse_token(_make_token({"aud": "single-client"}))
        assert claims.aud == "single-client"

    def test_ias_apis_as_string(self):
        claims = parse_token(_make_token({"ias_apis": "ALL"}))
        assert claims.ias_apis == "ALL"

    def test_sap_gtid_mapped(self):
        claims = parse_token(_make_token({"sap_gtid": "gtid-12345"}))
        assert claims.sap_gtid == "gtid-12345"

    def test_sap_id_type_app(self):
        claims = parse_token(_make_token({"sap_id_type": "app"}))
        assert claims.sap_id_type == "app"

    def test_malformed_token_raises_ias_token_error(self):
        with pytest.raises(IASTokenError):
            parse_token("not.a.valid.jwt")

    def test_empty_string_raises_ias_token_error(self):
        with pytest.raises(IASTokenError):
            parse_token("")

    def test_returns_ias_claims_instance(self):
        claims = parse_token(_make_token({"sub": "x"}))
        assert isinstance(claims, IASClaims)

    def test_user_uuid_mapped(self):
        claims = parse_token(_make_token({"user_uuid": "global-user-id"}))
        assert claims.user_uuid == "global-user-id"

    def test_custom_attributes_captures_unknown_claims(self):
        payload = {"sub": "x", "my_app_claim": "value", "another_custom": 42}
        claims = parse_token(_make_token(payload))

        assert claims.custom_attributes == {"my_app_claim": "value", "another_custom": 42}

    def test_custom_attributes_empty_when_no_unknown_claims(self):
        claims = parse_token(_make_token({"sub": "x", "email": "a@b.com"}))
        assert claims.custom_attributes == {}

    def test_known_claims_not_duplicated_in_custom_attributes(self):
        payload = {"sub": "x", "user_uuid": "uid", "unknown_claim": "yes"}
        claims = parse_token(_make_token(payload))

        assert "sub" not in claims.custom_attributes
        assert "user_uuid" not in claims.custom_attributes
        assert claims.custom_attributes == {"unknown_claim": "yes"}
