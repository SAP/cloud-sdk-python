"""SAP Cloud SDK for Python - Destination module

The create_client() function loads credentials from mounts/env vars and points to an instance in the cloud

Usage:
    from cloud_sdk_python.destination import create_client, Level, AccessStrategy
    from cloud_sdk_python.destination._models import Destination

    # Recommended: use the factory which configures OAuth/HTTP from environment
    client = create_client()

    # Read an instance-level destination
    dest = client.get_instance_destination("my-destination")

    # Read a subaccount-level destination using subscriber-first strategy
    dest = client.get_subaccount_destination(
        name="my-destination",
        access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
        tenant="tenant-subdomain"
    )
"""

from __future__ import annotations

from typing import Optional

from cloud_sdk_python.destination._models import (
    Destination,
    AuthToken,
    ConsumptionOptions,
    Fragment,
    Certificate,
    Level,
    AccessStrategy,
    ListOptions,
    TransparentProxy,
    TransparentProxyDestination,
    TransparentProxyHeader
)
from cloud_sdk_python.destination.utils._pagination import (
    PaginationInfo,
    PagedResult,
)
from cloud_sdk_python.destination.config import load_from_env_or_mount, DestinationConfig
from cloud_sdk_python.destination._http import TokenProvider, DestinationHttp
from cloud_sdk_python.destination.client import DestinationClient
from cloud_sdk_python.destination.fragment_client import FragmentClient
from cloud_sdk_python.destination.certificate_client import CertificateClient
from cloud_sdk_python.destination.exceptions import (
    DestinationError,
    ClientCreationError,
    ConfigError,
    HttpError,
    DestinationOperationError,
    DestinationNotFoundError,
)


def create_client(
        *,
        instance: Optional[str] = None,
        config: Optional[DestinationConfig] = None,
        use_default_proxy: bool = False,
):
    """Creates a Destination client with local/cloud detection.

    Behavior:
      - If config is provided, use HTTP mode with the given DestinationConfig
      - Else if RuntimeContext().is_local("destination"), return LocalDevDestinationProvider-based client
      - Else, resolve secrets via config.load_from_env_or_mount(instance) and return HTTP client

    Args:
        instance: Instance name used for secret resolution in cloud mode. Defaults to "default".
        config: Optional explicit DestinationConfig.
        use_default_proxy: Whether to use the default transparent proxy for all get operations. When True,
                          will attempt to load transparent proxy configuration from APPFND_CONHOS_TRANSP_PROXY
                          environment variable. To use a custom proxy, use client.set_proxy() after creation.
                          Defaults to False.

    Returns:
        DestinationClient or LocalDevDestinationProvider: Client implementing the Destination interface.

    Raises:
        ClientCreationError: If client creation fails due to configuration or initialization issues.
    """
    try:
        # Cloud mode via secret resolver or explicit config
        binding = config or load_from_env_or_mount(instance)
        tp = TokenProvider(binding)
        http = DestinationHttp(config=binding, token_provider=tp)

        return DestinationClient(http, use_default_proxy)

    except Exception as e:
        raise ClientCreationError(f"failed to create destination client: {e}")


def create_fragment_client(
        *,
        instance: Optional[str] = None,
        config: Optional[DestinationConfig] = None,
):
    """Creates a Fragment client with local/cloud detection.

    Behavior:
      - If config is provided, use HTTP mode with the given DestinationConfig
      - Else if RuntimeContext().is_local("destination"), return LocalDevFragmentClient
      - Else, resolve secrets via config.load_from_env_or_mount(instance) and return HTTP client

    Args:
        instance: Instance name used for secret resolution in cloud mode. Defaults to "default".
        config: Optional explicit DestinationConfig.

    Returns:
        FragmentClient or LocalDevFragmentClient: Client for managing destination fragments.

    Raises:
        ClientCreationError: If client creation fails due to configuration or initialization issues.
    """
    try:
        # Use provided config or load from environment/mount (cloud mode)
        binding = config or load_from_env_or_mount(instance)
        tp = TokenProvider(binding)
        http = DestinationHttp(config=binding, token_provider=tp)

        return FragmentClient(http)

    except Exception as e:
        raise ClientCreationError(f"failed to create fragment client: {e}")


def create_certificate_client(
        *,
        instance: Optional[str] = None,
        config: Optional[DestinationConfig] = None,
):
    """Creates a Certificate client with local/cloud detection.

    Behavior:
      - If config is provided, use HTTP mode with the given DestinationConfig
      - Else if RuntimeContext().is_local("destination"), return LocalDevCertificateClient
      - Else, resolve secrets via config.load_from_env_or_mount(instance) and return HTTP client

    Args:
        instance: Instance name used for secret resolution in cloud mode. Defaults to "default".
        config: Optional explicit DestinationConfig.

    Returns:
        CertificateClient or LocalDevCertificateClient: Client for managing certificates.

    Raises:
        ClientCreationError: If client creation fails due to configuration or initialization issues.
    """
    try:
        # Use provided config or load from environment/mount (cloud mode)
        binding = config or load_from_env_or_mount(instance)
        tp = TokenProvider(binding)
        http = DestinationHttp(config=binding, token_provider=tp)

        return CertificateClient(http)

    except Exception as e:
        raise ClientCreationError(f"failed to create certificate client: {e}")


__all__ = [
    # Public types
    "Destination",
    "AuthToken",
    "ConsumptionOptions",
    "Fragment",
    "Certificate",
    "DestinationConfig",
    "Level",
    "AccessStrategy",
    "ListOptions",
    "TransparentProxy",
    "TransparentProxyDestination",
    "TransparentProxyHeader",
    "PaginationInfo",
    "PagedResult",
    # Factory functions
    "create_client",
    "create_fragment_client",
    "create_certificate_client",
    # Client classes
    "DestinationClient",
    "FragmentClient",
    "CertificateClient",
    "LocalDevDestinationClient",
    "LocalDevFragmentClient",
    "LocalDevCertificateClient",
    # Exceptions
    "DestinationError",
    "ClientCreationError",
    "ConfigError",
    "HttpError",
    "DestinationOperationError",
    "DestinationNotFoundError",
]
