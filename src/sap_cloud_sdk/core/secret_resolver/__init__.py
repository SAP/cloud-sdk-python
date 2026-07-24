"""
Secret resolver: load configuration/secrets from mounted files or environment variables.

Built-in resolvers and chain builder::

    from sap_cloud_sdk.core.secret_resolver import (
        MountResolver,
        EnvVarResolver,
        ChainedResolver,
    )

    # Build a chain explicitly
    resolver = ChainedResolver([MountResolver(), EnvVarResolver()])
    resolver.resolve("destination", "default", binding)
"""

from sap_cloud_sdk.core.secret_resolver._resolvers import (
    Resolver,
    ChainedResolver,
)

from sap_cloud_sdk.core.secret_resolver.mount_resolver import (
    MountResolver,
)
from sap_cloud_sdk.core.secret_resolver.sdk_env_resolver import SdkEnvVarResolver

from sap_cloud_sdk.core.secret_resolver.sdk_config import (
    SdkConfig,
    configure,
    get,
    get_resolver,
)

__all__ = [
    # Class-based API
    "Resolver",
    "MountResolver",
    "SdkEnvVarResolver",
    "ChainedResolver",
    # Global configuration
    "SdkConfig",
    "configure",
    "get",
    "get_resolver",
]
