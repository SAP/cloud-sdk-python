"""LangGraph checkpointer factory for SAP Agent Memory.

Usage::

    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

    # No TTL — plain InMemorySaver
    checkpointer = create_checkpointer()

    # With TTL — TimedInMemorySaver evicts inactive threads automatically
    checkpointer = create_checkpointer(ttl_seconds=3600)

    app = workflow.compile(checkpointer=checkpointer)

    # Or with LangChain create_agent:
    from langchain.agents import create_agent
    agent = create_agent(model="...", tools=[...], checkpointer=checkpointer)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_checkpointer(*, ttl_seconds: Optional[int] = None):
    """Create a LangGraph checkpointer for the current environment.

    Returns LangGraph's ``InMemorySaver`` (no TTL) or ``TimedInMemorySaver``
    (with TTL-based thread eviction). State is held in-process and does not
    survive restarts.

    Args:
        ttl_seconds: Evict threads inactive for this many seconds.
                     ``None`` (default) disables eviction.

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
    except ImportError:
        raise ImportError(
            "langgraph is required for create_checkpointer(). "
            "Install it with: pip install langgraph"
        )

    if ttl_seconds is not None:
        from sap_cloud_sdk.agent_memory.factory._timed_memory import TimedInMemorySaver

        logger.warning(
            "create_checkpointer(): using TimedInMemorySaver(ttl_seconds=%d) — "
            "session state is in-process only and will be lost on process exit.",
            ttl_seconds,
        )
        return TimedInMemorySaver(ttl_seconds=ttl_seconds)

    logger.warning(
        "create_checkpointer(): using InMemorySaver — "
        "session state is in-process only and will be lost on process exit."
    )
    return InMemorySaver()
