"""Provider auto-detection for the objectstore module (Design 1).

Enumerates the binding keys present in the configured secret mount or
environment variables to determine which cloud provider is backing a given
objectstore instance — without loading any values.

This logic lives in the objectstore module (not core) because it duplicates the
mount-path enumeration logic rather than extending it, keeping ``core`` unchanged.
"""

import os

from sap_cloud_sdk.core.secret_resolver import resolve_base_mount
from sap_cloud_sdk.objectstore._models import ObjectStoreProvider

# Discriminators (order matters: azure/gcs checked before s3 so the shared
# "bucket"/"region" keys in s3 and gcs are never used as discriminators).
_DISCRIMINATORS: dict[ObjectStoreProvider, set[str]] = {
    ObjectStoreProvider.AZURE: {"container_uri", "sas_token", "container_name"},
    ObjectStoreProvider.GCS: {
        "base64encodedprivatekeydata",
        "projectid",
    },  # lowercased for case-insensitive match
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
       lowercase the remaining key.

    Returns:
        Set of key names (always lowercased) present in any of the above sources.
    """
    keys: set[str] = set()
    resolved_base = resolve_base_mount(_DEFAULT_BASE_MOUNT)

    # Strategy 1: servicebinding.io flat path ($ROOT/objectstore/)
    if os.environ.get("SERVICE_BINDING_ROOT") is not None:
        flat_dir = os.path.join(resolved_base, "objectstore")
        keys.update(_scan_dir(flat_dir))

    # Strategy 2: legacy three-level path ($ROOT/objectstore/{instance}/)
    legacy_dir = os.path.join(resolved_base, "objectstore", instance)
    keys.update(_scan_dir(legacy_dir))

    # Strategy 3: environment variables
    prefix = f"CLOUD_SDK_CFG_OBJECTSTORE_{instance.upper().replace('-', '_')}_"
    for var in os.environ:
        if var.upper().startswith(prefix):
            key = var[len(prefix) :].lower()
            if key:
                keys.add(key)

    return keys


def _scan_dir(directory: str) -> set[str]:
    """Return lowercased file names in ``directory``, or an empty set if absent."""
    try:
        return {
            entry.name.lower() for entry in os.scandir(directory) if entry.is_file()
        }
    except (FileNotFoundError, NotADirectoryError, OSError):
        return set()


def detect_provider(keys: set[str]) -> ObjectStoreProvider:
    """Infer the cloud provider from a set of present binding keys.

    Checks azure, gcs, then s3 (in that order) to avoid misidentifying a GCS
    binding as S3 on the shared ``bucket``/``region`` keys.  All comparisons
    are case-insensitive (keys are expected to already be lowercased).

    Args:
        keys: Lowercased set of keys returned by ``read_binding_keys``.

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
        "gcs (base64EncodedPrivateKeyData, projectId)."
    )
