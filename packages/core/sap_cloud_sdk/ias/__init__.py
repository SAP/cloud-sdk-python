"""SAP Cloud SDK for Python - IAS module

Utilities for parsing SAP Identity Authentication Service (IAS) JWT tokens.

Usage:
    from sap_cloud_sdk.ias import parse_token, IASClaims

    claims = parse_token(request.headers["Authorization"])
    print(claims.app_tid)           # tenant ID (multitenant scenarios)
    print(claims.scim_id)           # SCIM-based user ID
    print(claims.sub)               # OIDC subject identifier
    print(claims.email)             # user email (when email scope requested)
"""

from sap_cloud_sdk.ias._token import IASClaims, parse_token
from sap_cloud_sdk.ias.exceptions import IASTokenError

__all__ = [
    "IASClaims",
    "parse_token",
    "IASTokenError",
]
