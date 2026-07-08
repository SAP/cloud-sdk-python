import os
from typing import Any

from sap_cloud_sdk.core.secret_resolver._mapping import _get_field_map
from sap_cloud_sdk.core.secret_resolver.constants import (
    BASE_MOUNT_PATH,
    SERVICE_BINDING_ROOT,
)


class MountResolver:
    """Resolves bindings from a mounted volume path.

    Reads secret files at ``{base_volume_mount}/{module}/{instance}/{field_key}``.
    Respects the ``SERVICE_BINDING_ROOT`` environment variable (servicebinding.io
    spec) as an override for ``base_volume_mount``.

    Args:
        base_volume_mount: Base path for mounted secrets. Defaults to
            ``/etc/secrets/appfnd``.
    """

    def __init__(self, base_volume_mount: str = BASE_MOUNT_PATH) -> None:
        self._base_volume_mount = base_volume_mount

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Load secrets from the mounted volume path."""
        effective_base = resolve_base_mount(self._base_volume_mount)
        _load_from_mount(effective_base, module, instance, target)


def resolve_base_mount(base_volume_mount: str = BASE_MOUNT_PATH) -> str:
    """Resolve the base mount path for service binding discovery.

    Checks the ``SERVICE_BINDING_ROOT`` environment variable first (as defined
    by the `servicebinding.io <https://servicebinding.io/spec/core/1.1.0/>`_
    specification). Falls back to ``base_volume_mount`` when the env var is
    absent.

    Args:
        base_volume_mount: Default base path used when ``SERVICE_BINDING_ROOT``
            is not set. Defaults to ``/etc/secrets/appfnd``.

    Returns:
        The effective base path for secret mount resolution.
    """
    return os.environ.get(SERVICE_BINDING_ROOT, base_volume_mount)


def _load_from_mount(
    base_volume_mount: str, module: str, instance: str, target: Any
) -> None:
    """
    Load secrets from files at:
        {base_volume_mount}/{module}/{instance}/{field_key}

    Sets string attributes directly on the dataclass instance.
    """
    secret_dir = os.path.join(base_volume_mount, module, instance)
    _validate_path(secret_dir)

    field_map = _get_field_map(target)
    for key, (attr_name, _) in field_map.items():
        file_path = os.path.join(secret_dir, key)
        try:
            # Read entire file content as text; do not strip newlines to match Go behavior
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError as e:
            # Align with Go: surface precise file error
            raise FileNotFoundError(
                f"failed to read secret file {file_path}: {e}"
            ) from e
        except OSError as e:
            raise OSError(f"failed to read secret file {file_path}: {e}") from e

        # Set target field (string only)
        setattr(target, attr_name, content)


def _validate_path(path: str) -> None:
    """Validate that the given path exists and is a directory."""
    try:
        _st = os.stat(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"path does not exist: {path}") from e
    except OSError as e:
        raise OSError(f"cannot access path {path}: {e}") from e
    # If exists, ensure it's a directory
    if not os.path.isdir(path):
        raise NotADirectoryError(f"path is not a directory: {path}")
