# Secret Resolver User Guide

This module provides secure credential management by loading secrets from mounted volumes (Kubernetes-style) with fallback to environment variables. It supports type-safe configuration using dataclasses and follows Cloud patterns for secret resolution.

The Secret Resolver is designed to work seamlessly in both Kubernetes environments with mounted secrets and with environment variables.

## Import

```python
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var
```

---

## Getting Started

The Secret Resolver loads configuration into dataclass objects using a hierarchical approach:

1. **First**: Try to read from mounted volume paths (Kubernetes secrets)
2. **Fallback**: Use environment variables if mounted secrets are not available

```python
from dataclasses import dataclass
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

@dataclass
class DatabaseConfig:
    host: str = ""
    port: str = ""
    username: str = ""
    password: str = ""

# Load configuration
config = DatabaseConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",      # Base mount path
    base_var_name="DB",               # Environment variable prefix  
    module="database",        # Module/service name
    instance="primary",       # Instance name
    target=config           # Target dataclass instance
)

print(f"Database: {config.username}@{config.host}:{config.port}")
```

---

## Configuration Patterns

### Mount Path Structure

The Secret Resolver expects mounted secrets to follow this hierarchy:

```
/etc/secrets/appfnd
└── <module_name>/
    └── <instance_name>/
        ├── host
        ├── port  
        ├── username
        └── password
```

Example for the above configuration:
```
/etc/secrets/appfnd
└── database/
    └── primary/
        ├── host          # Contains: "db.example.com"
        ├── port          # Contains: "5432"
        ├── username      # Contains: "app_user"
        └── password      # Contains: "secret123"
```

### Environment Variable Fallback

If mounted secrets are not available, the resolver falls back to environment variables using this pattern:

```
<ENV_PREFIX>_<MODULE_NAME>_<INSTANCE_NAME>_<FIELD_NAME>
```
-  INSTANCE_NAME has `'-'` replaced with `'_'` for compatibility with system environment variable naming rules.


For the example above:
```bash
export DB_DATABASE_PRIMARY_HOST="db.example.com"
export DB_DATABASE_PRIMARY_PORT="5432"
export DB_DATABASE_PRIMARY_USERNAME="app_user"
export DB_DATABASE_PRIMARY_PASSWORD="secret123"
```

---

## Usage Examples

### ObjectStore Configuration

This is how the ObjectStore module uses the Secret Resolver internally:

```python
from dataclasses import dataclass
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

@dataclass
class ObjectStoreConfig:
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    host: str = ""

# Load ObjectStore credentials
config = ObjectStoreConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="OBJECTSTORE", 
    module="objectstore",
    instance="credentials",
    target=config
)
```

**Mounted secrets structure:**
```
/etc/secrets/appfnd
└── objectstore/
    └── credentials/
        ├── access_key_id
        ├── secret_access_key
        ├── bucket
        └── host
```

**Environment variable fallback:**
```bash
export OBJECTSTORE_OBJECTSTORE_CREDENTIALS_ACCESS_KEY_ID="AKIA..."
export OBJECTSTORE_OBJECTSTORE_CREDENTIALS_SECRET_ACCESS_KEY="secret"
export OBJECTSTORE_OBJECTSTORE_CREDENTIALS_BUCKET="my-bucket"
export OBJECTSTORE_OBJECTSTORE_CREDENTIALS_HOST="s3.amazonaws.com"
```

### Database Configuration with Multiple Instances

```python
from dataclasses import dataclass
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

@dataclass
class DatabaseConfig:
    host: str = ""
    port: str = "5432"           # Default value
    database: str = ""
    username: str = ""
    password: str = ""
    ssl_mode: str = "require"    # Default value

# Load primary database config
primary_db = DatabaseConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="APP",
    module="database", 
    instance="primary",
    target=primary_db
)

# Load read replica config
replica_db = DatabaseConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="APP",
    module="database",
    instance="replica", 
    target=replica_db
)

print(f"Primary DB: {primary_db.username}@{primary_db.host}")
print(f"Replica DB: {replica_db.username}@{replica_db.host}")
```

### API Configuration

```python
from dataclasses import dataclass
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

@dataclass
class ApiConfig:
    base_url: str = ""
    api_key: str = ""
    timeout: str = "30"
    retries: str = "3"

# Load external API configuration
api_config = ApiConfig()
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="EXTERNAL",
    module="payment",
    instance="stripe",
    target=api_config
)

# Convert string values to appropriate types
timeout_seconds = int(api_config.timeout)
max_retries = int(api_config.retries)
```

---

## Error Handling

The Secret Resolver handles missing secrets gracefully by leaving default values unchanged:

```python
from dataclasses import dataclass
from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

@dataclass
class ServiceConfig:
    api_key: str = ""
    timeout: str = "30"     # Default value
    retries: str = "3"      # Default value
    debug: str = "false"    # Default value

config = ServiceConfig()

# This won't raise an error if secrets are missing
read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets",
    base_var_name="API",
    module="external",
    instance="service",
    target=config
)

# Check if required values were loaded
if not config.api_key:
    raise ValueError("API key is required but not found in secrets or environment")

print(f"Loaded config: timeout={config.timeout}, retries={config.retries}")
```

---
