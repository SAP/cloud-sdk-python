# SAP Cloud SDK for Python

This SDK provides consistent interfaces for interacting with foundational services such as object storage, destination management, audit logging, telemetry, and secure credential handling.

The Python SDK offers a clean, type-safe API following Python best practices while maintaining compatibility with the SAP Application Foundation ecosystem.

---

## Available Modules

- [AuditLog User Guide](../src/cloud_sdk_python/core/auditlog/user-guide.md) - Compliance audit logging for SAP Audit Log Service
- [Destination User Guide](../src/cloud_sdk_python/destination/user-guide.md) - SAP BTP Destination Service integration with proxy support
- [ObjectStore User Guide](../src/cloud_sdk_python/objectstore/user-guide.md) - S3-compatible object storage
- [Secret Resolver User Guide](../src/cloud_sdk_python/core/secret_resolver/user-guide.md) - Secure credential management from mounted volumes and environment variables
- [Telemetry User Guide](../src/cloud_sdk_python/core/telemetry/user-guide.md) - OpenTelemetry tracing and GenAI auto-instrumentation

---

## Installation

TODO: To be defined

---

## Quick Start

```python
from cloud_sdk_python.objectstore import create_client

# Create an ObjectStore client (auto-detects local vs cloud)
client = create_client("my-instance")

# Upload a file
client.put_object_from_bytes(
    name="example.txt",
    data=b"Hello, World!", 
    content_type="text/plain"
)
```

---

## Key Features

- 🤖 **AI Core Integration**
- 📋 **Audit Log Service**
- 🌐 **Destination Service**
- 🗂️ **ObjectStore Service**
- 🔐 **Secret Resolver**
- 📊 **Telemetry & Observability**

---

## Requirements

- **Python**: 3.11 or higher

## Environment Configuration

The SDK automatically resolves configuration from multiple sources with the following priority:

1. **Kubernetes-mounted secrets**: `/etc/secrets/<module>/<instance>/<field>`
2. **Environment variables**: `<MODULE>_<INSTANCE>_<FIELD>`
   - For instance names, hyphens (`"-"`) are replaced with underscores (`"_"`) for compatibility with system environment variables.

### ObjectStore Configuration Example

```bash
# Environment variables for ObjectStore with instance name "credentials"
export OBJECTSTORE_CREDENTIALS_ACCESS_KEY_ID="your-access-key"
export OBJECTSTORE_CREDENTIALS_SECRET_ACCESS_KEY="your-secret-key"  
export OBJECTSTORE_CREDENTIALS_BUCKET="your-bucket-name"
export OBJECTSTORE_CREDENTIALS_HOST="s3.amazonaws.com"
```

### Kubernetes Mounted Secrets Example

```
/etc/secrets/objectstore/credentials/
├── access_key_id
├── secret_access_key
├── bucket
└── host
```

### Telemetry Configuration

For production environments (SAP BTP Managed Runtime), no configuration is needed as `OTEL_EXPORTER_OTLP_ENDPOINT` is automatically injected.

For local development:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otel-collector.example.com"
```

---

## Usage Examples

### Audit Logging

```python
from cloud_sdk_python.core.auditlog import (create_client, SecurityEvent)

# Create client )
client = create_client()

# Security event - authentication attempt
security_event = SecurityEvent(
    data="User login attempt",
    user="john.doe",
    tenant=Tenant.PROVIDER,
    identity_provider="SAP ID",
    ip="192.168.1.100",
    attributes=[
        SecurityEventAttribute("login_method", "password"),
        SecurityEventAttribute("session_id", "abc123")
    ]
)
client.log(security_event)
```

### Secret Resolver

Securely load configuration and credentials from Kubernetes mounted volumes or environment variables:

```python
from dataclasses import dataclass, field
from cloud_sdk_python.core.secret_resolver import read_from_mount_and_fallback_to_env_var

# Load configuration
config = DatabaseConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="MYAPP",
    module="database", 
    instance="primary",
    target=config
)
```

### Telemetry with GenAI Auto-instrumentation

Comprehensive telemetry and observability for AI applications with automatic instrumentation:

```python
from cloud_sdk_python.core.telemetry import (
    auto_instrument, context_overlay, GenAIOperation,
    chat_span, execute_tool_span, invoke_agent_span,
    record_metrics, set_tenant_id, add_span_attribute
)

# Enable auto-instrumentation before importing AI libraries
auto_instrument()

from litellm import completion
import openai

# Set tenant for multi-tenant applications
set_tenant_id("tenant-123")

# Basic GenAI operation tracking
with context_overlay(GenAIOperation.CHAT, attributes={"user.id": "123"}):
    response = completion(model="gpt-4", messages=[{"role": "user", "content": "Hello"}])

# Manual metrics and spans
@record_metrics(module="myapp", operation="data_processing")
def process_data(data):
    add_span_attribute("data.size", len(data))
    # Processing logic
    return processed_data
```
