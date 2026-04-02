# IAS User Guide

This module provides utilities for working with SAP Identity Authentication Service (IAS).

## Import

```python
from sap_cloud_sdk.ias import parse_token, IASClaims, IASTokenError
```

---

## Token Parsing

Use `parse_token` to decode an IAS JWT token into a typed dataclass. All standard IAS claims are mapped to named attributes.

> **Note:** `parse_token` does **not** verify the token signature. Validate the token against the IAS JWKS endpoint in your framework or middleware before using the extracted claims for authorization decisions.

```python
from sap_cloud_sdk.ias import parse_token

claims = parse_token(request.headers["Authorization"])  # accepts "Bearer <token>" or raw token

print(claims.app_tid)           # tenant ID (multitenant scenarios)
print(claims.scim_id)           # SCIM-based user ID in SAP Cloud Identity Services
print(claims.sub)               # OIDC subject identifier
print(claims.email)             # user email (when email scope was requested)
```

### Claims Reference

All fields on `IASClaims` are `Optional` — claims absent from the token are `None`.

| Attribute            | Claim                | Description                                                                                   |
|----------------------|----------------------|-----------------------------------------------------------------------------------------------|
| `app_tid`            | `app_tid`            | SAP tenant of the application. Present in multitenant scenarios.                              |
| `at_hash`            | `at_hash`            | Hash of the access token, used to bind the ID token to an access token.                       |
| `aud`                | `aud`                | Audience — recipient(s) of the token. `str` or `List[str]`.                                   |
| `auth_time`          | `auth_time`          | Time of user authentication (seconds since Unix epoch).                                       |
| `azp`                | `azp`                | Authorized party — client ID to which the ID token was issued.                                |
| `email`              | `email`              | User email address. Requires `email` scope.                                                   |
| `email_verified`     | `email_verified`     | Whether the email address has been verified. Requires `email` scope.                          |
| `exp`                | `exp`                | Expiration time (seconds since Unix epoch).                                                   |
| `family_name`        | `family_name`        | Surname. Requires `profile` scope.                                                            |
| `given_name`         | `given_name`         | Given name. Requires `profile` scope.                                                         |
| `groups`             | `groups`             | Groups the user belongs to. Requires `groups` scope.                                          |
| `ias_apis`           | `ias_apis`           | SAP API permission groups, or a fixed value when all APIs are consumed. `str` or `List[str]`. |
| `ias_iss`            | `ias_iss`            | SAP tenant identifier — stable even when using a custom domain.                               |
| `iat`                | `iat`                | Issued-at time (seconds since Unix epoch).                                                    |
| `iss`                | `iss`                | Issuer URL, e.g. `https://<tenant>.accounts.ondemand.com`.                                    |
| `jti`                | `jti`                | Unique JWT identifier, used to prevent replay attacks. Requires `profile` scope.              |
| `middle_name`        | `middle_name`        | Middle name of the user.                                                                      |
| `name`               | `name`               | Full display name.                                                                            |
| `nonce`              | `nonce`              | Session nonce to mitigate replay attacks.                                                     |
| `preferred_username` | `preferred_username` | Human-readable username.                                                                      |
| `sap_id_type`        | `sap_id_type`        | Token type: `"user"` for user credentials, `"app"` for application credentials.               |
| `scim_id`            | `scim_id`            | User's SCIM ID in SAP Cloud Identity Services.                                                |
| `sid`                | `sid`                | Session ID for tracking a user session across applications.                                   |
| `sub`                | `sub`                | Subject — unique identifier for the user, scoped to the issuer.                               |

> Claims are only present if the corresponding scope was requested during authentication. For example, `email` and `email_verified` require the `email` scope, and `given_name`/`family_name`/`jti` require the `profile` scope.


#### With Telemetry

```python
from sap_cloud_sdk.ias import parse_token
from sap_cloud_sdk.core.telemetry import set_tenant_id, add_span_attribute

claims = parse_token(token)
set_tenant_id(claims.app_tid or "")
add_span_attribute("enduser.id", claims.scim_id or claims.sub or "")
```