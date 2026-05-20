# Using the `auditlog_ng` Client in an Agent

This module provides an OTLP/gRPC client for sending structured audit log events
 to the SAP Audit Log Service (v3/NG). It supports mTLS, insecure mode for local
 testing, and both binary protobuf and JSON serialization formats.

---

## Overview

The Auditlog NG client sends audit log events as OpenTelemetry (OTLP) LogRecords over gRPC to the SAP Audit Log Service. It supports:

- **mTLS** (mutual TLS with client certificates)
- **Insecure** mode (local testing / no-auth)
- **Binary protobuf** and **JSON** serialization formats

---

## Prerequisites

### 1. Required Dependencies

```text
grpcio>=1.60.0
protobuf>=4.25.0
protovalidate>=0.13.0
opentelemetry-api>=1.28.0
opentelemetry-sdk>=1.28.0
opentelemetry-exporter-otlp-proto-grpc>=1.28.0
```

### 2. Generated Protobuf Code

The client depends on generated protobuf classes.

---

## Configuration

All constructor parameters for `AuditClient`:

| Parameter       | Type    | Required | Default        | Description                                                                                           |
|-----------------|---------|----------|----------------|-------------------------------------------------------------------------------------------------------|
| `endpoint`      | `str`   | ✅ Yes   | —              | OTLP gRPC endpoint of the Audit Log Service (`host:port`). When deploying on BTP, derive from the SPII payload: `endpoint_from_region(assignedTenant.deploymentRegion)` → e.g. `us30.als.services.cloud.sap:443`. |
| `deployment_id` | `str`   | ✅ Yes   | —              | Deployment/region identifier. Validated: only `[a-zA-Z0-9._-/~]` allowed. Raises `ValueError` if invalid. |
| `namespace`     | `str`   | ✅ Yes   | —              | Audit log namespace (e.g. `sap.als`). Same character-set validation as `deployment_id`.               |
| `cert_file`     | `str`   | ❌ No    | `None`         | Path to the mTLS client certificate file (PEM). Required together with `key_file` for mTLS.           |
| `key_file`      | `str`   | ❌ No    | `None`         | Path to the mTLS client private key file (PEM). Required together with `cert_file` for mTLS.          |
| `ca_file`       | `str`   | ❌ No    | `None`         | Path to a custom CA certificate (PEM) for server verification. Uses system trust store if omitted.    |
| `insecure`      | `bool`  | ❌ No    | `False`        | Disable TLS entirely (plaintext gRPC).                                                                |
| `service_name`  | `str`   | ❌ No    | `"audit-client"` | OpenTelemetry `service.name` resource attribute attached to every log record.                       |
| `batch`         | `bool`  | ❌ No    | `False`        | When `True`, uses `BatchLogRecordProcessor` (better throughput, small delay). When `False`, uses `SimpleLogRecordProcessor` (immediate, lower throughput). |
| `compression`   | `bool`  | ❌ No    | `True`         | Enable gzip compression on the gRPC channel (`grpc.Compression.Gzip`). Set to `False` to disable.    |
| `schema_url`    | `str`   | ❌ No    | `SCHEMA_URL`   | OpenTelemetry schema URL attached to the logger. Defaults to the canonical ALS proto schema URL.      |

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

---

## Usage in an Agent

### Step 1: Import the Client and Generated Protobuf

```python
from sap_cloud_sdk.core.auditlog_ng import create_client, AuditLogNGConfig, endpoint_from_region
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import auditevent_pb2 as pb
```

### Step 2: Initialize the Client

**With SPII payload (BTP production):**

```python
client = create_client(
    endpoint=endpoint_from_region(spii_payload["assignedTenant"]["deploymentRegion"]),
    deployment_id=spii_payload["assignedTenant"]["deploymentId"],
    namespace=spii_payload["assignedTenant"]["applicationNamespace"],
    cert_file="/path/to/client-certificate_chain.pem",
    key_file="/path/to/private-key.pem",
)
```

**With explicit endpoint (production):**

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

> ⚠️ **Important:** `deployment_id` and `namespace` are validated at construction time.
> Invalid values (e.g. containing spaces) will raise a `ValueError`.

### Step 3: Build an Audit Event

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

### Step 4: Send the Event

**Binary protobuf:**

```python
event_id = client.send(event, "DataAccess")
print(f"Sent event with ID: {event_id}")
```

**JSON format:**

```python
event_id = client.send_json(event, "DataAccess")
```

> The `event_type` argument is optional. If omitted, the client derives it from the protobuf descriptor name (e.g., `"sap.als.AuditEvent.DataAccess.v2"`).

### Step 5: Close the Client

Always close the client when the agent shuts down to flush pending events:

```python
client.close()
```

> Calling `send()` on a closed client raises a `RuntimeError`.

---

## Full Agent Integration Example

```python
from sap_cloud_sdk.core.auditlog_ng import create_client
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import auditevent_pb2 as pb
from datetime import datetime, timezone


class AgentAuditLogger:
    def __init__(self):
        self.client = create_client(
            endpoint="us30.als.services.cloud.sap:443",
            deployment_id="us30-staging",
            namespace="sap.als",
            cert_file="/path/to/client-certificate_chain.pem",
            key_file="/path/to/private-key.pem",
        )

    def log_data_access(self, user: str, tenant_id: str, resource: str):
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
        event.common.user_initiator_id = user
        event.common.tenant_id = tenant_id
        event.channel_type = "API"
        event.channel_id = "agent-v1"
        event.object_type = "resource"
        event.object_id = resource

        event_id = self.client.send(event, "DataAccess")
        return event_id

    def shutdown(self):
        self.client.close()


# In your agent main loop
audit_logger = AgentAuditLogger()
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

---

## One-Off Sends (Convenience Function)

For simple, one-off audit events without managing a persistent client:

```python
from sap_cloud_sdk.core.auditlog_ng import create_client

with create_client(
    endpoint="us30.als.services.cloud.sap:443",
    deployment_id="us30-staging",
    namespace="sap.als",
    cert_file="/path/to/cert.pem",
    key_file="/path/to/key.pem",
) as client:
    event_id = client.send(event, "DataAccess")
```

---

## Event Serialization Formats

| Method        | Format             | MIME Type              |
|---------------|--------------------|------------------------|
| `send()`      | Binary protobuf    | `application/protobuf` |
| `send_json()` | JSON               | `application/json`     |

---

## Validation

Events are validated against protobuf constraints using `protovalidate` before sending. A `ValueError` is raised if:

- The event fails schema validation
- The `tenant_id` is not a valid UUID
- The client has already been closed

---

## BTP / SPII Integration

When running on BTP, the agent receives a SPII payload at tenant-assign time. Use `endpoint_from_region` to derive the ALS NG endpoint and store all required values via the Destination Service so they are available at emit time.

### SPII field mapping

| SPII field | Parameter |
| --- | --- |
| `assignedTenant.deploymentRegion` | `endpoint_from_region(region)` |
| `assignedTenant.deploymentId` | `deployment_id` |
| `assignedTenant.applicationNamespace` | `namespace` |
| `assignedTenant.applicationTenantId` | `event.common.tenant_id` (per event) |

### At SPII assign time

```python
from sap_cloud_sdk.core.auditlog_ng import endpoint_from_region
from sap_cloud_sdk.destination._models import Destination

region = spii_payload["assignedTenant"]["deploymentRegion"]
destination = Destination(
    name="AuditLogV3_Destination",
    type="TCP",
    url=endpoint_from_region(region),
    properties={
        "deployment_id": spii_payload["assignedTenant"]["deploymentId"],
        "namespace":     spii_payload["assignedTenant"]["applicationNamespace"],
    }
)
# persist via Destination Service client
```

### At emit time

```python
from sap_cloud_sdk.core.auditlog_ng import create_client

dest = await destination_client.get_destination("AuditLogV3_Destination")
with create_client(
    endpoint=dest.url,
    deployment_id=dest.properties["deployment_id"],
    namespace=dest.properties["namespace"],
    cert_file="/path/to/client-certificate_chain.pem",
    key_file="/path/to/private-key.pem",
) as client:
    client.send(event, "DataAccess")
```

---

## Running the Unit Tests

```bash
    uv run pytest tests/core/unit/auditlog_ng/
```
