"""Process-wide SDK configuration.

Provides :class:`SdkConfig` and :func:`configure` so an application can set a
custom binding resolver chain once at startup, and every ``create_client()`` call
across all modules will use it automatically.

Usage::

    from sap_cloud_sdk.core.secret_resolver import (
        configure, SdkConfig, ChainedResolver, EnvVarResolver,
    )
    from sap_cloud_sdk.core.secrets_resolver_extended import VcapResolver

    # Cloud Foundry: VCAP first, env vars as fallback
    configure(SdkConfig(
        resolver=ChainedResolver([VcapResolver(), EnvVarResolver()])
    ))

If no configuration is set, all modules fall back to the default chain:
``ChainedResolver([MountResolver(), EnvVarResolver()])``, which is identical
to the previous ``read_from_mount_and_fallback_to_env_var()`` behaviour.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from sap_cloud_sdk.core.secret_resolver._resolvers import (
    Resolver,
    ChainedResolver,
    EnvVarResolver,
    MountResolver,
)

_lock = threading.Lock()
_sdk_config: Optional[SdkConfig] = None


@dataclass
class SdkConfig:
    """Process-wide SDK configuration.

    Attributes:
        resolver: The :class:`BindingResolver` that all ``create_client()`` calls
            use when no explicit config is passed. ``None`` means each module uses
            the default ``ChainedResolver([MountResolver(), EnvVarResolver()])`` chain.
    """

    resolver: Optional[Resolver] = None


def configure(config: SdkConfig) -> None:
    """Set the process-wide SDK configuration.

    Thread-safe. Replaces any previously set configuration. Call once at
    application startup before any ``create_client()`` is invoked.

    Args:
        config: :class:`SdkConfig` instance to install.
    """
    global _sdk_config
    with _lock:
        _sdk_config = config


def get_sdk_config() -> Optional[SdkConfig]:
    """Return the current process-wide SDK configuration, or ``None`` if unset."""
    return _sdk_config


def reset_sdk_config() -> None:
    """Reset the global configuration to the unset state.

    Intended for test teardown only. Not part of the public API.
    """
    global _sdk_config
    with _lock:
        _sdk_config = None


def get_resolver() -> Resolver:
    """Return the resolver all modules should use for binding resolution.

    Returns the custom resolver set via :func:`configure` if one has been
    installed; otherwise returns a fresh default
    ``ChainedResolver([MountResolver(), EnvVarResolver()])``.
    """
    cfg = get_sdk_config()
    if cfg is not None and cfg.resolver is not None:
        return cfg.resolver
    return ChainedResolver([MountResolver(), EnvVarResolver()])
