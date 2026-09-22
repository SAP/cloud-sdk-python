"""Provider auto-detection for the objectstore module.

Enumerates the binding keys present in the configured secret mount or
environment variables to determine which cloud provider is backing a given
objectstore instance.
"""

import os

from sap_cloud_sdk.core.secret_resolver import resolve_base_mount
from sap_cloud_sdk.object_storage._models import ObjectStoreProvider

_SIGNATURES: dict[ObjectStoreProvider, set[str]] = {
    ObjectStoreProvider.AZURE: {"container_uri", "sas_token", "container_name"},
    ObjectStoreProvider.GCS: {
        "base64EncodedPrivateKeyData",
        "projectId",
        "bucket",
    },
    ObjectStoreProvider.S3: {
        "access_key_id",
        "secret_access_key",
        "bucket",
        "host",
    },
}

_DEFAULT_BASE_MOUNT = "/etc/secrets/appfnd"


def read_binding_keys(instance: str) -> set[str]:
    """Enumerate keys from the first source with a complete provider signature.

    Sources are consulted in the same precedence order the credential loader
    uses (flat mount → legacy mount → env).

    Returns:
        Keys from the first source containing a complete provider signature.
        If none is complete, returns keys from the first non-empty source.
        Returns an empty set only when every source is empty.
    """
    resolved_base = resolve_base_mount(_DEFAULT_BASE_MOUNT)
    sources: list[set[str]] = []

    if os.environ.get("SERVICE_BINDING_ROOT") is not None:
        sources.append(_scan_dir(os.path.join(resolved_base, "objectstore")))

    sources.append(_scan_dir(os.path.join(resolved_base, "objectstore", instance)))

    prefix = f"CLOUD_SDK_CFG_OBJECTSTORE_{instance.upper().replace('-', '_')}_"
    sources.append(
        {
            var[len(prefix) :]
            for var in os.environ
            if var.upper().startswith(prefix) and var[len(prefix) :]
        }
    )

    first_non_empty: set[str] = set()
    for keys in sources:
        if keys and not first_non_empty:
            first_non_empty = keys
        if _matching_providers(keys):
            return keys

    return first_non_empty


def _scan_dir(directory: str) -> set[str]:
    """Return file names in ``directory``, or an empty set if absent."""
    try:
        return {entry.name for entry in os.scandir(directory) if entry.is_file()}
    except (FileNotFoundError, NotADirectoryError, OSError):
        return set()


def _matching_providers(keys: set[str]) -> list[ObjectStoreProvider]:
    """Return providers whose complete binding signature is present."""
    lowered = {key.lower() for key in keys}
    return [
        provider
        for provider, signature in _SIGNATURES.items()
        if {key.lower() for key in signature}.issubset(lowered)
    ]


def detect_provider(keys: set[str]) -> ObjectStoreProvider:
    """Infer the cloud provider from a set of present binding keys.

    Args:
        keys: Set of keys returned by ``read_binding_keys``.

    Returns:
        Detected object store provider.

    Raises:
        ValueError: If the keys identify no provider, or match more than one.
    """
    lowered = {k.lower() for k in keys}

    matched = _matching_providers(keys)

    if len(matched) == 1:
        return matched[0]

    if matched:
        names = ", ".join(sorted(p.value for p in matched))
        raise ValueError(
            f"binding keys {sorted(lowered)} match multiple providers ({names}); "
            "a single objectstore binding must belong to exactly one provider."
        )

    raise ValueError(
        f"Cannot detect objectstore provider from keys: {sorted(lowered)}. "
        "Expected one of: s3 (access_key_id, secret_access_key, bucket, host), "
        "azure (container_uri, sas_token, container_name), "
        "gcs (base64EncodedPrivateKeyData, projectId, bucket)."
    )
