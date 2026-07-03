"""LangGraph checkpointer factory for SAP Agent Memory.

Usage::

    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

    checkpointer = create_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)

    # Or with LangChain create_agent:
    from langchain.agents import create_agent
    agent = create_agent(model="...", tools=[...], checkpointer=checkpointer)
"""

import logging

logger = logging.getLogger(__name__)


def create_checkpointer():
    """Create a LangGraph checkpointer for the current environment.

    Returns LangGraph's ``InMemorySaver``. State is held in-process
    and does not survive restarts. Persistent checkpointing backed by
    the Agent Memory Service is not yet supported.

    Returns:
        BaseCheckpointSaver instance.

    Raises:
        ImportError: If langgraph is not installed.

    Example — compile a LangGraph workflow::

        checkpointer = create_checkpointer()
        app = workflow.compile(checkpointer=checkpointer)
        result = app.invoke(input, {"configurable": {"thread_id": "abc"}})

    Example — use with LangChain create_agent::

        from langchain.agents import create_agent
        agent = create_agent(
            model="...",
            tools=[...],
            checkpointer=create_checkpointer(),
        )
    """
    try:
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError:
        raise ImportError(
            "langgraph is required for create_checkpointer(). "
            "Install it with: pip install langgraph"
        )
    return InMemorySaver()
