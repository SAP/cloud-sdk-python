"""IAS JWT token parsing.

Decodes SAP IAS JWT tokens without signature verification and maps
all standard IAS claims to a typed dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

import jwt

from sap_cloud_sdk.ias.exceptions import IASTokenError


@dataclass
class IASClaims:
    """Typed representation of SAP IAS JWT token claims.

    All fields are optional — a claim absent from the token is None.

    Attributes:
        app_tid: SAP claim identifying the tenant of the application.
            Used in multitenant scenarios (e.g. subscribed BTP applications).
        at_hash: Hash of the access token. Can be used to bind the ID token
            to an access token and prevent token substitution attacks.
        aud: Audience — recipient(s) of the token. Can be a string or list
            of client IDs.
        auth_time: Time when the user authenticated (seconds since Unix epoch).
        azp: Authorized party — client ID to which the ID token was issued.
        email: Email address of the user. Included when the email scope is
            requested.
        email_verified: Whether the email address has been verified.
        exp: Expiration time after which the token must not be accepted
            (seconds since Unix epoch).
        family_name: Surname (last name) of the user. Included when the
            profile scope is requested.
        given_name: Given name (first name) of the user. Included when the
            profile scope is requested.
        groups: Groups the user belongs to, associated with authorizations.
            Included when the groups scope is requested.
        ias_apis: SAP claim listing API permission groups or a fixed value
            when all APIs of an application are consumed.
        ias_iss: SAP claim identifying the SAP tenant even when the token was
            issued from a custom domain in a non-SAP domain.
        iat: Time when the token was issued (seconds since Unix epoch).
        iss: Issuer of the token, typically a URL such as
            https://<tenant>.accounts.ondemand.com.
        jti: Unique identifier for the JWT, used to prevent replay attacks.
            Included when the profile scope is requested.
        middle_name: Middle name of the user.
        name: Full display name of the user.
        nonce: String associated with the client session to mitigate replay
            attacks.
        preferred_username: Human-readable display name / username of the user.
        sap_id_type: SAP claim identifying the type of token.
            ``"app"`` for application credentials, ``"user"`` for user
            credentials.
        scim_id: SAP claim identifying the user by their SCIM ID in SAP Cloud
            Identity Services.
        sid: Session ID used to track a user session across applications and
            logout scenarios.
        sub: Subject — unique identifier for the user, scoped to the issuer.
    """

    app_tid: Optional[str] = None
    at_hash: Optional[str] = None
    aud: Optional[Union[str, List[str]]] = None
    auth_time: Optional[int] = None
    azp: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    exp: Optional[int] = None
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    groups: Optional[List[str]] = None
    ias_apis: Optional[Union[str, List[str]]] = None
    ias_iss: Optional[str] = None
    iat: Optional[int] = None
    iss: Optional[str] = None
    jti: Optional[str] = None
    middle_name: Optional[str] = None
    name: Optional[str] = None
    nonce: Optional[str] = None
    preferred_username: Optional[str] = None
    sap_id_type: Optional[str] = None
    scim_id: Optional[str] = None
    sid: Optional[str] = None
    sub: Optional[str] = None


def parse_token(token: str) -> IASClaims:
    """Parse an SAP IAS JWT token and return its claims.

    Decodes the token without signature verification. The token is not
    validated against a JWKS endpoint — callers are responsible for
    ensuring the token has already been verified by their framework or
    middleware before using the extracted claims.

    Args:
        token: A JWT string, optionally prefixed with ``"Bearer "`` or ``"bearer "``.

    Returns:
        IASClaims with all present token claims populated. Absent claims
        are None.

    Raises:
        IASTokenError: If the token is malformed and cannot be decoded.

    Example:
        ```python
        from sap_cloud_sdk.ias import parse_token

        claims = parse_token(request.headers["Authorization"])
        print(claims.app_tid)    # tenant ID
        print(claims.scim_id)    # SCIM-based user ID
        print(claims.sub)        # OIDC subject identifier
        ```
    """
    raw = token.removeprefix("Bearer ").removeprefix("bearer ").strip()

    try:
        payload: dict = jwt.decode(
            raw,
            options={"verify_signature": False},
            algorithms=["RS256", "ES256", "HS256"],
        )
    except jwt.exceptions.DecodeError as e:
        raise IASTokenError(f"Failed to decode IAS token: {e}") from e

    return IASClaims(
        app_tid=payload.get("app_tid"),
        at_hash=payload.get("at_hash"),
        aud=payload.get("aud"),
        auth_time=payload.get("auth_time"),
        azp=payload.get("azp"),
        email=payload.get("email"),
        email_verified=payload.get("email_verified"),
        exp=payload.get("exp"),
        family_name=payload.get("family_name"),
        given_name=payload.get("given_name"),
        groups=payload.get("groups"),
        ias_apis=payload.get("ias_apis"),
        ias_iss=payload.get("ias_iss"),
        iat=payload.get("iat"),
        iss=payload.get("iss"),
        jti=payload.get("jti"),
        middle_name=payload.get("middle_name"),
        name=payload.get("name"),
        nonce=payload.get("nonce"),
        preferred_username=payload.get("preferred_username"),
        sap_id_type=payload.get("sap_id_type"),
        scim_id=payload.get("scim_id"),
        sid=payload.get("sid"),
        sub=payload.get("sub"),
    )
