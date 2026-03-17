# Destination User Guide

This module integrates with SAP BTP Destination Service to manage destinations, fragments, and certificates at subaccount and service instance levels. It uses a Pythonic dataclass pattern for type-safe message construction.

## Installation

This package is part of the `application_foundation` SDK. Import and use it directly in your application.

## Quick Start

```python
from sap_cloud_sdk.destination import (
    create_client,
    create_fragment_client,
    create_certificate_client,
    Level,
    AccessStrategy
)

# Auto-detection based on environment; in cloud mode it will load credentials
client = create_client(instance="default")
fragment_client = create_fragment_client(instance="default")
certificate_client = create_certificate_client(instance="default")

# Instance-level read
dest = client.get_instance_destination("my-destination")
fragment = fragment_client.get_instance_fragment("my-fragment")
cert = certificate_client.get_instance_certificate("my-cert")

# Subaccount-level read: provider only (no tenant required)
dest = client.get_subaccount_destination("my-destination", access_strategy=AccessStrategy.PROVIDER_ONLY)
fragment = fragment_client.get_subaccount_fragment("my-fragment", access_strategy=AccessStrategy.PROVIDER_ONLY)
cert = certificate_client.get_subaccount_certificate("my-cert", access_strategy=AccessStrategy.PROVIDER_ONLY)

# Subaccount-level read: subscriber-first (tenant required), fallback to provider
dest = client.get_subaccount_destination("my-destination", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-subdomain")
fragment = fragment_client.get_subaccount_fragment("my-fragment", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-subdomain")
cert = certificate_client.get_subaccount_certificate("my-cert", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-subdomain")
```

## Concepts

- Level:
  - SERVICE_INSTANCE: Operates on instance destinations
  - SUB_ACCOUNT: Operates on subaccount destinations

- AccessStrategy (applies to subaccount reads):
  - SUBSCRIBER_ONLY: Only subscriber (tenant required)
  - PROVIDER_ONLY: Only provider (no tenant)
  - SUBSCRIBER_FIRST: Try subscriber, fallback to provider (tenant required)
  - PROVIDER_FIRST: Try provider, fallback to subscriber (tenant required)

## API

### Destination Client

The client produced by `create_client()` exposes the following operations:

```python
class DestinationClient:
    # V1 Admin API - Read operations for destinations
    def get_instance_destination(self, name: str, proxy_enabled: Optional[bool] = None) -> Optional[Destination | TransparentProxyDestination]: ...
    def get_subaccount_destination(self, name: str, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None, proxy_enabled: Optional[bool] = None) -> Optional[Destination | TransparentProxyDestination]: ...
    def list_instance_destinations(self, filter: Optional[ListOptions] = None) -> PagedResult[Destination]: ...
    def list_subaccount_destinations(self, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None, filter: Optional[ListOptions] = None) -> PagedResult[Destination]: ...
    
    # V1 Admin API - Write operations
    def create_destination(self, dest: Destination, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def update_destination(self, dest: Destination, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def delete_destination(self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    
    # V2 Runtime API - Destination consumption with automatic token retrieval
    def get_destination(self, name: str, level: Optional[Level] = None, options: Optional[ConsumptionOptions] = None, proxy_enabled: Optional[bool] = None) -> Optional[Destination | TransparentProxyDestination]: ...
```

### Fragment Client

The fragment client produced by `create_fragment_client()` exposes the following operations:

```python
class FragmentClient:
    def get_instance_fragment(self, name: str) -> Optional[Fragment]: ...
    def get_subaccount_fragment(self, name: str, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None) -> Optional[Fragment]: ...
    def list_instance_fragments(self, filter: Optional[ListOptions] = None) -> PagedResult[Fragment]: ...
    def list_subaccount_fragments(self, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None, filter: Optional[ListOptions] = None) -> PagedResult[Fragment]: ...
    def create_fragment(self, fragment: Fragment, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def update_fragment(self, fragment: Fragment, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def delete_fragment(self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
```

### Certificate Client

The certificate client produced by `create_certificate_client()` exposes the following operations:

```python
class CertificateClient:
    def get_instance_certificate(self, name: str) -> Optional[Certificate]: ...
    def get_subaccount_certificate(self, name: str, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None) -> Optional[Certificate]: ...
    def list_instance_certificates(self, filter: Optional[ListOptions] = None) -> PagedResult[Certificate]: ...
    def list_subaccount_certificates(self, access_strategy: AccessStrategy = AccessStrategy.SUBSCRIBER_FIRST, tenant: Optional[str] = None, filter: Optional[ListOptions] = None) -> PagedResult[Certificate]: ...
    def create_certificate(self, certificate: Certificate, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def update_certificate(self, certificate: Certificate, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
    def delete_certificate(self, name: str, level: Optional[Level] = Level.SUB_ACCOUNT) -> None: ...
```

### Models

- `Destination(name: str, type: str, url?: str, proxy_type?: str, authentication?: str, description?: str, properties?: dict[str, str], auth_tokens?: list[AuthToken], certificates?: list[Certificate])`
  - `auth_tokens` and `certificates` are populated by the v2 consumption API
- `ConsumptionOptions(fragment_name?: str, tenant?: str)` - Options for v2 destination consumption
- `AuthToken(type: str, value: str, http_header: dict, expires_in?: str, error?: str, scope?: str, refresh_token?: str)` - Authentication token from v2 API
- `Fragment(name: str, properties: dict[str, str])`
- `Certificate(name: str, content: str, type: str)`
- `DestinationConfig(url, token_url, client_id, client_secret, identityzone)`
- `TransparentProxy(proxy_name: str, namespace: str)` - Configuration for transparent proxy routing
- `TransparentProxyDestination(name: str, url: str, headers: dict[str, str])` - Destination configured for transparent proxy access
- `ListOptions(name?: str, $skip?: int, $top?: int)` - For pagination and filtering list operations
- `PagedResult[T](items: list[T], pagination?: PaginationInfo)` - Contains results and optional pagination metadata
- `PaginationInfo(next_cursor?: str, total_count?: int)` - Pagination metadata from response headers

**Notes:**
- Unknown string-valued destination fields are captured into `Destination.properties` preserving their original key casing and are included when serializing via `Destination.to_dict`. Non-string unknown fields are ignored.
- Fragment properties are stored as string key-value pairs in `Fragment.properties`.
- Certificate `content` should be base64-encoded. Supported certificate types include PEM, JKS, P12, etc.
- The v2 consumption API returns tokens in the `auth_tokens` field with ready-to-use HTTP headers in `http_header` dict.

## Transparent Proxy Support

The destination client supports routing requests through a transparent proxy. This enables access to on-premise systems and private network resources through a proxy deployed in your Kubernetes cluster.

### Configuration

There are three ways to configure transparent proxy support:

#### 1. Client-Level Default (Recommended)

Enable proxy by default for all destination lookups when creating the client:

```python
from sap_cloud_sdk.destination import create_client

# Default: use_default_proxy=False
# Turning it to true will use TransparentProxy from APPFND_CONHOS_TRANSP_PROXY environment variable
# Turning it to true will use TransparentProxy from APPFND_CONHOS_TRANSP_PROXY environment variable
client = create_client(instance="default", use_default_proxy=True)

# All get operations will use the proxy by default
dest = client.get_instance_destination("my-destination")
# Returns TransparentProxyDestination
```

The environment variable `APPFND_CONHOS_TRANSP_PROXY` should be set with the format `{proxy_name}.{namespace}`:
The environment variable `APPFND_CONHOS_TRANSP_PROXY` should be set with the format `{proxy_name}.{namespace}`:

```bash
export APPFND_CONHOS_TRANSP_PROXY="connectivity-proxy.my-namespace"
```

**This setting might be automatically configured depending on the runtime**

#### 2. Explicit Proxy Configuration

You can set or update the proxy configuration after client creation using the `set_proxy()` method:

```python
from sap_cloud_sdk.destination import create_client, TransparentProxy

# Create client first
client = create_client(instance="default")

# Set custom proxy configuration
transparent_proxy = TransparentProxy(proxy_name="my-destination", namespace="my-namespace")
client.set_proxy(transparent_proxy)
```

#### 3. Per-Request Override

Override the client's default proxy setting for individual requests:

```python
# Client created with use_default_proxy=True (uses proxy by default)
client = create_client(instance="default", use_default_proxy=True)

# Override to NOT use proxy for this specific request
dest = client.get_instance_destination("my-destination", proxy_enabled=False)
# Returns regular Destination

# Or explicitly enable proxy (even if client default is False)
client2 = create_client(instance="default", use_default_proxy=False)
dest2 = client2.get_instance_destination("my-destination", proxy_enabled=True)
# Returns TransparentProxyDestination
```

### Usage Examples

```python
from sap_cloud_sdk.destination import create_client, TransparentProxy, AccessStrategy

# Example 1: Using environment variable with default proxy
client = create_client(instance="default", use_default_proxy=True)
dest = client.get_instance_destination("my-destination")
# Uses proxy from APPFND_CONHOS_TRANSP_PROXY
# Uses proxy from APPFND_CONHOS_TRANSP_PROXY

# Example 2: Explicit proxy configuration with set_proxy()
client = create_client(instance="default")
transparent_proxy = TransparentProxy(proxy_name="my-proxy", namespace="my-namespace")
client.set_proxy(transparent_proxy)
dest = client.get_instance_destination("my-destination", proxy_enabled=True)

# Example 3: Update proxy after creation
client = create_client(instance="default")
transparent_proxy = TransparentProxy(proxy_name="my-destination", namespace="my-namespace")
client.set_proxy(transparent_proxy)
dest = client.get_instance_destination("my-destination", proxy_enabled=True)

# Example 4: Subaccount destination with proxy
client = create_client(instance="default", use_default_proxy=True)
dest = client.get_subaccount_destination(
    name="my-destination",
    access_strategy=AccessStrategy.PROVIDER_ONLY
)
# Uses proxy by default (client's use_default_proxy=True)

# Example 5: Override client default per request
client = create_client(instance="default", use_default_proxy=True)
regular_dest = client.get_instance_destination("my-destination", proxy_enabled=False)
# Returns regular Destination (overrides client default)

# Example 6: V2 API (get_destination) with proxy support
client = create_client(instance="default", use_default_proxy=True)
dest = client.get_destination("my-api", proxy_enabled=True)
# Returns TransparentProxyDestination

# Example 7: V2 API with ConsumptionOptions and proxy disabled
client = create_client(instance="default", use_default_proxy=True)
options = ConsumptionOptions(fragment_name="production", tenant="tenant-1")
dest = client.get_destination("my-api", options=options, proxy_enabled=False)
# Returns regular Destination with merged fragment and tenant context

# Example 8: V2 API with level parameter for optimized lookup
client = create_client(instance="default")
# Search only at instance level
dest = client.get_destination("my-api", level=Level.SERVICE_INSTANCE)
# Search only at subaccount level
dest = client.get_destination("my-api", level=Level.SUB_ACCOUNT)
# No level specified - searches at instance level as default
dest = client.get_destination("my-api")

# Example 9: Combine level with options
options = ConsumptionOptions(fragment_name="production", tenant="tenant-1")
dest = client.get_destination("my-api", level=Level.SUB_ACCOUNT, options=options)
```

### Return Type

When `proxy_enabled=True` (either as client default or per-request override), the methods return a `TransparentProxyDestination` instead of a regular `Destination`:

```python
# TransparentProxyDestination has these properties:
# - name: str - The destination name
# - url: str - The proxy URL (e.g., "http://connectivity-proxy.my-namespace")
# - headers: dict[str, str] - Required headers including "X-destination-name"

client = create_client(instance="default", use_default_proxy=True)
proxy_dest = client.get_instance_destination("my-destination")
print(proxy_dest.name)      # "my-destination"
print(proxy_dest.url)       # "http://connectivity-proxy.my-namespace"
print(proxy_dest.headers)   # {"X-destination-name": "my-destination"}
```

### Setting Custom Headers

The `TransparentProxyDestination` class provides a `set_header()` method to add or update headers required by the transparent proxy. Use the `TransparentProxyHeader` enum to ensure type-safe header names:

```python
from sap_cloud_sdk.destination import (
    create_client,
    TransparentProxyHeader
)

# Get a transparent proxy destination
client = create_client(instance="default", use_default_proxy=True)
proxy_dest = client.get_instance_destination("my-destination")

# Set additional headers using the enum
proxy_dest.set_header(
    TransparentProxyHeader.AUTHORIZATION,
    "Bearer token123"
)

# Access the updated headers
print(proxy_dest.headers)
# {
#   "X-destination-name": "my-destination",
#   "Authorization": "Bearer token123"
# }
```

**Available Headers (TransparentProxyHeader enum):**
- `X_DESTINATION_NAME` - Header for specifying the destination name (automatically set by `from_proxy()`)
- `AUTHORIZATION` - Header for authorization (e.g., "Bearer token", "Basic base64credentials")
- `X_FRAGMENT_NAME` - Header for specifying the fragment name
- `X_TENANT_SUBDOMAIN` - Header for tenant subdomain
- `X_TENANT_ID` - Header for tenant ID
- `X_FRAGMENT_OPTIONAL` - Header for optional fragment flag
- `X_DESTINATION_LEVEL` - Header for destination level
- `X_FRAGMENT_LEVEL` - Header for fragment level
- `X_TOKEN_SERVICE_TENANT` - Header for token service tenant
- `X_CLIENT_ASSERTION` - Header for client assertion
- `X_CLIENT_ASSERTION_TYPE` - Header for client assertion type
- `X_CLIENT_ASSERTION_DESTINATION_NAME` - Header for client assertion destination name
- `X_SUBJECT_TOKEN_TYPE` - Header for subject token type
- `X_ACTOR_TOKEN` - Header for actor token
- `X_ACTOR_TOKEN_TYPE` - Header for actor token type
- `X_REDIRECT_URI` - Header for redirect URI
- `X_CODE_VERIFIER` - Header for code verifier
- `X_CHAIN_NAME` - Header for chain name
- `X_CHAIN_VAR_SUBJECT_TOKEN` - Header for chain variable subject token
- `X_CHAIN_VAR_SUBJECT_TOKEN_TYPE` - Header for chain variable subject token type
- `X_CHAIN_VAR_SAML_PROVIDER_DESTINATION_NAME` - Header for chain variable SAML provider destination name

The `set_header()` method accepts:
- `header`: A `TransparentProxyHeader` enum value
- `value`: The string value for the header

This ensures only valid headers are used with transparent proxy destinations.

### Important Notes

- If `use_default_proxy=True` but no proxy configuration is available in the environment variable, `load_transparent_proxy()` returns `None` and proxy functionality is disabled
- The actual destination configuration is retrieved by the proxy service, not by the SDK
- When `proxy_enabled` is not specified in get methods, the client's default setting (from `use_default_proxy`) is used
- Proxy support is available for all three get methods:
  - `get_instance_destination()` - V1 API for instance-level destinations
  - `get_subaccount_destination()` - V1 API for subaccount-level destinations with access strategies
  - `get_destination()` - V2 API for runtime consumption with automatic token retrieval

## Secret Resolution

### Service Binding

- Mount path: `/etc/secrets/appfnd/destination/{instance}/`
- Keys: `clientid`, `clientsecret`, `url` (auth base), `uri` (service base), `identityzone`
- Fallback env vars: `CLOUD_SDK_CFG_DESTINATION_{INSTANCE}_{FIELD_KEY}` (uppercased)
- Fallback env vars: `CLOUD_SDK_CFG_DESTINATION_{INSTANCE}_{FIELD_KEY}` (uppercased)
- The config loader normalizes to a unified binding:
  - `DestinationConfig(url=..., token_url=..., client_id=..., client_secret=..., identityzone=...)`

### Transparent Proxy

- Environment variable: `APPFND_CONHOS_TRANSP_PROXY`
- Environment variable: `APPFND_CONHOS_TRANSP_PROXY`
- Format: `{proxy_name}.{namespace}` (e.g., `connectivity-proxy.my-namespace`)
- The proxy configuration is loaded and validated when the client is created
- Proxy reachability is tested via HTTP HEAD request to `http://{proxy_name}.{namespace}`

## Tokens and Access Strategy (Cloud Mode)

The OAuth2 token URL is derived from service binding (`DestinationConfig.token_url`). For subscriber context, when a `tenant` is provided, the token provider constructs the subscriber token URL by replacing the identityzone segment with the tenant sub-domain.

## Error Handling

- `DestinationNotFoundError`: mapped from HTTP 404 where applicable
- `DestinationOperationError`: general operation failures
- `HttpError`: HTTP-related or local store read/write errors with `status_code` and `response_text` when applicable

## Notes

- Current implementation omits explicit HTTP retries/timeouts for simplicity.
- The v2 consumption API (`get_destination`) is supported for runtime scenarios requiring automatic token retrieval.
