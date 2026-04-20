"""Internal IAS JWT claim name definitions."""

from enum import Enum


class _IASClaim(str, Enum):
    APP_TID = "app_tid"
    AT_HASH = "at_hash"
    AUD = "aud"
    AUTH_TIME = "auth_time"
    AZP = "azp"
    EMAIL = "email"
    EMAIL_VERIFIED = "email_verified"
    EXP = "exp"
    FAMILY_NAME = "family_name"
    GIVEN_NAME = "given_name"
    GROUPS = "groups"
    IAS_APIS = "ias_apis"
    IAS_ISS = "ias_iss"
    IAT = "iat"
    ISS = "iss"
    JTI = "jti"
    MIDDLE_NAME = "middle_name"
    NAME = "name"
    NONCE = "nonce"
    PREFERRED_USERNAME = "preferred_username"
    SAP_GTID = "sap_gtid"
    SAP_ID_TYPE = "sap_id_type"
    SCIM_ID = "scim_id"
    SID = "sid"
    SUB = "sub"
    USER_UUID = "user_uuid"


_KNOWN_CLAIM_VALUES: frozenset[str] = frozenset(c.value for c in _IASClaim)
