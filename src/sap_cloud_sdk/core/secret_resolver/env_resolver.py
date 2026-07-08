import os
from typing import Any

from sap_cloud_sdk.core.secret_resolver._mapping import _get_field_map
from sap_cloud_sdk.core.secret_resolver.constants import BASE_VAR_NAME


class EnvVarResolver:
    """Resolves bindings from environment variables.

    Reads variables named ``{base_var_name}_{module}_{instance}_{field_key}``
    (uppercased, hyphens in module/instance replaced with underscores).

    Args:
        base_var_name: Env var name prefix. Defaults to ``"CLOUD_SDK_CFG"``.
    """

    def __init__(self, base_var_name: str = BASE_VAR_NAME) -> None:
        self._base_var_name = base_var_name

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Load secrets from environment variables."""
        normalized_module = module.replace("-", "_")
        normalized_instance = instance.replace("-", "_")
        _load_from_env(
            self._base_var_name, normalized_module, normalized_instance, target
        )


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
