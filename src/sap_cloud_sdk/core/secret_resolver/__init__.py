"""
Secret resolver: load configuration/secrets from mounted files or environment variables

Usage:
    from dataclasses import dataclass, field
    from sap_cloud_sdk.secret_resolver import read_from_mount_and_fallback_to_env_var

    @dataclass
    class MyConfig:
        username: str = field(metadata={"secret": "username"})
        password: str = field(metadata={"secret": "password"})
        endpoint: str = "http://localhost"

    cfg = MyConfig()
    read_from_mount_and_fallback_to_env_var(
        base_volume_mount="/etc/secrets/appfnd",
        base_var_name="CLOUD_SDK_CFG",
        module="objectstore",
        instance="default",
        target=cfg
    )
"""

from .resolver import read_from_mount_and_fallback_to_env_var, resolve_base_mount

__all__ = ["read_from_mount_and_fallback_to_env_var", "resolve_base_mount"]
