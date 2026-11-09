"""Per-module shared backend registry.

SDK modules that create a new client on every request can opt into a
per-module *shared* backend so that the cache survives across requests.
This module holds the registry that maps module names to their backends.

Sizing (``max_size``, ``on_evict``) is fixed on the **first** call for a
given module name; subsequent calls with different values are ignored.
That is intentional — a module uses one sizing policy and registers its
backend exactly once at startup.

Private to the cache package; not exported from ``sap_cloud_sdk.core.resilience.cache``.
"""

from __future__ import annotations

import threading
from typing import Callable

from sap_cloud_sdk.core.resilience.cache._lru_backend import InMemoryLRUBackend

# Module-level registry guarded by a lock so concurrent first-time
# registrations are safe.
_lock: threading.Lock = threading.Lock()
_backends: dict[str, InMemoryLRUBackend] = {}


def get_module_backend(
    name: str,
    max_size: int,
    on_evict: Callable[[str, str], None] | None,
) -> InMemoryLRUBackend:
    """Return the shared ``InMemoryLRUBackend`` for *name*, creating it on the first call.

    Args:
        name: Logical module identifier, e.g. ``"agentgateway"``.
        max_size: Maximum backend capacity (LRU). Used only on the first
            call for *name*; ignored on subsequent calls.
        on_evict: Eviction callback. Used only on the first call for *name*.

    Returns:
        The singleton ``InMemoryLRUBackend`` for *name*.
    """
    # Fast path — backend already registered.
    try:
        return _backends[name]
    except KeyError:
        pass

    with _lock:
        # Re-check under the lock to avoid a race between two first-time callers.
        if name not in _backends:
            _backends[name] = InMemoryLRUBackend(max_size=max_size, on_evict=on_evict)

        return _backends[name]


def reset_module_backends() -> None:
    """Clear the registry.  **Test seam only — do not call in production.**

    Removes all per-module backend singletons so that the next call to
    ``get_module_backend()`` starts fresh. This is necessary because
    module-level state persists across test cases.
    """
    with _lock:
        _backends.clear()
