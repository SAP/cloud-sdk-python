"""
Secret resolver: load configuration/secrets from mounted files or environment variables.

Built-in resolvers and chain builder::

    from sap_cloud_sdk.core.secret_resolver import (
        MountResolver,
        EnvVarResolver,
        ChainedResolver,
        BindingResolver,
    )

    # Build a chain explicitly
    resolver = ChainedResolver([MountResolver(), EnvVarResolver()])
    resolver.resolve("destination", "default", binding)

Legacy function-based API (still supported)::

    from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var

    read_from_mount_and_fallback_to_env_var(
        base_volume_mount="/etc/secrets/appfnd",
        base_var_name="CLOUD_SDK_CFG",
        module="destination",
        instance="default",
        target=binding,
    )
"""

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
    resolve_base_mount,
)
from sap_cloud_sdk.core.secret_resolver._resolvers import (
    Resolver,
    ChainedResolver,
    EnvVarResolver,
    MountResolver,
)
from sap_cloud_sdk.core.secret_resolver.sdk_config import (
    SdkConfig,
    configure,
    get_sdk_config,
    get_resolver,
    reset_sdk_config,
)

__all__ = [
    # Class-based API
    "Resolver",
    "MountResolver",
    "EnvVarResolver",
    "ChainedResolver",
    # Global configuration
    "SdkConfig",
    "configure",
    "get_sdk_config",
    "get_resolver",
    "reset_sdk_config",
    # Legacy function-based API
    "read_from_mount_and_fallback_to_env_var",
    "resolve_base_mount",
]
