# SAP Cloud SDK — CBC module

Typed Python client for reading tenant-specific business configuration from
SAP Central Business Configuration (CBC).

## Concepts

**Consumption version** — a snapshot of the business configuration for one app
tenant at a point in time. An app tenant usually has one active version.

**Configuration object** — a logical grouping of related configuration, e.g.
`payment-config` or `agent-config`. Authored by the application or agent team
and shipped as part of a reference content package.

**Entity** — one slice of configuration within a config object. A config
object has one or more related entities; each entity has a stable authored `id`
(e.g. `payment-mode`) and a JSON schema defining its data shape.

**Entity data** — the configuration content for an entity.

## Setup

The recommended entry point is `create_client()` with no arguments. On the SAP
application platform it infers everything from provisioning:

- the application tenant id and the subscriber subdomain come from the SDK-wide
  runtime context (wire `bootstrap(app)` once at startup — see below);
- the CBC URL comes from the tenant-mapping Destination Fragment written during
  provisioning;
- the mTLS certificate comes from the Destination Service.

```python
from sap_cloud_sdk import cbc

cbc_client = cbc.create_client()
config = cbc_client.get_configuration()
```

The mTLS context is resolved once when the client is built and re-invoked only if
a request fails the TLS handshake, so a rotated certificate is picked up
automatically on the next call.

To override any individual piece — for local development, tests, or a bespoke
deployment — pass a `CBCConfig`. See [Overrides](#overrides).

## Reading configuration

### Fetch everything in one call

```python
# latest version resolved automatically
config = cbc_client.get_configuration()

# pin a specific version
config = cbc_client.get_configuration(consumption_version="a0392d4f-72a9-...")

# pick from the list
versions = cbc_client.get_consumption_versions()
cv = versions.latest()  # or versions.items[0], or your own selection logic
config = cbc_client.get_configuration(consumption_version=cv.version)
```

### ConfigurationData structure

```
ConfigurationData
├── consumption_version: str          # e.g. "a0392d4f-72a9-..."
├── app_tenant_id: str
└── configuration_objects: list[ConfigurationObject]
    ├── ConfigurationObject
    │   ├── configuration_object_id: str     # e.g. "payment-config"
    │   └── entities: list[ConfigurationEntity]
    │       └── ConfigurationEntity
    │           ├── entity_id: str        # e.g. "payment-mode"
    │           └── data: EntityData   # .as_list() or .as_object()
    └── ConfigurationObject
        ├── configuration_object_id: str     # e.g. "agent-config"
        └── entities: list[ConfigurationEntity]
            └── ConfigurationEntity
                ├── entity_id: str        # e.g. "contact"
                └── data: EntityData   # .as_list() or .as_object()
```

### Iterate all config objects and entities

```python
for co in config.configuration_objects:
    for ed in co.entities:
        print(f"{co.configuration_object_id}/{ed.entity_id}")
```

### Look up a specific entity

```python
# From already-fetched ConfigurationData
modes = config.get_entity_data("payment-config", "payment-mode")  # EntityData | None
if modes:
    for row in modes.as_list():
        print(row["paymentModeCode"], row["name"])
```

If you need all entities for one config object, use `get_configuration_object` to get the
`ConfigurationObject` and iterate its `entities` list.

`modes.as_list()` returns `list[dict]` and raises `ValueError` if the data is not a list.
`modes.as_object()` returns `dict` and raises `ValueError` if the data is not a dict.

If you don't know the shape in advance, check first with `modes.is_list()` /
`modes.is_object()`, or call `modes.value()` to get the raw `list[dict] | dict`
without any shape assertion:

```python
if modes.is_list():
    rows = modes.as_list()
else:
    settings = modes.as_object()
```

```python
# Unmarshal into your own class
modes_list = [PaymentMode(**row) for row in modes.as_list()]
policy = PolicyConfig(**policy_entity.as_object())
```

### Fetch a single entity directly

When you only need one entity, use `get_entity_data` to avoid fetching all
configuration objects and their entities:

```python
# One targeted HTTP call — no full config fetch
modes = cbc_client.get_entity_data("payment-config", "payment-mode")
for row in modes.as_list():
    print(row["paymentModeCode"], row["name"])

# Pin a specific version
modes = cbc_client.get_entity_data(
    "payment-config", "payment-mode", consumption_version="a0392d4f-..."
)
```


## Feature status

Alongside configuration, CBC tracks which AI features are enabled for an app
tenant. Query the current activation state with `get_feature_statuses`:

```python
statuses = cbc_client.get_feature_statuses()

if statuses.is_enabled("ai_assisted_supplier_bid_analysis"):
    ...
```

`is_enabled(feature_id)` returns `False` for a feature that is disabled or not
present for the tenant. To inspect a feature directly, use `get`:

```python
feature = statuses.get("ai_assisted_tco_analysis")  # FeatureStatus | None
if feature is not None:
    print(feature.feature_id, feature.enabled)
```

To fetch a single feature without pulling the whole list, use
`get_feature_status`, which filters server-side and returns one `FeatureStatus`
(or `None` if the tenant has no entry for it):

```python
feature = cbc_client.get_feature_status("ai_assisted_lead_routing")
if feature is not None and feature.is_enabled():
    ...
```


## Error handling

| Exception | When |
|---|---|
| `CBCClientError` | 4xx from CBC (e.g. tenant not found) |
| `CBCServerError` | 5xx from CBC |
| `CBCNetworkError` | connection failure |
| `CBCConfigError` | the client cannot resolve the tenant mapping or certificate from provisioning |

```python
from sap_cloud_sdk import cbc

try:
    config = cbc_client.get_configuration()
except cbc.CBCClientError as e:
    print(e.code, e.message)  # e.g. "NOT_FOUND", "Tenant unknown"
except cbc.CBCNetworkError:
    ...  # retry / circuit-break
```

## Platform setup

On the SAP application platform `create_client()` needs no arguments. It reads
the application tenant id and the subscriber subdomain from the SDK-wide
**runtime context**, resolves the CBC URL from the tenant's Destination Fragment,
and loads the mTLS certificate from the Destination Service.

The two artifacts it depends on follow the platform convention:

- the app's own provider-level **Destination**, holding the mTLS certificate;
- the tenant-mapping **Fragment**, carrying the CBC URL (written by the platform
  during tenant provisioning).

The runtime context is populated once at startup via `bootstrap(app)`; CBC then
reads `APP_TENANT_ID` and `DWC_SUBDOMAIN` from it per request. You do not set any
CBC-specific context by hand.

```python
from sap_cloud_sdk import bootstrap, cbc

bootstrap(app)  # wires the runtime context (IAS app_tid, dwc-subdomain, …)

# once, at startup — the mTLS context is built here
cbc_client = cbc.create_client()

# per request: nothing CBC-specific to set — the runtime context already carries
# the app tenant id and subdomain for the current request.
config = cbc_client.get_configuration()
```

The CBC URL comes from the `cbcUrl` property of the tenant-mapping fragment. The
client fetches the `CBC_TenantMapping_<subdomain>` fragment for the subscriber's
subdomain directly by name and uses its `cbcUrl` verbatim. The certificate is the
app's own provider-level mTLS certificate, fetched from the Destination Service.

**Performance note.** The fragment lookup (Destination Service HTTP call) runs
on every `get_configuration()` call, because the CBC URL is resolved fresh each
time. For high-throughput agents making frequent CBC calls, consider caching the
resolved URL at the application layer (e.g. per tenant, invalidated on
`CBCClientError` with a not-found code).

**Certificate rotation.** The mTLS certificate is loaded from the Destination
Service and reloaded automatically when a request fails the TLS handshake (as
happens once a certificate has rotated or expired): the client rebuilds its
mTLS context from a freshly-fetched certificate and retries the request once. A
long-lived `create_client()` singleton therefore recovers from rotation on its
own — no need to recreate it.

## Multi-tenancy

- **Supported:** Yes
- **Authentication:** IAS (the `app_tid` claim) for tenant identity; provider-level
  mTLS to CBC. The subscriber subdomain selects the tenant's CBC endpoint.
- **How to use:** Wire `bootstrap(app)` once at startup, then call
  `create_client()` with no arguments. CBC is resolved per request from the
  SDK-wide runtime context: the application tenant id (`APP_TENANT_ID`, the IAS
  `app_tid` claim) is sent as the `appTenantId` query parameter, and the
  subscriber subdomain (`DWC_SUBDOMAIN`) selects the tenant-mapping Destination
  Fragment (`CBC_TenantMapping_<subdomain>`, fetched with
  `AccessStrategy.SUBSCRIBER_ONLY`) whose `cbcUrl` is the per-tenant base URL. A
  single client instance is safe to share across tenants and threads — nothing
  tenant-specific is held on the client; each call reads the current request's
  tenant from the runtime context. For local development or pro-code callers,
  override `base_url` / `app_tenant_id` on `CBCConfig` (see [Overrides](#overrides)).
- **Further reading:** [Platform setup](#platform-setup); `sap_cloud_sdk.core.runtime_context`.

## Overrides

`create_client` accepts an optional `CBCConfig`. Any field left unset is inferred
from provisioning; a field you set wins over its `CLOUD_SDK_CBC_*` env var, which
in turn falls back to the platform default.

| Variable | Default | Description |
|---|---|---|
| `APPFND_CONHOS_LANDSCAPE` | (platform-provided) | Landscape used to derive the certificate name `sap-managed-runtime-ias-{landscape}.pem` |
| `CLOUD_SDK_CBC_CERTIFICATE_NAME` | landscape-derived | Explicit certificate name, overriding the landscape derivation |
| `CLOUD_SDK_CBC_DESTINATION_INSTANCE` | `default` | The `instance` passed to the destination `create_fragment_client` / `create_certificate_client` (used for secret resolution in cloud mode) |
| `CLOUD_SDK_CBC_P12_PASSWORD` | (none) | Password for the certificate keystore, if encrypted |

```python
from sap_cloud_sdk import cbc

# steer the default certificate lookup
cbc_client = cbc.create_client(
    cbc.CBCConfig(cbc_cert_name="my-cert.pem"),
)
```

`CBCConfig` also exposes three override hooks that replace a whole default
resolver — `base_url`, `app_tenant_id` (each a string or a per-request callable),
and `ssl_context`. Set only the axis you want to control:

```python
from sap_cloud_sdk import cbc

# e.g. supply your own mTLS context from a vault, keep provisioning for the rest
client = cbc.create_client(
    cbc.CBCConfig(ssl_context=lambda: my_ctx),
)
```

The `ssl_context` callable you pass still participates in the automatic
reload-on-TLS-failure rotation described above.

> **Note.** The mTLS loader is the default **only** in pure provisioning mode.
> Once you override `base_url` or `app_tenant_id` (for example, to point at a
> local mock), an unset `ssl_context` means plain HTTPS with the public CA bundle
> — set `ssl_context` explicitly if you still need a client certificate.

```python
# local mock: plain HTTP, no certificate needed
client = cbc.create_client(
    cbc.CBCConfig(
        base_url="http://localhost:8001",
        app_tenant_id="my-app-tenant",
    ),
)
```

## Using a test double

`create_client` returns a concrete `CBCClient`. For tests, inject a mock
`httpx.Client` when constructing one directly, or substitute your own stub object
that implements the public methods:

```python
from sap_cloud_sdk import cbc


class StubCBCClient:
    def get_consumption_versions(self): ...
    def get_configuration(self, consumption_version=None):
        return cbc.ConfigurationData(
            consumption_version="cv1",
            app_tenant_id="app-t1",
            configuration_objects=[],
        )

    def get_entity_data(
        self, configuration_object_id, entity_id, consumption_version=None
    ): ...

    def get_feature_statuses(self):
        return cbc.FeatureStatuses(features=[])

    def get_feature_status(self, feature_id):
        return None


def test_my_service():
    service = MyService(cbc_client=StubCBCClient())
    ...
```
