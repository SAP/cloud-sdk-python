# Audit Log NG User Guide

This module provides an OTLP/gRPC client for sending structured audit log events to the SAP Audit Log Service (v3/NG). It sends events as OpenTelemetry (OTLP) LogRecords over gRPC and supports:

- **mTLS** (mutual TLS with client certificates)
- **Insecure** mode (local testing / no-auth)
- **Binary protobuf** and **JSON** serialization formats
- **Destination-based configuration** — resolve connection parameters automatically from a named SAP Destination (SPII-based deployments)

## Installation

### Required Dependencies

```
grpcio>=1.60.0
protobuf>=4.25.0
protovalidate>=0.13.0
opentelemetry-api>=1.28.0
opentelemetry-sdk>=1.28.0
opentelemetry-exporter-otlp-proto-grpc>=1.28.0
```

### Generated Protobuf Code

The client depends on generated protobuf classes.

## Quick Start

The minimal recommended call is just `tenant` — `destination_name` and `destination_instance`
default to the values provisioned for SPII-based deployments:

```python
from sap_cloud_sdk.core.auditlog_ng import create_client
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
    auditevent_pb2 as pb,
)
from datetime import datetime, timezone

client = create_client(tenant="tenant_subdomain")

event = pb.DataAccess()
event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
event.common.user_initiator_id = "agent@example.com"
event.common.tenant_id = "9e0d89c9-17cd-439d-8a8b-9c44d3d272f0"
event.channel_type = "API"
event.channel_id = "agent-v1"
event.object_type = "resource"
event.object_id = "resource-001"

event_id = client.send(event)
client.close()
```

The SDK resolves `endpoint`, `deployment_id`, and `namespace` from the destination automatically.

## Usage

### Initialize the Client

**From a Destination (SPII-based deployments):**

You can spell out the destination parameters and pass connection options alongside:

```python
client = create_client(
    tenant="tenant_subdomain",                    # required to activate destination resolution
    destination_name="AuditLogV3_Destination",    # optional — this is the default
    destination_instance="default",               # optional — this is the default
    # fragment_name="AuditLogV3_Fragment_tenant_subdomain",  # optional tenant-specific fragment
    service_name="my-agent",
    batch=True,
)
```

> **Note:** Omitting `tenant` disables destination resolution — `create_client` then expects
> `endpoint`, `deployment_id`, and `namespace` (or a `config=` object) and raises `ValueError`
> otherwise.

**With mTLS (explicit configuration):**

```python
client = create_client(
    endpoint="us30.als.services.cloud.sap:443",
    deployment_id="us30-staging",
    namespace="sap.als",
    cert_file="/path/to/client-certificate_chain.pem",
    key_file="/path/to/private-key.pem",
    ca_file="/path/to/ca.pem",  # optional
)
```

**Insecure mode (local testing):**

```python
client = create_client(
    endpoint="localhost:4317",
    deployment_id="my-deployment",
    namespace="sap.als",
    insecure=True,
)
```

> **Important:** `deployment_id` and `namespace` are validated at construction time.
> Invalid values (e.g. containing spaces) will raise a `ValueError`.

### Build an Audit Event

```python
event = pb.DataAccess()
event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
event.common.user_initiator_id = "agent@example.com"
event.common.tenant_id = "9e0d89c9-17cd-439d-8a8b-9c44d3d272f0"
event.channel_type = "API"
event.channel_id = "agent-v1"
event.object_type = "resource"
event.object_id = "resource-001"
```

> **Tip:** When using `StarletteIASTelemetryMiddleware` (see [Automatic Tenant and User Injection](#automatic-tenant-and-user-injection)), `common.tenant_id` and `common.user_initiator_id` are filled automatically from the incoming IAS JWT. You only need to set them explicitly if you want to override the values from the token.

### Send the Event

**Binary protobuf:**

```python
event_id = client.send(event)
print(f"Sent event with ID: {event_id}")
```

**JSON format:**

```python
event_id = client.send_json(event)
```

### Close the Client

Always close the client when the agent shuts down to flush pending events:

```python
client.close()
```

> Calling `send()` on a closed client raises a `RuntimeError`.

### Full Agent Integration Example

```python
from sap_cloud_sdk.core.auditlog_ng import create_client
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
    auditevent_pb2 as pb,
)
from datetime import datetime, timezone


class AgentAuditLogger:
    def __init__(self, tenant: str):
        self.client = create_client(tenant=tenant)

    def log_data_access(self, user: str, tenant_id: str, resource: str):
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
        event.common.user_initiator_id = user
        event.common.tenant_id = tenant_id
        event.channel_type = "API"
        event.channel_id = "agent-v1"
        event.object_type = "resource"
        event.object_id = resource

        event_id = self.client.send(event)
        return event_id

    def shutdown(self):
        self.client.close()


# In your agent main loop
audit_logger = AgentAuditLogger(tenant="tenant_subdomain")
try:
    event_id = audit_logger.log_data_access(
        user="agent-user@example.com",
        tenant_id="9e0d89c9-17cd-439d-8a8b-9c44d3d272f0",
        resource="sensitive-record-42",
    )
    print(f"Audit event logged: {event_id}")
finally:
    audit_logger.shutdown()
```

### One-Off Sends (Convenience Function)

For simple, one-off audit events without managing a persistent client:

```python
from sap_cloud_sdk.core.auditlog_ng import create_client

with create_client(tenant="tenant_subdomain") as client:
    event_id = client.send(event)
```

### Event Serialization Formats

| Method        | Format             | MIME Type              |
|---------------|--------------------|------------------------|
| `send()`      | Binary protobuf    | `application/protobuf` |
| `send_json()` | JSON               | `application/json`     |

### Automatic Tenant and User Injection

When `StarletteIASTelemetryMiddleware` is registered on your app, it parses the
incoming `Authorization: Bearer <token>` header on every request and stores the
IAS claims in the current async context.

`AuditClient.send()` reads that context automatically before validation and
back-fills two fields on the event's `common` block — only if they are not
already set by the caller:

| Field populated | IAS claim used |
|---|---|
| `common.tenant_id` | `app_tid` |
| `common.user_initiator_id` | `user_uuid` |

#### Setup

Register the middleware once when your app starts:

```python
from sap_cloud_sdk.core.telemetry import auto_instrument
from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

app = FastAPI(...)
auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app)])
```

#### Usage

With the middleware in place, you can omit `tenant_id` and `user_initiator_id`
from every event — they are injected automatically:

```python
event = pb.DataAccess()
event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
# tenant_id and user_initiator_id are filled from the IAS JWT automatically
event.channel_type = "API"
event.channel_id = "agent-v1"
event.object_type = "resource"
event.object_id = "resource-001"

event_id = client.send(event)
```

If neither the middleware nor an explicit value provides `tenant_id`, the event
will fail `protovalidate` validation and raise a `ValidationError`.

## Configuration

`create_client` supports three mutually exclusive ways to provide configuration. They are evaluated in this order of precedence:

1. **Explicit config object** — pass a pre-built `AuditLogNGConfig` via `config=`. When provided, it takes precedence over the other paths.
2. **Destination-based resolution (recommended)** — pass `tenant`; connection parameters are resolved from the named SAP Destination automatically. This is the recommended path for SPII-based deployments.
3. **Explicit keyword arguments** — pass `endpoint`, `deployment_id`, and `namespace` directly.

### Destination-based configuration parameters

| Parameter              | Type   | Required | Default                    | Description |
|------------------------|--------|----------|----------------------------|-------------|
| `tenant`               | `str`  | Yes      | —                          | Tenant subdomain. **Required to activate destination-based resolution.** |
| `destination_name`     | `str`  | No       | `"AuditLogV3_Destination"` | Name of the SAP Destination to resolve. |
| `destination_instance` | `str`  | No       | `"default"`                | Destination service binding instance name. |
| `fragment_name`        | `str`  | No       | `None`                     | Destination fragment merged before resolution (for tenant-specific overrides). Follows the pattern `AuditLogV3_Fragment_{tenant_subdomain}`. |

The destination must expose these custom properties:

| Property           | Required | Description |
|--------------------|----------|-------------|
| `deploymentId`     | Yes (or `deploymentRegion`) | Deployment identifier. Falls back to `deploymentRegion` when absent or empty. |
| `deploymentRegion` | Fallback | Used as `deployment_id` when `deploymentId` is missing or empty. |
| `namespace`        | Yes      | Audit log namespace (e.g. `sap.als`). |

The destination `url` is used as the OTLP endpoint. The lookup is always performed at subaccount level.

### Explicit configuration parameters for `AuditClient`

| Parameter       | Type    | Required | Default        | Description                                                                                           |
|-----------------|---------|----------|----------------|-------------------------------------------------------------------------------------------------------|
| `endpoint`      | `str`   | Yes      | —              | OTLP endpoint of the Audit Log Service (`host:port`)                                             |
| `deployment_id` | `str`   | Yes      | —              | Deployment/region identifier. Validated: only `[a-zA-Z0-9._/~-]` allowed. Raises `ValueError` if invalid. |
| `namespace`     | `str`   | Yes      | —              | Audit log namespace (e.g. `sap.als`). Same character-set validation as `deployment_id`.               |
| `cert_file`     | `str`   | No       | `None`         | Path to the mTLS client certificate file (PEM). Required together with `key_file` for mTLS.           |
| `key_file`      | `str`   | No       | `None`         | Path to the mTLS client private key file (PEM). Required together with `cert_file` for mTLS.          |
| `ca_file`       | `str`   | No       | `None`         | Path to a custom CA certificate (PEM) for server verification. Uses system trust store if omitted.    |
| `insecure`      | `bool`  | No       | `False`        | Disable TLS entirely (plaintext gRPC).                                                                |
| `service_name`  | `str`   | No       | `"audit-client"` | OpenTelemetry `service.name` resource attribute attached to every log record.                       |
| `batch`         | `bool`  | No       | `False`        | When `True`, uses `BatchLogRecordProcessor` (better throughput, small delay). When `False`, uses `SimpleLogRecordProcessor` (immediate, lower throughput). |
| `compression`   | `bool`  | No       | `True`         | Enable gzip compression on the gRPC channel (`grpc.Compression.Gzip`). Set to `False` to disable.    |
| `schema_url`    | `str`   | No       | `SCHEMA_URL`   | OpenTelemetry schema URL attached to the logger. Defaults to the canonical ALS proto schema URL.      |

### Example values

| Parameter       | Production example                                |
|-----------------|---------------------------------------------------|
| `endpoint`      | `us30.als.services.cloud.sap:443`                 |
| `deployment_id` | `us30-staging`                                    |
| `namespace`     | `sap.als`                                         |
| `cert_file`     | `/path/to/client-certificate_chain.pem`           |
| `key_file`      | `/path/to/private-key.pem`                        |
| `ca_file`       | `/path/to/ca.pem`                                 |
| `insecure`      | `False`                                           |
| `service_name`  | `"my-agent"`                                      |
| `batch`         | `True` (high-throughput agents)                   |
| `compression`   | `True`                                            |

## Multi-tenancy

- **Supported:** N/A at auth level
- **Authentication:** None (uses Destination Service / SPII for transport)
- **How to use:** Tenant identity is embedded in each event payload via the `tenant_id` field. Transport and auth are handled by the Destination Service / SPII. This module is only available through SAP for ME.
- **Further reading:**
  - [SAP Audit Log Service — SAP Help Portal](https://help.sap.com/docs/btp/sap-business-technology-platform/audit-log-service)

## Error Handling

Events are validated against protobuf constraints using `protovalidate` before sending.
`AuditClient.send()` (and `send_json()`) can raise:

- `ValidationError` — the event fails `protovalidate` schema validation. This is a subclass of `AuditLogNGError`.
- `ValueError` — `common.tenant_id` is not a string, or contains characters outside `[a-zA-Z0-9._/~-]`.
- `RuntimeError` — `send()` was called on a client that has already been closed.
