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

---

## Verified Claims (Security-Sensitive Consumers)

`parse_token` is a low-level claim extractor — it does not authenticate the token. For security-sensitive consumers (telemetry identity, audit attribution) use the `TokenVerifier` / `VerifiedIASClaims` pattern to prove that a token was cryptographically verified before its claims are used.

```python
from sap_cloud_sdk.ias import VerifiedIASClaims, TokenVerifier
```

### `VerifiedIASClaims`

A frozen dataclass wrapper around `IASClaims`. Its existence at runtime means "these claims came through a verifier." Create an instance **only** inside your verifier function, after a successful signature check.

```python
@dataclass(frozen=True)
class VerifiedIASClaims:
    claims: IASClaims
```

### `TokenVerifier`

A type alias for the verifier callable contract:

```python
TokenVerifier = Callable[[str], VerifiedIASClaims]
```

The callable receives the raw `Authorization` header value (may include `"Bearer "`), **must raise** (fail closed) on any invalid token, and returns `VerifiedIASClaims` on success.

### Implementing a JWKS-based verifier

For apps deployed on SAP BTP where JWT signature verification is not already handled by the platform (e.g. Kyma Istio JWT `RequestAuthentication` policy), implement a real JWKS verifier using `PyJWKClient` from `PyJWT`:

```python
import jwt
from jwt import PyJWKClient
from sap_cloud_sdk.ias import parse_token, VerifiedIASClaims, IASTokenError


def make_ias_verifier(jwks_url: str, issuer: str, audience: str):
    """Build a token verifier backed by IAS JWKS key rotation.

    Args:
        jwks_url:  IAS JWKS endpoint, e.g. "https://<tenant>.accounts.ondemand.com/oauth2/certs"
        issuer:    Expected token issuer, e.g. "https://<tenant>.accounts.ondemand.com"
        audience:  Expected audience / client_id of this application

    Returns:
        A TokenVerifier callable.
    """
    jwk_client = PyJWKClient(jwks_url)  # caches keys; thread-safe

    def verify(authorization: str) -> VerifiedIASClaims:
        raw = authorization.removeprefix("Bearer ").removeprefix("bearer ").strip()
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(raw)  # selects by kid
            jwt.decode(
                raw,
                signing_key.key,
                algorithms=["RS256", "ES256"],   # pin asymmetric algs; NEVER "none" or HS*
                issuer=issuer,
                audience=audience,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.exceptions.PyJWTError as e:
            raise IASTokenError(f"IAS token verification failed: {e}") from e
        return VerifiedIASClaims(claims=parse_token(raw))

    return verify
```

**Required validations:** `PyJWT` enforces signature via the JWKS key, `kid` selection via `PyJWKClient`, issuer (`iss`), audience (`aud`/`azp`), expiration (`exp`), and not-before (`nbf`). Do **not** accept `alg=none`, HS256/HS512 (symmetric), or tokens without `exp`/`iss`/`aud`.

**Dependency note:** RSA/EC signature verification requires the `cryptography` package. Install it alongside `PyJWT`:

```bash
pip install "PyJWT[cryptography]"
```

### Platform pre-verified adapter

For apps where the deployment platform (e.g. Kyma Istio `RequestAuthentication`, UCL mTLS) has already verified the JWT before the request reaches your app, you can use a thin adapter that trusts the platform verification and delegates claim extraction to `parse_token`:

```python
from sap_cloud_sdk.ias import parse_token, VerifiedIASClaims

def platform_pre_verified(authorization: str) -> VerifiedIASClaims:
    # Platform auth (e.g. Istio/UCL) verified the JWT before routing here.
    # parse_token() is safe here as a claim extractor only.
    return VerifiedIASClaims(claims=parse_token(authorization))
```

> **Important:** only use this adapter when you have confirmed that your deployment platform enforces JWT verification on every request that carries an `Authorization` header.

---

## Claims Reference

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
| `user_uuid`          | `user_uuid`          | SAP claim identifying the global user ID.                                                     |
| `custom_attributes`  | *(any)*              | Claims not in the standard IAS set. Always a `dict`, empty if no custom claims are present.   |

### Custom Attributes

Any claim not in the standard IAS set lands in `custom_attributes` as a plain dict, so nothing is silently dropped:

```python
claims = parse_token(token)
print(claims.custom_attributes)  # {"my_app_claim": "value", ...}
```


#### With Telemetry

```python
from sap_cloud_sdk.ias import parse_token
from sap_cloud_sdk.core.telemetry import set_tenant_id, add_span_attribute

claims = parse_token(token)
set_tenant_id(claims.app_tid or "")
add_span_attribute("enduser.id", claims.scim_id or claims.sub or "")
```
