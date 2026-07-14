"""Core secret resolver implementation."""

from __future__ import annotations
import os
from typing import Any

from sap_cloud_sdk.core.secret_resolver.mount_resolver import (
    resolve_base_mount,
    _load_from_mount,
)
from sap_cloud_sdk.core.secret_resolver.env_resolver import _load_from_env


def read_from_mount_and_fallback_to_env_var(
    base_volume_mount: str,
    base_var_name: str,
    module: str,
    instance: str,
    target: Any,
) -> None:
    """
    Load secrets for a given module and instance into the provided dataclass instance `target`.
    Fallback order:
      1. Mounted volume path: {base_volume_mount}/{module}/{instance}/{field_key}
         (``SERVICE_BINDING_ROOT`` env var overrides ``base_volume_mount`` — see
         :func:`resolve_base_mount`)
      2. Environment variables: {base_var_name}_{module}_{instance}_{field_key} (uppercased)

    Raises:
      ValueError: If inputs are invalid or target is not a dataclass instance
      FileNotFoundError / NotADirectoryError / OSError: If mount path issues occur
      KeyError: If environment variables are missing on fallback
      RuntimeError: If both mount and env var loading fail (aggregated error)
    """
    _validate_inputs(module, instance)

    resolved_base_path = resolve_base_mount(base_volume_mount)
    errors: list[str] = []
    normalized_module = module.replace("-", "_")
    normalized_instance = instance.replace("-", "_")

    try:
        _load_from_mount(resolved_base_path, module, instance, target)
        return
    except Exception as e:
        errors.append(f"mount failed: {e};")

    try:
        _load_from_env(base_var_name, normalized_module, normalized_instance, target)
        return
    except Exception as e:
        errors.append(f"env var failed: {e};")

    # Aggregate errors with actionable guidance for local dev and env fallback
    prefix_upper = f"{base_var_name}_{normalized_module}_{normalized_instance}".upper()
    mount_dir = os.path.join(resolved_base_path, module, instance) + "/"
    guidance_parts: list[str] = []
    guidance_parts.append("Secrets could not be loaded from mount or environment.")
    guidance_parts.append("Options:")
    guidance_parts.append(
        f"- Provide environment variables like {prefix_upper}_CLIENTID."
    )
    guidance_parts.append(
        f"- Alternatively, mount secrets under {mount_dir} with files for each required key."
    )
    guidance = " ".join(guidance_parts)
    raise RuntimeError(
        f"module={module} instance={instance} failed to read secrets: {errors} {guidance}"
    )


def _validate_inputs(module: str, instance: str) -> None:
    """Validate module and instance inputs."""
    if not isinstance(module, str) or not module.strip():
        raise ValueError("module name cannot be empty")
    if not isinstance(instance, str) or not instance.strip():
        raise ValueError("instance name cannot be empty")
