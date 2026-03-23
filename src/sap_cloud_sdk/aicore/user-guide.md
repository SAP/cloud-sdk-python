# AI Core User Guide

This module provides utilities to configure SAP AI Core credentials for use with AI frameworks like LiteLLM. It automatically loads credentials from mounted secrets or environment variables and sets them up for seamless integration with AI Core services.

## Installation

The AI Core module is part of the Cloud SDK for Python and is automatically available when the SDK is installed.

## Import

```python
from sap_cloud_sdk.aicore import set_aicore_config
```

---

## Quick Start

### Basic Setup

Use `set_aicore_config()` to automatically load and configure AI Core credentials:

```python
from sap_cloud_sdk.aicore import set_aicore_config

# Load credentials and configure environment for AI Core
set_aicore_config()

# Now use LiteLLM with AI Core
from litellm import completion

response = completion(
    model="sap/gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Custom Instance

If you have multiple AI Core instances, specify the instance name:

```python
from sap_cloud_sdk.aicore import set_aicore_config

# Load credentials for a specific AI Core instance
set_aicore_config(instance_name="aicore-production")
```

---

## What It Does

The `set_aicore_config()` function:

1. **Loads credentials** from mounted secrets (Kubernetes) or environment variables
2. **Configures environment variables** for LiteLLM to use AI Core
3. **Normalizes URLs** by adding required suffixes (`/oauth/token` for auth, `/v2` for base URL)
4. **Sets resource group** (defaults to "default" if not specified)

### Credentials Loaded

The function loads and configures these credentials:

- **AICORE_CLIENT_ID** - OAuth2 client ID for authentication
- **AICORE_CLIENT_SECRET** - OAuth2 client secret
- **AICORE_AUTH_URL** - Authentication endpoint (auto-appends `/oauth/token` if needed)
- **AICORE_BASE_URL** - AI Core service base URL (auto-appends `/v2` if needed)
- **AICORE_RESOURCE_GROUP** - Resource group name (defaults to "default")

---

## Configuration

### Cloud Mode (Mounted Secrets)

In Kubernetes environments, secrets are automatically loaded from:

```
/etc/secrets/appfnd/aicore/{instance_name}/
├── clientid              # OAuth2 client ID
├── clientsecret          # OAuth2 client secret
├── url                   # Authentication server URL
└── serviceurls           # JSON file with AI_API_URL field
```

**serviceurls file format:**
```json
{
  "AI_API_URL": "https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com"
}
```

### Environment Variable Fallback

If mounted secrets are not available, the function falls back to environment variables:

```bash
# Authentication credentials
export AICORE_CLIENT_ID="your-client-id"
export AICORE_CLIENT_SECRET="your-client-secret"

# Service endpoints
export AICORE_AUTH_URL="https://your-subdomain.authentication.eu10.hana.ondemand.com/oauth/token"
export AICORE_BASE_URL="https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com/v2"

# Optional: Resource group (defaults to "default")
export AICORE_RESOURCE_GROUP="my-resource-group"
```

---

## Usage with LiteLLM

After calling `set_aicore_config()`, LiteLLM automatically uses the configured AI Core credentials:

```python
from sap_cloud_sdk.aicore import set_aicore_config
from litellm import completion

# Configure AI Core
set_aicore_config()

# Use AI Core models through LiteLLM
response = completion(
    model="sap/gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is SAP AI Core?"}
    ]
)

print(response.choices[0].message.content)
```

### Streaming Responses

```python
from sap_cloud_sdk.aicore import set_aicore_config
from litellm import completion

set_aicore_config()

response = completion(
    model="sap/gpt-4",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Using Different Models

```python
from sap_cloud_sdk.aicore import set_aicore_config
from litellm import completion, embedding

set_aicore_config()

# Chat completion
chat_response = completion(
    model="sap/gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Text embeddings
embedding_response = embedding(
    model="sap/text-embedding-ada-002",
    input=["Hello world", "How are you?"]
)
```

---

## Multiple AI Core Instances

If you have multiple AI Core instances (e.g., development, staging, production), specify the instance name:

```python
from sap_cloud_sdk.aicore import set_aicore_config

# Development environment
set_aicore_config(instance_name="aicore-dev")

# Production environment
set_aicore_config(instance_name="aicore-prod")
```

Each instance should have its own mounted secrets or environment variables.

---

## URL Normalization

The function automatically normalizes URLs to ensure compatibility:

### Authentication URL
- **Input**: `https://subdomain.authentication.region.hana.ondemand.com`
- **Output**: `https://subdomain.authentication.region.hana.ondemand.com/oauth/token`

### Base URL
- **Input**: `https://api.ai.prod.region.aws.ml.hana.ondemand.com`
- **Output**: `https://api.ai.prod.region.aws.ml.hana.ondemand.com/v2`

---

## Complete Example

```python
from sap_cloud_sdk.aicore import set_aicore_config
from litellm import completion
import logging

# Configure logging to see credential loading messages
logging.basicConfig(level=logging.INFO)

# Load and configure AI Core credentials
try:
    set_aicore_config(instance_name="aicore-instance")
    print("AI Core configuration successful")
except Exception as e:
    print(f"Failed to configure AI Core: {e}")
    exit(1)

# Use AI Core through LiteLLM
try:
    response = completion(
        model="sap/gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Explain SAP AI Core in one sentence."}
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"AI Core request failed: {e}")
```

---

## Logging

The module uses Python's standard logging to provide visibility into the credential loading process:

```python
import logging
from sap_cloud_sdk.aicore import set_aicore_config

# Enable INFO logging to see which credentials were loaded
logging.basicConfig(level=logging.INFO)

set_aicore_config()
# Logs will show:
# INFO:sap_cloud_sdk.aicore:Loaded AICORE_CLIENT_ID from file: /etc/secrets/appfnd/aicore/aicore-instance/clientid
# INFO:sap_cloud_sdk.aicore:Loaded AICORE_CLIENT_SECRET from file: /etc/secrets/appfnd/aicore/aicore-instance/clientsecret
# etc.
```

---

## Error Handling

Always handle potential configuration errors:

```python
from sap_cloud_sdk.aicore import set_aicore_config
import logging

logging.basicConfig(level=logging.WARNING)

try:
    set_aicore_config()
except Exception as e:
    logging.error(f"Failed to configure AI Core: {e}")
    # Handle the error appropriately
    # - Use default/fallback configuration
    # - Notify monitoring system
    # - Exit gracefully
```

---

## Best Practices

1. **Call once at startup**: Configure AI Core credentials once at application startup, before making any LiteLLM calls

2. **Use instance names**: When deploying to multiple environments, use descriptive instance names:
   ```python
   set_aicore_config(instance_name="aicore-prod")
   ```

3. **Enable logging**: Use logging to troubleshoot credential loading issues:
   ```python
   logging.basicConfig(level=logging.INFO)
   ```

4. **Handle errors gracefully**: Wrap configuration in try-except to handle missing credentials:
   ```python
   try:
       set_aicore_config()
   except Exception as e:
       # Fallback or exit
       pass
   ```

5. **Keep secrets secure**: Never hardcode credentials; always use mounted secrets or environment variables

---

## Troubleshooting

### Credentials Not Found

If you see warnings about missing credentials:

```
WARNING:sap_cloud_sdk.aicore:No value found for AICORE_CLIENT_ID, using default
```

**Solution**: Ensure either:
- Mounted secrets exist at `/etc/secrets/appfnd/aicore/{instance_name}/`
- Environment variables are set with the correct naming pattern

### Authentication Errors

If LiteLLM fails with authentication errors:

1. **Check credentials are loaded**: Enable INFO logging to verify credentials were found
2. **Verify URLs**: Ensure AICORE_AUTH_URL and AICORE_BASE_URL are correct
3. **Check resource group**: Verify AICORE_RESOURCE_GROUP matches your AI Core setup

### Wrong Instance

If credentials from the wrong instance are loaded:

```python
# Explicitly specify the correct instance name
set_aicore_config(instance_name="correct-instance-name")
```

---

## Integration with Telemetry

The AI Core configuration function includes built-in telemetry support using the SDK's telemetry module. All calls to `set_aicore_config()` are automatically tracked with metrics.

To enable telemetry tracking:

```python
from sap_cloud_sdk.core.telemetry import auto_instrument
from sap_cloud_sdk.aicore import set_aicore_config

# Enable auto-instrumentation
auto_instrument()

# Configuration calls are now tracked
set_aicore_config()
```

---

## Notes

- The `set_aicore_config()` function sets environment variables that persist for the lifetime of the Python process
- If you need to switch between multiple AI Core instances at runtime, call `set_aicore_config()` with different instance names
- The function is safe to call multiple times; subsequent calls will overwrite the environment variables
- Resource group defaults to "default" if not specified in secrets or environment variables