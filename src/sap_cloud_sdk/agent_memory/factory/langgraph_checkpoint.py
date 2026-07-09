"""LangGraph checkpointer factory for SAP Agent Memory.

Usage::

    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

    # No TTL
    checkpointer = create_checkpointer()

    # With TTL — accepted now, enforced when HanaAgentMemorySaver is available
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

    Returns LangGraph's ``InMemorySaver``. State is held in-process
    and does not survive restarts.

    Args:
        ttl_seconds: Thread TTL in seconds. Accepted for interface stability —
                     TTL enforcement will be active when ``HanaAgentMemorySaver``
                     is available. Has no effect with ``InMemorySaver``.

    Returns:
        BaseCheckpointSaver instance.

    Raises:
        ImportError: If langgraph is not installed.

    Example — no TTL::

        checkpointer = create_checkpointer()
        app = workflow.compile(checkpointer=checkpointer)

    Example — with TTL (enforced in production, accepted but inactive locally)::

        checkpointer = create_checkpointer(ttl_seconds=3600)
        app = workflow.compile(checkpointer=checkpointer)

    Example — with @agent_config for centralised TTL configuration::

        from sap_cloud_sdk.agent_decorators import agent_config

        @agent_config(
            key="config.thread_ttl_seconds",
            label="Thread TTL (seconds)",
            description="Evict inactive threads after this period",
        )
        def thread_ttl_seconds() -> int:
            return 3600

        checkpointer = create_checkpointer(ttl_seconds=thread_ttl_seconds())
    """
    try:
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError:
        raise ImportError(
            "langgraph is required for create_checkpointer(). "
            "Install it with: pip install langgraph"
        )

    if ttl_seconds is not None:
        logger.warning(
            "create_checkpointer(ttl_seconds=%d): TTL has no effect with "
            "InMemorySaver. TTL will be enforced when HanaAgentMemorySaver "
            "is available. Manage thread eviction manually via delete_thread() "
            "for local development.",
            ttl_seconds,
        )

    logger.warning(
        "create_checkpointer(): using InMemorySaver — "
        "session state is in-process only and will be lost on process exit."
    )
    return InMemorySaver()
