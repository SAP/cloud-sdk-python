"""Provider auto-detection for the objectstore module.

Enumerates the binding keys present in the configured secret mount or
environment variables to determine which cloud provider is backing a given
objectstore instance.
"""

import os

from sap_cloud_sdk.core.secret_resolver import resolve_base_mount
from sap_cloud_sdk.objectstore._models import ObjectStoreProvider

_DISCRIMINATORS: dict[ObjectStoreProvider, set[str]] = {
    ObjectStoreProvider.AZURE: {"container_uri", "sas_token", "container_name"},
    ObjectStoreProvider.GCS: {
        "base64encodedprivatekeydata",
        "projectid",
    },
    ObjectStoreProvider.S3: {"access_key_id", "secret_access_key", "host"},
}

_DEFAULT_BASE_MOUNT = "/etc/secrets/appfnd"


def read_binding_keys(instance: str) -> set[str]:
    """Enumerate present binding keys from mount (flat + legacy layouts) then env.

    Mirrors the three lookup strategies of ``read_from_mount_and_fallback_to_env_var``:

    1. If ``SERVICE_BINDING_ROOT`` is set → flat path
       ``$ROOT/objectstore/`` (servicebinding.io spec).
    2. Legacy path ``{base}/objectstore/{instance}/`` (always tried; falls back
       from the flat attempt if SERVICE_BINDING_ROOT is set).
    3. Env-var prefix
       ``CLOUD_SDK_CFG_OBJECTSTORE_{instance_upper}_`` → strip the prefix,
       return the remaining key as-is.

    Returns:
        Set of key names present in any of the above sources.
    """
    keys: set[str] = set()
    resolved_base = resolve_base_mount(_DEFAULT_BASE_MOUNT)

    # servicebinding.io flat path ($ROOT/objectstore/)
    if os.environ.get("SERVICE_BINDING_ROOT") is not None:
        flat_dir = os.path.join(resolved_base, "objectstore")
        keys.update(_scan_dir(flat_dir))

    # Three-level path ($ROOT/objectstore/{instance}/)
    legacy_dir = os.path.join(resolved_base, "objectstore", instance)
    keys.update(_scan_dir(legacy_dir))

    # Environment variables
    prefix = f"CLOUD_SDK_CFG_OBJECTSTORE_{instance.upper().replace('-', '_')}_"
    for var in os.environ:
        if var.upper().startswith(prefix):
            key = var[len(prefix) :]
            if key:
                keys.add(key)

    return keys


def _scan_dir(directory: str) -> set[str]:
    """Return file names in ``directory``, or an empty set if absent."""
    try:
        return {entry.name for entry in os.scandir(directory) if entry.is_file()}
    except (FileNotFoundError, NotADirectoryError, OSError):
        return set()


def detect_provider(keys: set[str]) -> ObjectStoreProvider:
    """Infer the cloud provider from a set of present binding keys.

    Args:
        keys: Set of keys returned by ``read_binding_keys``.

    Returns:
        Detected object store provider.

    Raises:
        ValueError: If no provider can be identified from the available keys.
    """
    lowered = {k.lower() for k in keys}
    if _DISCRIMINATORS[ObjectStoreProvider.AZURE].issubset(lowered):
        return ObjectStoreProvider.AZURE
    if _DISCRIMINATORS[ObjectStoreProvider.GCS].issubset(lowered):
        return ObjectStoreProvider.GCS
    if _DISCRIMINATORS[ObjectStoreProvider.S3].issubset(lowered):
        return ObjectStoreProvider.S3

    raise ValueError(
        f"Cannot detect objectstore provider from keys: {sorted(lowered)}. "
        "Expected one of: s3 (access_key_id, secret_access_key, host), "
        "azure (container_uri, sas_token, container_name), "
        "gcs (base64encodedprivatekeydata, projectid)."
    )
