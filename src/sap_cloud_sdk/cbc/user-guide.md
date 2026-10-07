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

`base_url` and `app_tenant_id` are supplied as callables, invoked on every
request. In a multi-tenant agent both the CBC URL and the application tenant id
vary per request (resolved from request-scoped context), so the client never
binds them at construction time.

```python
from sap_cloud_sdk import cbc

cbc_client = cbc.create_client(
    base_url=lambda: resolve_cbc_url(),
    app_tenant_id=lambda: resolve_app_tenant_id(),
    ssl_context=lambda: build_ssl_ctx(),
)
```

`ssl_context` is a callable returning a fresh `ssl.SSLContext`. It is resolved
once when the client is built and re-invoked only if a request fails the TLS
handshake, so a rotated certificate is picked up automatically on the next call.

Apps or agents running on the SAP application foundation platform can use `create_agent_client`
instead — it supplies both resolvers and the mTLS context from the platform's
provisioning conventions. See [Platform setup](#platform-setup).

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

### ConfigData structure

```
ConfigData
├── consumption_version: str          # e.g. "a0392d4f-72a9-..."
├── app_tenant_id: str
└── config_objects: list[ConfigObject]
    ├── ConfigObject
    │   ├── config_object_id: str     # e.g. "payment-config"
    │   └── entities: list[ConfigEntity]
    │       └── ConfigEntity
    │           ├── entity_id: str        # e.g. "payment-mode"
    │           └── data: EntityData   # .as_list() or .as_object()
    └── ConfigObject
        ├── config_object_id: str     # e.g. "agent-config"
        └── entities: list[ConfigEntity]
            └── ConfigEntity
                ├── entity_id: str        # e.g. "contact"
                └── data: EntityData   # .as_list() or .as_object()
```

### Iterate all config objects and entities

```python
for co in config.config_objects:
    for ed in co.entities:
        print(f"{co.config_object_id}/{ed.entity_id}")
```

### Look up a specific entity

```python
# From already-fetched ConfigData
modes = config.get_entity_data("payment-config", "payment-mode")  # EntityData | None
if modes:
    for row in modes.as_list():
        print(row["paymentModeCode"], row["name"])
```

If you need all entities for one config object, use `get_config_object` to get the
`ConfigObject` and iterate its `entities` list.

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


## Error handling

| Exception | When |
|---|---|
| `CBCClientError` | 4xx from CBC (e.g. tenant not found) |
| `CBCServerError` | 5xx from CBC |
| `CBCNetworkError` | connection failure |
| `CBCConfigError` | platform adapter cannot resolve the tenant mapping or certificate |

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

Apps running on the SAP application platform can skip wiring the two resolvers by
hand. `create_agent_client` supplies them from the platform's provisioning
conventions: it reads the application tenant id and tenant subdomain from two
SDK-owned `ContextVar`s, resolves the CBC URL from the tenant's Destination
Fragment, and loads the mTLS certificate from the Destination Service.

The two artifacts it depends on follow the platform convention:

- the app's own provider-level **Destination**, holding the mTLS certificate;
- the tenant-mapping **Fragment**, carrying the CBC URL (written by the platform
  during tenant provisioning).

Populate the two ContextVars from your request context — the SDK owns the vars,
your app owns *how* they are filled (e.g. from the IAS JWT `app_tid` claim
and the `dwc-subdomain` header, though the SDK does not mandate the source).

```python
from sap_cloud_sdk import cbc

# once, at startup — the mTLS context is built here
cbc_client = cbc.create_agent_client()

# per request
cbc.app_tenant_id_var.set(parse_token(bearer).app_tid)  # "5649a2cf-..."
cbc.tenant_subdomain_var.set(request.headers["dwc-subdomain"])  # "subscriber-abc"
```

The CBC URL comes from the `cbcUrl` property of the tenant-mapping fragment. The
adapter lists the `CBC_TenantMapping_*` fragments in the subscriber's subaccount
and picks the one whose `appTenantId` property matches; the `cbcUrl` is used
verbatim. The certificate is the app's own provider-level mTLS certificate,
fetched from the Destination Service.

**Performance note.** The fragment lookup (Destination Service HTTP call) runs
on every `get_configuration()` call, because the CBC URL is resolved fresh each
time via the `base_url` callable. For high-throughput agents making frequent CBC
calls, consider caching the resolved URL at the application layer (e.g. per
tenant, invalidated on `CBCClientError` with a not-found code).

**Certificate rotation.** The mTLS certificate is loaded from the Destination
Service and reloaded automatically when a request fails the TLS handshake (as
happens once a certificate has rotated or expired): the client rebuilds its
mTLS context from a freshly-fetched certificate and retries the request once. A
long-lived `create_agent_client()` singleton therefore recovers from rotation on
its own — no need to recreate it.

### Platform env overrides

Defaults cover the common case; override via env when needed:

| Variable | Default | Description |
|---|---|---|
| `APPFND_CONHOS_LANDSCAPE` | (platform-provided) | Landscape used to derive the certificate name `sap-managed-runtime-ias-{landscape}.pem` |
| `CLOUD_SDK_CBC_CERTIFICATE_NAME` | landscape-derived | Explicit certificate name, overriding the landscape derivation |
| `CLOUD_SDK_CBC_DESTINATION_INSTANCE` | `default` | The `instance` passed to the destination `create_fragment_client` / `create_certificate_client` (used for secret resolution in cloud mode) |
| `CLOUD_SDK_CBC_P12_PASSWORD` | (none) | Password for the certificate keystore, if encrypted |

The same three fields can be set in code via `cbc.CBCDestinationConfig`, passed as
`create_agent_client(config=...)`; a value set on the config wins over its env var,
and any field left unset falls back to the env var, then the default.

```python
from sap_cloud_sdk import cbc

cbc_client = cbc.create_agent_client(
    config=cbc.CBCDestinationConfig(cbc_cert_name="my-cert.pem"),
)
```


### Overriding one axis

`create_agent_client` is a fixed preset: it wires all three inputs — `base_url`,
`app_tenant_id`, and the mTLS `ssl_context` — from the platform conventions. To
keep *most* of that but override a single axis (say, supply your own mTLS context
from a vault while keeping the fragment-based `base_url` and the ContextVar
`app_tenant_id`), compose the generic `create_client` with the public platform
resolvers:

```python
from sap_cloud_sdk import cbc

client = cbc.create_client(
    base_url=lambda: cbc.resolve_base_url("default"),
    app_tenant_id=cbc.resolve_app_tenant_id,
    ssl_context=lambda: my_ctx,  # your own mTLS, still reloaded on TLS failure
)
```

`resolve_base_url(destination_instance)`, `resolve_app_tenant_id`, and
`load_ssl_context(destination_instance, cert_name, p12_password)` are the same
resolvers the preset uses; mix in your own callable for the axis you want to
control. The `ssl_context` callable you pass still participates in the automatic
reload-on-TLS-failure rotation described above.

## Using a test double

`CBCClient` is a `Protocol` — implement it directly in tests:

```python
from sap_cloud_sdk import cbc


class StubCBCClient:
    def get_consumption_versions(self): ...
    def get_configuration(self, consumption_version=None):
        return cbc.ConfigData(
            consumption_version="cv1",
            app_tenant_id="app-t1",
            config_objects=[],
        )


def test_my_service():
    service = MyService(cbc_client=StubCBCClient())
    ...
```
