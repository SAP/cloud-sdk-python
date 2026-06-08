---
name: scaffold-module
description: Scaffold a new BTP service module for the SAP Cloud SDK for Python. Use when a contributor wants to add a new service integration and needs the standard directory layout, stubs, and telemetry wiring generated automatically.
tools: Bash, Read, Write, Edit
compatibility: uv, local cloud-sdk-python checkout (run from repo root)
---

# New Module Scaffold: SAP Cloud SDK for Python

Generates the full standard module layout with lint-clean stubs, wires telemetry, then runs a self-review pass on the generated files so you start from a clean baseline.

Run from the root of your `cloud-sdk-python` checkout.

---

## Phase 1: Collect Inputs

Ask the user for the following. Confirm before writing any files.

| Variable | What to ask | Example |
|----------|-------------|---------|
| `MODULE_NAME` | "Module directory name (snake_case)?" | `document_management` |
| `SERVICE_NAME` | "Full service display name?" | `Document Management Service` |
| `SHORT` | "Short prefix for class names (e.g. DMS, AGW)?" | `DMS` |
| `DESCRIPTION` | "One-sentence description of what this service does?" | `Provides document storage and retrieval on SAP BTP.` |

Derive automatically:
- `SHORT_LOWER` = `SHORT` lowercased (e.g., `dms`)
- `MODULE_UPPER` = `MODULE_NAME` uppercased (e.g., `DOCUMENT_MANAGEMENT`)

---

## Phase 2: Check for Existing Files

```bash
ls src/sap_cloud_sdk/<MODULE_NAME>/ 2>/dev/null && echo "EXISTS" || echo "OK"
ls tests/<MODULE_NAME>/ 2>/dev/null && echo "EXISTS" || echo "OK"
```

If either exists, warn and ask whether to overwrite before continuing.

---

## Phase 3: Generate Files

Write all files below, substituting all `<PLACEHOLDERS>`.

### `src/sap_cloud_sdk/<MODULE_NAME>/__init__.py`

```python
"""SAP Cloud SDK for Python - <SERVICE_NAME> module.

<DESCRIPTION>

Usage:
    from sap_cloud_sdk.<MODULE_NAME> import create_client

    client = create_client()
"""

from __future__ import annotations

import logging
from typing import Optional

from sap_cloud_sdk.<MODULE_NAME>.client import <SHORT>Client
from sap_cloud_sdk.<MODULE_NAME>.config import load_from_env_or_mount, <SHORT>Config
from sap_cloud_sdk.<MODULE_NAME>.exceptions import (
    <SHORT>Error,
    ClientCreationError,
    ConfigError,
    HttpError,
)

logger = logging.getLogger(__name__)


def create_client(
    *,
    instance: Optional[str] = None,
    config: Optional[<SHORT>Config] = None,
) -> <SHORT>Client:
    """Create a <SERVICE_NAME> client with automatic cloud configuration.

    Args:
        instance: Instance name for secret resolution. Defaults to "default".
        config: Optional explicit <SHORT>Config bypassing secret resolution.

    Returns:
        <SHORT>Client ready to use.

    Raises:
        ClientCreationError: If client creation fails.
    """
    try:
        binding = config or load_from_env_or_mount(instance)
        return <SHORT>Client(binding)
    except Exception as e:
        raise ClientCreationError(f"failed to create <SHORT_LOWER> client: {e}") from e


__all__ = [
    "create_client",
    "<SHORT>Client",
    "<SHORT>Config",
    "<SHORT>Error",
    "ClientCreationError",
    "ConfigError",
    "HttpError",
]
```

### `src/sap_cloud_sdk/<MODULE_NAME>/client.py`

```python
"""<SERVICE_NAME> client.

Do not instantiate directly: use create_client() from the module root.
"""

from __future__ import annotations

from sap_cloud_sdk.<MODULE_NAME>.config import <SHORT>Config


class <SHORT>Client:
    """Client for the SAP BTP <SERVICE_NAME>.

    Use :func:`sap_cloud_sdk.<MODULE_NAME>.create_client` instead of
    instantiating this class directly.
    """

    def __init__(self, config: <SHORT>Config) -> None:
        self._config = config

    # TODO: implement service methods. Add to imports when ready:
    #   from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
    # Then decorate each method:
    # @record_metrics(Module.<MODULE_UPPER>, Operation.<OPERATION_CONSTANT>)
    # def my_operation(self, ...) -> ...:
    #     ...
```

### `src/sap_cloud_sdk/<MODULE_NAME>/config.py`

```python
"""Configuration and secret resolution for <SERVICE_NAME>."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
)
from sap_cloud_sdk.<MODULE_NAME>.exceptions import ConfigError


@dataclass
class <SHORT>Config:
    """Service binding for <SERVICE_NAME>.

    Attributes:
        url: Service base URL.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        token_url: OAuth2 token endpoint URL.
    """

    url: str
    client_id: str
    client_secret: str
    token_url: str


@dataclass
class BindingData:
    """Raw binding fields read by the secret resolver."""

    url: str = ""
    clientid: str = ""
    clientsecret: str = ""

    def validate(self) -> None:
        """Validate that required fields are present."""
        if not self.url:
            raise ValueError("url is required")
        if not self.clientid:
            raise ValueError("clientid is required")
        if not self.clientsecret:
            raise ValueError("clientsecret is required")

    def to_config(self) -> <SHORT>Config:
        """Transform raw binding into a unified <SHORT>Config."""
        # TODO: BTP service bindings vary — check the actual binding schema.
        # Some services provide a separate UAA URL (e.g. binding["uaa"]["url"]);
        # others include it as a top-level "url" field. Do not derive token_url
        # from the service URL; read it from the binding instead.
        return <SHORT>Config(
            url=self.url,
            client_id=self.clientid,
            client_secret=self.clientsecret,
            token_url="",  # TODO: populate from the correct binding field
        )


def load_from_env_or_mount(instance: Optional[str] = None) -> <SHORT>Config:
    """Load <SERVICE_NAME> configuration from mount or environment variables.

    Mount path: /etc/secrets/appfnd/<MODULE_NAME>/{instance}/
    Env fallback: CLOUD_SDK_CFG_<MODULE_UPPER>_{INSTANCE}_{FIELD_KEY}

    Args:
        instance: Logical instance name. Defaults to "default".

    Returns:
        <SHORT>Config

    Raises:
        ConfigError: If loading or validation fails.
    """
    inst = instance or "default"
    binding = BindingData()

    try:
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="<MODULE_NAME>",
            instance=inst,
            target=binding,
        )
        binding.validate()
        return binding.to_config()
    except Exception as e:
        raise ConfigError(
            f"failed to load <MODULE_NAME> configuration for instance='{inst}': {e}"
        ) from e
```

### `src/sap_cloud_sdk/<MODULE_NAME>/exceptions.py`

```python
"""Exception classes for the <SERVICE_NAME> module."""


class <SHORT>Error(Exception):
    """Base exception for all <SERVICE_NAME> module errors."""


class ClientCreationError(<SHORT>Error):
    """Raised when client creation fails."""


class ConfigError(<SHORT>Error):
    """Raised when configuration or secret resolution fails."""


class HttpError(<SHORT>Error):
    """Raised for HTTP-related errors from <SERVICE_NAME>.

    Attributes:
        status_code: HTTP status code, if available.
        response_text: Raw response payload for diagnostics, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
```

### `src/sap_cloud_sdk/<MODULE_NAME>/_models.py`

```python
"""Pydantic models for <SERVICE_NAME> API requests and responses."""

from __future__ import annotations


# TODO: define Pydantic models for service API responses. Add to imports when ready:
#   from pydantic import BaseModel
# Example:
#
# class <SHORT>Item(BaseModel):
#     id: str
#     name: str
```

### `src/sap_cloud_sdk/<MODULE_NAME>/py.typed`

Empty file (PEP 561 marker).

### `src/sap_cloud_sdk/<MODULE_NAME>/user-guide.md`

```markdown
# <SERVICE_NAME>: User Guide

<DESCRIPTION>

## Prerequisites

Add the service binding to your `app.yaml`:

```yaml
requires:
  - name: my-<SHORT_LOWER>-instance
    service: <SHORT_LOWER>   # TODO: replace with the actual BTP service name
    plan: standard
```

## Installation

```bash
uv add sap-cloud-sdk
```

## Quick Start

```python
from sap_cloud_sdk.<MODULE_NAME> import create_client

client = create_client()

# TODO: add the most common usage example
```

## Configuration

Credentials are resolved automatically from:
- **Cloud (mounted secret)**: `/etc/secrets/appfnd/<MODULE_NAME>/{instance}/`
- **Env fallback**: `CLOUD_SDK_CFG_<MODULE_UPPER>_{INSTANCE}_{FIELD}`

To target a specific binding instance:
```python
client = create_client(instance="my-<SHORT_LOWER>-instance")
```

## API Reference

### `create_client(*, instance=None, config=None) → <SHORT>Client`

Creates and returns a configured `<SHORT>Client`.

<!-- TODO: document each public client method -->

## Error Handling

```python
from sap_cloud_sdk.<MODULE_NAME>.exceptions import <SHORT>Error, ConfigError, HttpError

try:
    result = client.my_operation()
except HttpError as e:
    print(f"HTTP {e.status_code}: {e}")
except ConfigError as e:
    print(f"Config error: {e}")
except <SHORT>Error as e:
    print(f"<SHORT_LOWER> error: {e}")
```
```

### `tests/<MODULE_NAME>/__init__.py`

Empty file.

### `tests/<MODULE_NAME>/unit/__init__.py`

Empty file.

### `tests/<MODULE_NAME>/unit/test_client.py`

```python
"""Unit tests for <SHORT>Client."""

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.<MODULE_NAME> import create_client
from sap_cloud_sdk.<MODULE_NAME>.client import <SHORT>Client
from sap_cloud_sdk.<MODULE_NAME>.config import <SHORT>Config


@pytest.fixture
def mock_config() -> <SHORT>Config:
    return <SHORT>Config(
        url="https://example.ondemand.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
        token_url="https://example.authentication.eu10.hana.ondemand.com/oauth/token",
    )


def test_create_client_returns_client(mock_config: <SHORT>Config) -> None:
    client = create_client(config=mock_config)
    assert isinstance(client, <SHORT>Client)


# TODO: add tests following test_<functionality>_<condition>_<expected_result>
```

---

## Phase 4: Update Telemetry Module Registry

Read `src/sap_cloud_sdk/core/telemetry/module.py` and insert the new entry into the `Module` enum in **alphabetical order by key**:

```python
<MODULE_UPPER> = "<MODULE_NAME>"
```

---

## Phase 5: Self-Review

Check the generated files against these criteria. Fix any issues found before reporting to the user.

**E3: Module structure**: verify all required files exist:
- `__init__.py`, `client.py`, `config.py`, `exceptions.py`, `_models.py`, `py.typed`, `user-guide.md`
- `tests/<MODULE_NAME>/unit/__init__.py`, `tests/<MODULE_NAME>/unit/test_client.py`

**D5: Telemetry**: verify `Module.<MODULE_UPPER>` was added to `core/telemetry/module.py` in alphabetical order.

**C3: Type hints**: verify all public functions and the `__init__` method in `client.py` have full type annotations.

**C6: Naming**: verify class names use the `<SHORT>` prefix consistently, private internal fields use `_` prefix.

**D2: Public API hygiene**: verify `__all__` in `__init__.py` contains exactly the public symbols and nothing internal.

Run the full local quality gate on the generated files:
```bash
uv run ruff check src/sap_cloud_sdk/<MODULE_NAME>/
uv run ruff format --check src/sap_cloud_sdk/<MODULE_NAME>/
uv run ty check src/sap_cloud_sdk/<MODULE_NAME>/
uv run pytest tests/<MODULE_NAME>/ -v
```

Fix any reported issues before proceeding.

---

## Phase 6: Report

```
✅ Generated files:
   src/sap_cloud_sdk/<MODULE_NAME>/__init__.py
   src/sap_cloud_sdk/<MODULE_NAME>/client.py
   src/sap_cloud_sdk/<MODULE_NAME>/config.py
   src/sap_cloud_sdk/<MODULE_NAME>/exceptions.py
   src/sap_cloud_sdk/<MODULE_NAME>/_models.py
   src/sap_cloud_sdk/<MODULE_NAME>/py.typed
   src/sap_cloud_sdk/<MODULE_NAME>/user-guide.md
   tests/<MODULE_NAME>/__init__.py
   tests/<MODULE_NAME>/unit/__init__.py
   tests/<MODULE_NAME>/unit/test_client.py
✅ Added Module.<MODULE_UPPER> to core/telemetry/module.py
✅ Self-review passed (or: fixed N issues)

📋 Your remaining steps:
  1. Add operation constants  → src/sap_cloud_sdk/core/telemetry/operation.py
  2. Implement client methods → src/sap_cloud_sdk/<MODULE_NAME>/client.py
     Each method needs: @record_metrics(Module.<MODULE_UPPER>, Operation.<YOUR_OP>)
  3. Define response models   → src/sap_cloud_sdk/<MODULE_NAME>/_models.py
  4. Add service binding to app.yaml (check BTP catalog for exact service name)
  5. Bump version in pyproject.toml (CI will block without this)
  6. Run full checks:
       uv run pytest tests/<MODULE_NAME>/ -v
       uv run ty check src/sap_cloud_sdk/<MODULE_NAME>/
```
