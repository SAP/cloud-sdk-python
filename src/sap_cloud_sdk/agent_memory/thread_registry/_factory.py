"""Factory for creating a thread registry for the current environment."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sap_cloud_sdk.agent_memory.thread_registry._base import BaseThreadRegistry

logger = logging.getLogger(__name__)


def create_thread_registry(
    *,
    ttl_seconds: Optional[int] = None,
) -> "BaseThreadRegistry":
    """Create a thread registry for the current environment.

    Automatically detects whether Agent Memory Service credentials are available:

    - **Credentials present** — returns :class:`SAPAgentMemoryThreadRegistry` backed
      by the Agent Memory Service (persistent across restarts).
    - **No credentials** — falls back to :class:`InMemoryThreadRegistry`. State is
      in-process only and will not survive restarts.

    Args:
        ttl_seconds: Registry-level default inactivity threshold in seconds.
            Threads inactive for longer than this are treated as expired. The window
            slides — it resets on each write. Applied per-thread when the caller does
            not pass an explicit ``ttl_seconds`` per operation. ``None`` = never
            expire.

    Returns:
        A :class:`~sap_cloud_sdk.agent_memory.thread_registry.BaseThreadRegistry` instance.
    """
    from sap_cloud_sdk.agent_memory.config import _load_config_from_env
    from sap_cloud_sdk.agent_memory.thread_registry._in_memory import (
        InMemoryThreadRegistry,
    )
    from sap_cloud_sdk.agent_memory.thread_registry._service import (
        SAPAgentMemoryThreadRegistry,
    )

    config = _load_config_from_env()

    if config is not None:
        logger.info("create_thread_registry(): using SAPAgentMemoryThreadRegistry.")
        return SAPAgentMemoryThreadRegistry(
            config,
            default_ttl_seconds=ttl_seconds,
        )

    logger.warning(
        "create_thread_registry(): no Agent Memory Service credentials found, "
        "using InMemoryThreadRegistry — state is in-process only and will be "
        "lost on process exit."
    )
    return InMemoryThreadRegistry(
        default_ttl_seconds=ttl_seconds,
    )
