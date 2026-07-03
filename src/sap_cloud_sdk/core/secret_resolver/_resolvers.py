"""BindingResolver protocol and built-in implementations.

This module defines the core extensibility contract for secret resolution.
Each resolver encapsulates one binding source. Compose them into an ordered
chain via :class:`ChainedResolver` — the first resolver that succeeds wins.

Protocol contract::

    resolver.resolve(module, instance, target)

- On success: populates ``target`` in-place, returns ``None``
- On failure: raises any exception; the chain tries the next resolver
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Protocol, runtime_checkable

from sap_cloud_sdk.core.secret_resolver.resolver import (
    _load_from_env,
    _load_from_mount,
    resolve_base_mount,
)


@runtime_checkable
class Resolver(Protocol):
    """Contract for a single binding resolution strategy.

    A ``BindingResolver`` reads credentials from one source and populates
    ``target`` in-place. Implementations raise on failure so that a
    :class:`ChainedResolver` can try the next strategy.

    Any object implementing ``resolve`` with this signature satisfies the
    protocol — no inheritance required.
    """

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Populate ``target`` with credentials for ``module``/``instance``.

        Args:
            module: Service module name (e.g. ``"destination"``).
            instance: Instance identifier (e.g. ``"default"``).
            target: Dataclass instance whose ``str`` fields will be set.

        Raises:
            Any exception on failure; the caller determines how to handle it.
        """
        ...


class MountResolver:
    """Resolves bindings from a mounted volume path.

    Reads secret files at ``{base_volume_mount}/{module}/{instance}/{field_key}``.
    Respects the ``SERVICE_BINDING_ROOT`` environment variable (servicebinding.io
    spec) as an override for ``base_volume_mount``.

    Args:
        base_volume_mount: Base path for mounted secrets. Defaults to
            ``/etc/secrets/appfnd``.
    """

    def __init__(self, base_volume_mount: str = "/etc/secrets/appfnd") -> None:
        self._base_volume_mount = base_volume_mount

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Load secrets from the mounted volume path."""
        effective_base = resolve_base_mount(self._base_volume_mount)
        _load_from_mount(effective_base, module, instance, target)


class EnvVarResolver:
    """Resolves bindings from environment variables.

    Reads variables named ``{base_var_name}_{module}_{instance}_{field_key}``
    (uppercased, hyphens in module/instance replaced with underscores).

    Args:
        base_var_name: Env var name prefix. Defaults to ``"CLOUD_SDK_CFG"``.
    """

    def __init__(self, base_var_name: str = "CLOUD_SDK_CFG") -> None:
        self._base_var_name = base_var_name

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Load secrets from environment variables."""
        normalized_module = module.replace("-", "_")
        normalized_instance = instance.replace("-", "_")
        _load_from_env(
            self._base_var_name, normalized_module, normalized_instance, target
        )


class ChainedResolver:
    """Tries each resolver in order; returns on the first success.

    Collects failure messages from each resolver and raises a
    :class:`RuntimeError` with an aggregated report when all resolvers fail.

    Args:
        resolvers: Ordered list of :class:`BindingResolver` implementations to try.
        base_var_name: Used only for the error guidance message.
    """

    def __init__(
        self,
        resolvers: list[Resolver],
        base_var_name: str = "CLOUD_SDK_CFG",
    ) -> None:
        if not resolvers:
            raise ValueError("resolvers list must not be empty")
        self._resolvers = resolvers
        self._base_var_name = base_var_name

    def resolve(self, module: str, instance: str, target: Any) -> None:
        """Try each resolver in order; raise on total failure."""
        if not is_dataclass(target) or isinstance(target, type):
            raise TypeError("target must be a dataclass instance")
        for f in fields(target):
            if f.type is not str and f.type != "str":
                raise TypeError(
                    f"target field {f.name!r} is not a string (only str fields are supported)"
                )

        errors: list[str] = []
        for resolver in self._resolvers:
            try:
                resolver.resolve(module, instance, target)
                return
            except Exception as e:
                label = type(resolver).__name__
                errors.append(f"{label} failed: {e}")

        raise RuntimeError(
            f"module={module!r} instance={instance!r} failed to read secrets from all resolvers: "
            f"{errors}. "
            "Options: mount secrets under the service binding path, set environment variables "
            f"like {self._base_var_name}_{module}_{instance}_<KEY> (uppercased), or set VCAP_SERVICES."
        )
