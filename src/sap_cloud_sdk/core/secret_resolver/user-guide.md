# Secret Resolver — User Guide

The `secret_resolver` module loads service-binding credentials (secrets) into
dataclass instances from two sources: **mounted volume files** and **environment
variables**. Resolvers are composable and the default chain can be replaced
process-wide for custom environments (e.g. Cloud Foundry VCAP).

---

## Concepts

### Target dataclass

All resolvers populate a **dataclass instance** whose fields are all `str`.
Each field maps to one secret key. By default the key is the lowercase field
name; you can override it with `field(metadata={"secret": "custom-key"})`.

```python
from dataclasses import dataclass, field

@dataclass
class DestinationBinding:
    clientid: str = ""
    clientsecret: str = ""
    url: str = ""
    # Override the lookup key to "token_service_url"
    token_url: str = field(default="", metadata={"secret": "token_service_url"})
```

### module / instance

Every resolver call takes a `module` (service category, e.g. `"destination"`)
and an `instance` (service instance name, e.g. `"default"`). These are used to
build the lookup path or variable name prefix. Hyphens in both are normalised
to underscores where required.

---

## Resolver types

### `MountResolver`

Reads secret files at:

```
{base_volume_mount}/{module}/{instance}/{field_key}
```


```python
from sap_cloud_sdk.core.secret_resolver import MountResolver

resolver = MountResolver()                          # defaults to /etc/secrets/appfnd
resolver = MountResolver("/custom/mount/path")      # explicit base path
```

### `EnvVarResolver`

Reads environment variables named:

```
{BASE_VAR_NAME}_{MODULE}_{INSTANCE}_{FIELD_KEY}   (all uppercased)
```

Example: `CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID`

```python
from sap_cloud_sdk.core.secret_resolver import EnvVarResolver

resolver = EnvVarResolver()                         # base prefix: CLOUD_SDK_CFG
resolver = EnvVarResolver("MY_APP_SECRETS")         # custom prefix
```

### `ChainedResolver`

Tries each resolver in order and returns on the first success. Raises
`RuntimeError` with an aggregated report when all resolvers fail.

```python
from sap_cloud_sdk.core.secret_resolver import ChainedResolver, MountResolver, EnvVarResolver

resolver = ChainedResolver([MountResolver(), EnvVarResolver()])
resolver.resolve("destination", "default", binding)
```

### Custom resolver

Any object with a `resolve(module, instance, target)` method satisfies the
`Resolver` protocol — no inheritance needed.

```python
class VaultResolver:
    def resolve(self, module: str, instance: str, target: object) -> None:
        # fetch from HashiCorp Vault, populate target fields
        ...
```

---

## Process-wide configuration

Call `configure()` once at application startup to install a custom resolver
chain. All `create_client()` calls across every module will use it.

```python
from sap_cloud_sdk.core.secret_resolver import configure, SdkConfig, ChainedResolver, EnvVarResolver

configure(SdkConfig(
    resolver=ChainedResolver([VaultResolver(), EnvVarResolver()])
))
```

If `configure()` is never called, each module falls back to the default chain:
`ChainedResolver([MountResolver(), EnvVarResolver()])`.

### Configuration API

| Function | Description |
|---|---|
| `configure(config)` | Install a process-wide `SdkConfig`. Thread-safe. |
| `get_sdk_config()` | Return the current `SdkConfig`, or `None` if unset. |
| `get_resolver()` | Return the active resolver (custom or default chain). |
| `reset_sdk_config()` | Reset to unset state. Intended for test teardown only. |

---

## Putting it together

```python
from dataclasses import dataclass, field
from sap_cloud_sdk.core.secret_resolver import ChainedResolver, MountResolver, EnvVarResolver

@dataclass
class DestinationBinding:
    clientid: str = ""
    clientsecret: str = ""
    url: str = ""

binding = DestinationBinding()

resolver = ChainedResolver([MountResolver(), EnvVarResolver()])
resolver.resolve("destination", "my-instance", binding)

print(binding.clientid)
```

---

## Legacy API

The function-based API from earlier SDK versions is still supported:

```python
from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var

read_from_mount_and_fallback_to_env_var(
    base_volume_mount="/etc/secrets/appfnd",
    base_var_name="CLOUD_SDK_CFG",
    module="destination",
    instance="default",
    target=binding,
)
```

Prefer the class-based API for new code — it is more composable and supports
process-wide configuration.

---

## Error handling

| Situation | Exception raised |
|---|---|
| Target is not a dataclass instance | `TypeError` |
| A target field is not `str` | `TypeError` |
| Mount directory does not exist | `FileNotFoundError` |
| Mount path is not a directory | `NotADirectoryError` |
| Expected env var is absent | `KeyError` |
| All resolvers in a chain fail | `RuntimeError` (aggregated message with guidance) |
