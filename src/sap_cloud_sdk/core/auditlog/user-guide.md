# Audit Log User Guide

This module provides a unified API for logging audit events that comply with the SAP Audit Log Service OpenAPI specification. It supports both cloud-based and local logging depending on the environment and uses a Pythonic dataclass pattern for type-safe message construction.

The module handles configuration, message construction, formatting, and transport of audit log entries — so developers can focus on business logic while ensuring compliance with audit requirements.

## Installation

The audit log module is part of the SAP Cloud SDK for Python and is automatically available when the SDK is installed.

## Import

You can import specific classes:

```python
from sap_cloud_sdk.core.auditlog import (
    create_client,
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    Tenant,
    SecurityEventAttribute,
    DataAccessAttribute,
    ChangeAttribute
)
```

Or use star import for convenience:

```python
from sap_cloud_sdk.core.auditlog import *
```

## Quick Start

### Basic Setup

Use `create_client()` to get a client with automatic environment detection:

```python
from sap_cloud_sdk.core.auditlog import create_client, SecurityEvent

client = create_client()

# Create and log a security event
security_event = SecurityEvent(
    data="User login attempt",
    success=True,
    user="john.doe",
    tenant=Tenant.PROVIDER
)

client.log(security_event)
```

### Custom Configuration

There's also support for custom configuration:

```python
from sap_cloud_sdk.core.auditlog import create_client, AuditLogConfig

config = AuditLogConfig(
    service_url="https://api.auditlog.cf.example.com/audit-log/oauth2/v2",
    oauth_url="https://example.authentication.com/oauth/token",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

client = create_client(config=config)
```

## Event Types

The module supports six types of audit events:

1. **Security Events**: Authentication, authorization, and security-related activities
2. **Data Access Events**: Reading or accessing personal/sensitive data (GDPR compliance)
3. **Data Modification Events**: Creating, updating, or modifying personal/sensitive data
4. **Data Deletion Events**: Deleting personal/sensitive data (specialized for deletions)
5. **Configuration Change Events**: System configuration and settings changes
6. **Configuration Deletion Events**: Deleting system configurations (specialized for deletions)

## Unified Logging Interface

The audit client provides a single `log()` method that accepts any audit event type. All events are Python dataclasses with built-in validation to ensure required fields are present.

**Optional fields for all events:**

- `user`: defaults to `$USER`
- `tenant`: defaults to `Tenant.PROVIDER`
- `custom_details`: additional custom information as a dictionary

### Security Events

Security events record authentication attempts, authorization failures, and other security-relevant activities.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, SecurityEvent, SecurityEventAttribute, Tenant
)

client = create_client()

security_event = SecurityEvent(
    data="User authentication failed",
    success=False,
    user="john.doe",
    tenant=Tenant.PROVIDER,
    identity_provider="SAP ID",
    ip="192.168.1.100",
    attributes=[
        SecurityEventAttribute("login_method", "password"),
        SecurityEventAttribute("failure_reason", "invalid_credentials")
    ]
)

client.log(security_event)
```

**Required fields for Security Events:**

- `data`: must not be empty
- `success`: must be explicitly set

### Data Access Events

Data access events record when personal or sensitive data is read or accessed. This is particularly important for GDPR compliance and data privacy auditing.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, DataAccessEvent, DataAccessAttribute, Tenant
)

client = create_client()

data_access = DataAccessEvent(
    success=True,
    object_type="database",
    object_id={"table": "customers", "schema": "public"},
    subject_type="customer",
    subject_id={"customer_id": "12345"},
    subject_role="end_user",
    attributes=[
        DataAccessAttribute("email", successful=True),
        DataAccessAttribute("phone_number", successful=True)
    ],
    user="service-account",
    tenant=Tenant.PROVIDER,
    identity_provider="OAuth2"
)

client.log(data_access)
```

**Required fields for Data Access Events:**

- `object_type`: Type of the data object
- `object_id`: Dictionary identifying the data object
- `subject_type`: Type of the data subject
- `subject_id`: Dictionary identifying the data subject
- `attributes`: at least one attribute with name (successful is optional)
- `success`: must be explicitly set

### Data Modification Events

Data modification events record when personal or sensitive data is created, updated, or deleted. This includes tracking old and new values for compliance purposes.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, DataModificationEvent, ChangeAttribute, Tenant
)

client = create_client()

data_modification = DataModificationEvent(
    success=True,
    object_type="user_profile",
    object_id={"profile_id": "profile-123"},
    subject_type="user",
    subject_id={"user_id": "user-456"},
    subject_role="customer",
    attributes=[
        ChangeAttribute("email", "new@example.com", "old@example.com"),
        ChangeAttribute("phone", "+0987654321", "+1234567890")
    ],
    user="admin-user",
    tenant=Tenant.PROVIDER
)

client.log(data_modification)
```

**Required fields for Data Modification Events:**

- `object_type`: Type of the data object
- `object_id`: Dictionary identifying the data object
- `subject_type`: Type of the data subject
- `subject_id`: Dictionary identifying the data subject
- `attributes`: at least one attribute with name and new value (old is optional)
- `success`: must be explicitly set

### Configuration Change Events

Configuration change events record when system configurations, settings, or other non-personal data is modified.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, ConfigurationChangeEvent, ChangeAttribute, Tenant
)

client = create_client()

config_change = ConfigurationChangeEvent(
    success=True,
    object_type="system_config",
    object_id={"component": "authentication", "setting": "timeout"},
    attributes=[
        ChangeAttribute("session_timeout", "60", "30"),
        ChangeAttribute("max_attempts", "5", "3")
    ],
    user="system-admin",
    tenant=Tenant.PROVIDER,
    id="config-change-001"
)

client.log(config_change)
```

**Required fields for Configuration Change Events:**

- `object_type`: Type of the data object
- `object_id`: Dictionary identifying the data object
- `attributes`: at least one attribute with name and new value (old is optional)
- `success`: must be explicitly set

### Data Deletion Events

Data deletion events are specialized for tracking when personal or sensitive data is deleted from the system. They use `DeletedAttribute` to record what was removed.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, DataDeletionEvent, DeletedAttribute, Tenant
)

client = create_client()

data_deletion = DataDeletionEvent(
    success=True,
    object_type="user_profile",
    object_id={"profile_id": "profile-123"},
    subject_type="user",
    subject_id={"user_id": "user-456"},
    subject_role="customer",
    attributes=[
        DeletedAttribute("email", "deleted@example.com"),
        DeletedAttribute("phone", "+1234567890"),
        DeletedAttribute("personal_notes")
    ],
    user="admin-user",
    tenant=Tenant.PROVIDER
)

client.log(data_deletion)
```

**Required fields for Data Deletion Events:**

- `object_type`: Type of the data object
- `object_id`: Dictionary identifying the data object
- `subject_type`: Type of the data subject
- `subject_id`: Dictionary identifying the data subject
- `attributes`: at least one attribute with name (old value is optional)
- `success`: must be explicitly set

### Configuration Deletion Events

Configuration deletion events track when system configurations or settings are removed from the system.

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, ConfigurationDeletionEvent, DeletedAttribute, Tenant
)

client = create_client()

config_deletion = ConfigurationDeletionEvent(
    success=True,
    object_type="feature_flag",
    object_id={"component": "ui", "flag": "new_dashboard"},
    attributes=[
        DeletedAttribute("enabled", "true"),
        DeletedAttribute("rollout_percentage", "50"),
        DeletedAttribute("target_users")
    ],
    user="system-admin",
    tenant=Tenant.PROVIDER,
    id="config-deletion-001"
)

client.log(config_deletion)
```

**Required fields for Configuration Deletion Events:**

- `object_type`: Type of the configuration object
- `object_id`: Dictionary identifying the configuration object
- `attributes`: at least one attribute with name (old value is optional)
- `success`: must be explicitly set

### Using Custom Details

All event types support custom details for additional context:

```python
security_event = SecurityEvent(
    data="User login attempt",
    success=True,
    custom_details={
        "request_id": "req-123",
        "correlation_id": "corr-456",
        "source_ip": "10.0.0.1",
        "user_agent": "MyApp/1.0"
    }
)

client.log(security_event)
```

## Error Handling

Always handle exceptions when logging audit events:

```python
from sap_cloud_sdk.core.auditlog import create_client, SecurityEvent
from sap_cloud_sdk.core.auditlog.exceptions import AuditLogError

client = create_client()

security_event = SecurityEvent(
    data="Login attempt",
    success=False
)

try:
    client.log(security_event)
except AuditLogError as e:
    # Handle the error appropriately
    print(f"Failed to log security event: {e}")

    # Consider whether to fail the operation or continue
    # Audit logging failures should generally not break business logic
```

## Batch Logging

The audit client supports batch logging for efficiency when logging multiple events:

```python
from sap_cloud_sdk.core.auditlog import (
    create_client, SecurityEvent, DataAccessEvent, DataAccessAttribute
)

client = create_client()

# Create multiple audit events
events = [
    SecurityEvent(data="User login", success=True),
    DataAccessEvent(
        success=True,
        object_type="user_profile",
        object_id={"id": "123"},
        subject_type="user",
        subject_id={"id": "456"},
        subject_role="user",
        attributes=[DataAccessAttribute("email", successful=True)]
    )
]

# Log all events in a batch
failed_messages = client.log_batch(events)

# Handle any failed messages
for failed in failed_messages:
    print(f"Failed to log event: {failed.error}")
```

## Configuration

### Service Binding

- **Mount path**: `$SERVICE_BINDING_ROOT/auditlog/default/` (defaults to `/etc/secrets/appfnd/auditlog/default/`)
- **Required Keys**: `url` (Audit Log service URL), `uaa` (JSON string with XSUAA credentials)
- **Env var fallback**: `CLOUD_SDK_CFG_AUDITLOG_DEFAULT_{FIELD}` (uppercased)

> **Note:** `SERVICE_BINDING_ROOT` defaults to `/etc/secrets/appfnd` when not set. See the [Secret Resolver guide](../secret_resolver/user-guide.md) for details.

#### Mounted Secrets (Kubernetes)

```
$SERVICE_BINDING_ROOT/auditlog/default/
├── url
└── uaa
```

#### Environment Variables

```bash
export CLOUD_SDK_CFG_AUDITLOG_DEFAULT_URL="https://auditlog.example.com"
export CLOUD_SDK_CFG_AUDITLOG_DEFAULT_UAA='{"clientid":"...","clientsecret":"...","url":"https://..."}'
```

#### UAA JSON Schema

The `uaa` key must contain a JSON string with the XSUAA credentials:

```json
{
  "clientid": "sb-xxx",
  "clientsecret": "xxx",
  "url": "https://subdomain.authentication.region.hana.ondemand.com"
}
```
