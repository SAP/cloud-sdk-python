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

```python
from sap_cloud_sdk.cbc import create_client, TenantContext

# single-tenant: bind tenant IDs at startup
client = create_client(
    tenant_context=TenantContext(cbcTenantId="<cbc-tenant-id>", appTenantId="<app-tenant-id>")
)

# multi-tenant: callable is invoked on every request
client = create_client(tenant_context=lambda: resolve_tenant_from_request_context())
```

For local development against a mock server, set `CLOUD_SDK_CBC_REPLACE_SUBDOMAIN=false` to disable subdomain rewriting:

```bash
CLOUD_SDK_CBC_URL=http://localhost:8001 CLOUD_SDK_CBC_REPLACE_SUBDOMAIN=false python my_agent.py
```

## Reading configuration

### Fetch everything in one call

```python
# latest version resolved automatically
config = client.get_configuration()

# pin a specific version
config = client.get_configuration(consumption_version="a0392d4f-72a9-...")

# pick from the list
versions = client.get_consumption_versions()
cv = versions.latest()   # or versions.items[0], or your own selection logic
config = client.get_configuration(consumption_version=cv.version)
```

### ConfigData structure

```
ConfigData
├── consumption_version: str          # e.g. "a0392d4f-72a9-..."
├── tenant_context: TenantContext
└── config_objects: list[ConfigObject]
    ├── ConfigObject
    │   ├── config_object_id: str     # e.g. "payment-config"
    │   └── entities: list[EntityData]
    │       └── EntityData
    │           ├── entity_id: str        # e.g. "payment-mode"
    │           └── data: EntityContent   # .as_list() or .as_object()
    └── ConfigObject
        ├── config_object_id: str     # e.g. "agent-config"
        └── entities: list[EntityData]
            └── EntityData
                ├── entity_id: str        # e.g. "contact"
                └── data: EntityContent   # .as_list() or .as_object()
```

### Iterate all config objects and entities

```python
for co in config.config_objects:
    for ed in co.entities:
        print(f"{co.config_object_id}/{ed.entity_id}")
```

### Look up a specific entity

```python
# All entities for one config object
payment = config.get_config_object("payment-config")   # ConfigObject | None
if payment:
    modes = payment.get_entity("payment-mode")         # EntityData | None
    if modes:
        for row in modes.data.as_list():
            print(row["paymentModeCode"], row["name"])
```

`modes.data.as_list()` returns `list[dict]` and raises `ValueError` if the data is not a list.
`modes.data.as_object()` returns `dict` and raises `ValueError` if the data is not a dict.

```python
# Shortcut — config object + entity in one step
modes = config.get_entity_data("payment-config", "payment-mode")  # EntityData | None
```

```python
# Unmarshal into your own class
modes_list = [PaymentMode(**row) for row in modes.data.as_list()]
policy = PolicyConfig(**policy_entity.data.as_object())
```


## Error handling

| Exception | When |
|---|---|
| `CBCClientError` | 4xx from CBC (e.g. tenant not found) |
| `CBCServerError` | 5xx from CBC |
| `CBCNetworkError` | connection failure |
| `CBCConfigError` | missing or incomplete credentials at startup |

```python
from sap_cloud_sdk.cbc import CBCClientError, CBCServerError, CBCNetworkError

try:
    config = client.get_configuration(tenant)
except CBCClientError as e:
    print(e.code, e.message)   # e.g. "NOT_FOUND", "Tenant unknown"
except CBCNetworkError:
    ...  # retry / circuit-break
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `CLOUD_SDK_CBC_URL` | yes | Base URL of the CBC service |
| `CLOUD_SDK_CBC_CERT_PATH` | prod only | Path to the mTLS client certificate (PEM file) |
| `CLOUD_SDK_CBC_KEY_PATH` | prod only | Path to the mTLS private key (PEM file) |
| `CLOUD_SDK_CBC_CERT` | prod only | mTLS client certificate value (PEM string, alternative to `CERT_PATH`) |
| `CLOUD_SDK_CBC_KEY` | prod only | mTLS private key value (PEM string, alternative to `KEY_PATH`) |
| `CLOUD_SDK_CBC_REPLACE_SUBDOMAIN` | no | Override subdomain replacement (`true`/`false`). Defaults to `true`. Set to `false` when pointing at a local mock server. |

`CERT_PATH`/`KEY_PATH` (file paths) take precedence over `CERT`/`KEY` (values) when both are set.

## Using a test double

`CBCClient` is a `Protocol` — implement it directly in tests:

```python
from sap_cloud_sdk.cbc import CBCClient, ConfigData, TenantContext

class StubCBCClient:
    def get_consumption_versions(self, tenant_context):
        ...
    def get_configuration(self, tenant_context, consumption_version=None):
        return ConfigData(
            consumption_version="cv1",
            tenant_context=tenant_context,
            config_objects=[],
        )

def test_my_service():
    service = MyService(cbc_client=StubCBCClient())
    ...
```
