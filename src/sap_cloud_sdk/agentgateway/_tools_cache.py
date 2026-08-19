"""Result cache for MCP tool lists.

Caches list[MCPTool] per (filter, auth-type) key to avoid redundant MCP
session round-trips during agentic loops. Bounded by max_size with LRU
eviction; each entry has a monotonic TTL.

Thread safety:
CPython GIL makes individual OrderedDict operations atomic, but compound
check-then-set is not. Two concurrent coroutines for the same key may both
miss and both fetch; the race produces redundant tool-list requests, not
data corruption. This matches the accepted behaviour in _token_cache.py.
"""

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

from sap_cloud_sdk.agentgateway._models import CacheOptions, MCPTool, MCPToolFilter

logger = logging.getLogger(__name__)


@dataclass
class _CachedToolList:
    tools: list[MCPTool]
    expires_at: float  # time.monotonic() value

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at


def _make_cache_key(filter: MCPToolFilter | None, user_scoped: bool) -> str:
    """Build a stable string key from filter options and auth type."""
    ord_ids = "|".join(sorted(filter.ord_ids)) if filter and filter.ord_ids else ""
    names = "|".join(sorted(filter.names)) if filter and filter.names else ""
    auth = "user" if user_scoped else "system"
    return f"{auth}:ord={ord_ids}:names={names}"


class MCPToolsCache:
    """TTL + LRU cache for MCP tool list results.

    Keyed by (filter combo, auth type). Entries expire after `options.ttl`
    seconds. When the number of entries exceeds `options.max_size`, the
    least-recently-used entry is evicted.

    Callers hold a reference to their CacheOptions instance and call
    evict() to invalidate all entries.
    """

    def __init__(self) -> None:
        self._entries: OrderedDict[str, _CachedToolList] = OrderedDict()

    def get(
        self,
        filter: MCPToolFilter | None,
        user_scoped: bool,
    ) -> list[MCPTool] | None:
        """Return cached tools for the given filter/auth combo, or None if miss/expired."""
        key = _make_cache_key(filter, user_scoped)
        entry = self._entries.get(key)
        if entry and entry.is_valid():
            self._entries.move_to_end(key)
            return entry.tools
        if entry:
            del self._entries[key]
        return None

    def set(
        self,
        tools: list[MCPTool],
        filter: MCPToolFilter | None,
        user_scoped: bool,
        options: CacheOptions,
    ) -> None:
        """Store tools under the given filter/auth key, evicting LRU if at capacity."""
        key = _make_cache_key(filter, user_scoped)
        expires_at = time.monotonic() + options.ttl
        self._entries[key] = _CachedToolList(tools=tools, expires_at=expires_at)
        self._entries.move_to_end(key)
        while len(self._entries) > options.max_size:
            evicted, _ = self._entries.popitem(last=False)
            logger.debug("MCP tools cache full — evicted key '%s'", evicted)

    def evict(self) -> None:
        """Clear all cached entries. Forces a fresh fetch on the next call."""
        self._entries.clear()
        logger.debug("MCP tools cache evicted")
