"""LangGraph checkpointer factory for SAP Agent Memory.

Usage::

    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

    # No TTL — plain InMemorySaver
    checkpointer = create_checkpointer()

    # ttl_seconds is deprecated — use create_thread_registry(ttl_seconds=...) instead
    checkpointer = create_checkpointer(ttl_seconds=3600)  # deprecated

    app = workflow.compile(checkpointer=checkpointer)

    # Or with LangChain create_agent:
    from langchain.agents import create_agent
    agent = create_agent(model="...", tools=[...], checkpointer=checkpointer)
"""

import logging
import warnings
from typing import Optional

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


@record_metrics(
    Module.AGENT_MEMORY,
    Operation.AGENT_MEMORY_CREATE_CHECKPOINTER,
    deprecated=True,
)
def _create_timed_checkpointer(ttl_seconds: int):
    """Build the deprecated TTL-based checkpointer.

    Isolated into its own decorated helper so the ``deprecated=True`` metric is
    recorded only for the deprecated ``ttl_seconds`` path — a bare
    ``create_checkpointer()`` never reaches here and emits nothing.
    """
    from sap_cloud_sdk.agent_memory.factory._timed_memory import TimedInMemorySaver

    return TimedInMemorySaver(ttl_seconds=ttl_seconds)


def create_checkpointer(*, ttl_seconds: Optional[int] = None):
    """Create a LangGraph checkpointer for the current environment.

    Returns LangGraph's ``InMemorySaver`` (no TTL) or ``TimedInMemorySaver``
    (with TTL-based thread eviction). State is held in-process and does not
    survive restarts.

    Args:
        ttl_seconds: Evict threads inactive for this many seconds.
                     ``None`` (default) disables eviction.

                     .. deprecated::
                        TTL is now managed at the thread level. Call
                        ``create_checkpointer()`` without ``ttl_seconds`` and
                        pass ``ttl_seconds`` to ``create_thread_registry()``
                        instead. Threads that expire in the registry
                        automatically clean up their checkpoints.

    Returns:
        BaseCheckpointSaver instance.

    Raises:
        ImportError: If langgraph is not installed.

    Example — no TTL::

        checkpointer = create_checkpointer()
        app = workflow.compile(checkpointer=checkpointer)

    Example — evict threads inactive for 1 hour::

        checkpointer = create_checkpointer(ttl_seconds=3600)
        app = workflow.compile(checkpointer=checkpointer)
    """
    try:
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError as exc:
        raise ImportError(
            "langgraph is required for create_checkpointer(). "
            "Install it with: pip install sap-cloud-sdk[langgraph] or pip install langgraph"
        ) from exc

    if ttl_seconds is not None:
        warnings.warn(
            "The ttl_seconds parameter is deprecated. TTL is now managed at the thread level: "
            "call create_checkpointer() without ttl_seconds, and pass ttl_seconds to "
            "create_thread_registry() instead. Threads that expire in the registry will "
            "automatically clean up their checkpoints.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.warning(
            "create_checkpointer(ttl_seconds=%d): the ttl_seconds parameter is deprecated — "
            "pass ttl_seconds to create_thread_registry() instead. "
            "Threads that expire in the registry automatically clean up their checkpoints.",
            ttl_seconds,
        )
        return _create_timed_checkpointer(ttl_seconds)

    logger.info(
        "create_checkpointer(): using InMemorySaver — session state is "
        "in-process only and will be lost on process exit."
    )
    return InMemorySaver()
