"""Object store client factory — provider detection and dispatch."""

from typing import Callable, Union, cast

from sap_cloud_sdk.core.secret_resolver import ConfigFactory
from sap_cloud_sdk.object_storage._azure import AzureClient
from sap_cloud_sdk.object_storage._detect import detect_provider, read_binding_keys
from sap_cloud_sdk.object_storage._gcs import GcsClient
from sap_cloud_sdk.object_storage._models import ObjectStoreProvider
from sap_cloud_sdk.object_storage._protocol import ObjectStoreClient
from sap_cloud_sdk.object_storage._s3 import S3Client
from sap_cloud_sdk.object_storage.config import (
    AzureConfig,
    GcsConfig,
    S3Config,
    _BINDING_TYPES,
)
from sap_cloud_sdk.object_storage.exceptions import ClientCreationError, ConfigError

_ProviderConfig = Union[S3Config, AzureConfig, GcsConfig]


def _make_static_factory(config: _ProviderConfig) -> Callable[[], _ProviderConfig]:
    """Wrap a fixed config in a no-op factory (no rotation tracking)."""

    def _factory() -> _ProviderConfig:
        return config

    return _factory


def create_client(
    *,
    instance: str | None = None,
    config: Union[S3Config, AzureConfig, GcsConfig, None] = None,
) -> ObjectStoreClient:
    """Create an object store client with automatic provider detection.

    When ``config`` is omitted the function reads the service binding for
    ``instance`` from the secret mount or environment variables, infers the
    cloud provider, and returns the matching concrete client.

    Args:
        instance: Instance name used for secret resolution. Defaults to
            ``"default"`` and is ignored when ``config`` is provided.
        config: Optional explicit client configuration. If provided,
            auto-detection is skipped, this configuration is used directly, and
            rotation tracking is disabled.

    Returns:
        A client satisfying the ``ObjectStoreClient`` protocol.

    Raises:
        ConfigError: If the binding cannot be loaded or is missing required fields.
        ClientCreationError: If no provider can be detected or client creation fails.
    """
    if config is not None:
        factory: Callable[[], _ProviderConfig] = _make_static_factory(config)
        provider = _provider_for_config(config)
    else:
        resolved_instance = instance or "default"
        keys = read_binding_keys(resolved_instance)
        try:
            provider = detect_provider(keys)
        except ValueError as e:
            raise ClientCreationError(
                "Cannot create objectstore client for instance "
                f"'{resolved_instance}': {e}"
            ) from e
        binding_cls = _BINDING_TYPES[provider]
        factory = ConfigFactory(
            module="objectstore",
            instance=resolved_instance,
            binding_cls=binding_cls,
            extract=lambda b: b.to_config(),
        )

    try:
        if provider is ObjectStoreProvider.S3:
            return S3Client(cast(Callable[[], S3Config], factory))
        if provider is ObjectStoreProvider.AZURE:
            return AzureClient(cast(Callable[[], AzureConfig], factory))
        if provider is ObjectStoreProvider.GCS:
            return GcsClient(cast(Callable[[], GcsConfig], factory))
    except (ConfigError, ClientCreationError):
        raise
    except Exception as e:
        raise ConfigError(
            f"failed to load objectstore configuration for instance '{instance}': {e}"
        ) from e
    raise ClientCreationError(f"Unsupported provider: {provider}")


def _provider_for_config(config: _ProviderConfig) -> ObjectStoreProvider:
    """Map an explicit config instance to its provider."""
    if isinstance(config, S3Config):
        return ObjectStoreProvider.S3
    if isinstance(config, AzureConfig):
        return ObjectStoreProvider.AZURE
    if isinstance(config, GcsConfig):
        return ObjectStoreProvider.GCS
    raise ClientCreationError(f"Unsupported config type: {type(config).__name__}")
