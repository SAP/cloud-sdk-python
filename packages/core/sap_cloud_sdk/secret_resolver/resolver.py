"""Core secret resolver implementation."""

from __future__ import annotations

import os
from dataclasses import fields, is_dataclass
from typing import Any, Dict, Tuple


def _validate_inputs(module: str, instance: str) -> None:
    """Validate module and instance inputs."""
    if not isinstance(module, str) or not module.strip():
        raise ValueError("module name cannot be empty")
    if not isinstance(instance, str) or not instance.strip():
        raise ValueError("instance name cannot be empty")


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


def _get_field_map(target: Any) -> Dict[str, Tuple[str, type]]:
    """
    Build a mapping from secret key -> (attribute_name, attribute_type) for a dataclass instance.

    Priority:
      1. Use field.metadata["secret"] if present as the key
      2. Fallback to the lowercase dataclass field name
    Only string-typed fields are supported.
    """
    if not is_dataclass(target) or isinstance(target, type):
        raise TypeError("target must be a dataclass instance")

    mapping: Dict[str, Tuple[str, type]] = {}
    for f in fields(target):
        # Only support string fields for secrets (consistent with Go SDK)
        # Allow plain 'str' annotations; reject others to keep behavior predictable
        if f.type is not str:
            raise TypeError(
                f"target field '{f.name}' is not a string (only str fields are supported)"
            )
        key = f.metadata.get("secret") if hasattr(f, "metadata") else None
        if key and isinstance(key, str) and key.strip():
            mapping[key] = (f.name, f.type)
        else:
            mapping[f.name.lower()] = (f.name, f.type)
    return mapping


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


def _load_from_env(base_var_name: str, module: str, instance: str, target: Any) -> None:
    """
    Load secrets from environment variables with names:
        {base_var_name}_{module}_{instance}_{field_key} (uppercased)
    instance names have '-' replaced with '_' for env var compatibility.
    """
    field_map = _get_field_map(target)
    prefix = f"{base_var_name}_{module}_{instance}".upper()

    for key, (attr_name, _) in field_map.items():
        var_name = f"{prefix}_{key}".upper()
        value = os.environ.get(var_name)
        if value is None:
            # Align with Go: error if env var not found
            raise KeyError(f"env var not found: {var_name}")
        setattr(target, attr_name, value)


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
      2. Environment variables: {base_var_name}_{module}_{instance}_{field_key} (uppercased)

    Raises:
      ValueError: If inputs are invalid or target is not a dataclass instance
      FileNotFoundError / NotADirectoryError / OSError: If mount path issues occur
      KeyError: If environment variables are missing on fallback
      RuntimeError: If both mount and env var loading fail (aggregated error)
    """
    _validate_inputs(module, instance)

    errors: list[str] = []
    normalized_module = module.replace("-", "_")
    normalized_instance = instance.replace("-", "_")

    try:
        _load_from_mount(base_volume_mount, module, instance, target)
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
    mount_dir = os.path.join(base_volume_mount, module, instance) + "/"
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
