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

claims = parse_token(
    request.headers["Authorization"]
)  # accepts "Bearer <token>" or raw token

print(claims.app_tid)  # tenant ID (multitenant scenarios)
print(claims.scim_id)  # SCIM-based user ID in SAP Cloud Identity Services
print(claims.sub)  # OIDC subject identifier
print(claims.email)  # user email (when email scope was requested)
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

---

## Verified Claims

`parse_token` decodes the JWT without verifying its signature. For security-sensitive consumers — telemetry identity attributes, audit context — use `IASVerifier` to perform JWKS-backed signature verification before trusting the claims.

### IASVerifier

`IASVerifier` is a built-in verifier that fetches signing keys from the IAS JWKS endpoint and validates the token's signature, issuer, algorithm, and expiry. It auto-configures itself from the environment:

- **Cloud Foundry**: reads `VCAP_SERVICES` → `identity[0]` or `xsuaa[0]` credentials.
- **Kubernetes (managed runtime)**: reads the `identity-service` secret mounted at `/etc/secrets/appfnd/identity-service/default/` — mounted automatically by the agent deployment template, no `app.yaml` changes needed.
- **Manual / local**: reads `IAS_URL` (and optionally `IAS_CLIENT_ID`) environment variables.

```python
from sap_cloud_sdk.ias import IASVerifier, IASConfigError

# Auto-configure from VCAP_SERVICES (CF), K8s secret mount, or IAS_URL env var
try:
    verifier = IASVerifier.from_env()
except IASConfigError:
    # No IAS binding found — handle gracefully
    ...

# Or configure explicitly
verifier = IASVerifier(ias_url="https://my-tenant.accounts.ondemand.com", client_id="my-client-id")

# Verify a token — raises IASTokenError on any failure
verified = verifier("Bearer <token>")
claims = verified.claims  # IASClaims, provably from IAS
```

`IASVerifier` pins algorithms to `RS256` and `ES256` (asymmetric only), caches signing keys internally, and handles key rotation transparently.

### VerifiedIASClaims

`VerifiedIASClaims` is a frozen dataclass that wraps `IASClaims`. Its presence is the SDK's provenance marker: an instance can only be obtained by calling a `TokenVerifier` that ran signature verification. Never construct it directly from `parse_token` output in security-sensitive code.

```python
from sap_cloud_sdk.ias import VerifiedIASClaims, IASClaims

verified: VerifiedIASClaims = verifier("Bearer <token>")
claims: IASClaims = verified.claims  # access the underlying claims
```

### Zero-config with StarletteIASTelemetryMiddleware

When an IAS service binding is present, `StarletteIASTelemetryMiddleware` auto-configures `IASVerifier.from_env()` and verifies every token before stamping span attributes or setting the auth context — no extra code required:

```python
from starlette.applications import Starlette
from sap_cloud_sdk.core.telemetry import auto_instrument
from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

app = Starlette(...)
# IASVerifier auto-configured from VCAP_SERVICES or IAS_URL
auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app)])
```

If no binding is found, a WARNING is logged at startup and identity attributes are not stamped until a binding is added. See [Telemetry user guide](../core/telemetry/user-guide.md#built-in-starletteiastelemetrymiddleware) for details.
