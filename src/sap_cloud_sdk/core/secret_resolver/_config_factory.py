"""Generic config factory for re-reading service binding credentials on demand."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Generic, Optional, Type, TypeVar
from sap_cloud_sdk.core.secret_resolver.resolver import resolve_base_mount

logger = logging.getLogger(__name__)

C = TypeVar("C")

_BASE_VOLUME_MOUNT = "/etc/secrets/appfnd"
_BASE_VAR_NAME = "CLOUD_SDK_CFG"


class ConfigFactory(Generic[C]):
    """Re-reads a service binding from mount or env on every invocation.

    Callers that need always-fresh credentials (e.g. after secret rotation)
    call the factory before each token refresh. The factory also tracks the
    filesystem mtime of the secret directory so callers can detect rotation
    proactively via :meth:`has_changed`.

    Args:
        module: Service module name (e.g. ``"hana-agent-memory"``).
        instance: Binding instance name (e.g. ``"default"`` or tenant subdomain).
        binding_cls: Dataclass type used by the secret resolver as ``target``.
        extract: Callable that converts a populated ``binding_cls`` to ``C``.
        base_volume_mount: Root path for mounted secrets.
        base_var_name: Env-var prefix used by the secret resolver.
    """

    def __init__(
        self,
        module: str,
        instance: str,
        binding_cls: Type[Any],
        extract: Callable[[Any], C],
        *,
        base_volume_mount: str = _BASE_VOLUME_MOUNT,
        base_var_name: str = _BASE_VAR_NAME,
    ) -> None:
        self._module = module
        self._instance = instance
        self._binding_cls = binding_cls
        self._extract = extract
        self._base_volume_mount = base_volume_mount
        self._base_var_name = base_var_name
        self._watch_path = os.path.join(
            resolve_base_mount(base_volume_mount), module, instance
        )
        self._last_mtime: Optional[float] = None

    def __call__(self) -> C:
        """Read the binding and return a fresh config instance."""
        from sap_cloud_sdk.core.secret_resolver import (
            read_from_mount_and_fallback_to_env_var,
        )

        binding = self._binding_cls()
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount=self._base_volume_mount,
            base_var_name=self._base_var_name,
            module=self._module,
            instance=self._instance,
            target=binding,
        )
        binding.validate()
        return self._extract(binding)

    def has_changed(self) -> bool:
        """Return ``True`` if the secret directory mtime changed since the last check.

        On the first call, records the baseline mtime and returns ``False`` to
        avoid false positives. Returns ``False`` when the watch path does not
        exist (env-var backed bindings).
        """
        try:
            mtime = os.stat(self._watch_path).st_mtime
        except OSError:
            return False
        changed = self._last_mtime is not None and mtime != self._last_mtime
        self._last_mtime = mtime
        if changed:
            logger.info(
                "Secret rotation detected for %s/%s (mtime changed to %.3f)",
                self._module,
                self._instance,
                mtime,
            )
        return changed
