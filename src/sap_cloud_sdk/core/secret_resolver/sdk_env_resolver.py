"""Resolver that reads service binding secrets from environment variables."""

import os
from typing import Any


from sap_cloud_sdk.core.secret_resolver._mapping import _get_field_map
from sap_cloud_sdk.core.secret_resolver.constants import BASE_VAR_NAME


class SdkEnvVarResolver:
    """Resolves bindings from environment variables.

    Reads variables named ``{base_var_name}_{service_name}_{instance}_{field_key}``
    (uppercased, hyphens in service_name/instance replaced with underscores).

    Args:
        base_var_name: Env var name prefix. Defaults to ``"CLOUD_SDK_CFG"``.
    """

    def __init__(self, base_var_name: str = BASE_VAR_NAME) -> None:
        self._base_var_name = base_var_name

    def resolve(self, service_name: str, instance: str, target: Any) -> None:
        """Load secrets from environment variables."""
        normalized_service_name = service_name.replace("-", "_")
        normalized_instance = instance.replace("-", "_")

        field_map = _get_field_map(target)
        prefix = f"{self._base_var_name}_{normalized_service_name}_{normalized_instance}".upper()

        for key, (attr_name, _) in field_map.items():
            var_name = f"{prefix}_{key}".upper()
            value = os.environ.get(var_name)
            if value is None:
                # Align with Go: error if env var not found
                raise KeyError(f"env var not found: {var_name}")
            setattr(target, attr_name, value)
