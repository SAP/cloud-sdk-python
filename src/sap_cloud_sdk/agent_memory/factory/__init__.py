"""Factory subpackage for SAP Agent Memory framework adapters.

Each module in this package provides a factory function that creates the
appropriate framework-specific implementation for the current environment.

Available factories:

- :func:`sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint.create_checkpointer`
  — returns a LangGraph ``BaseCheckpointSaver`` (short-term memory / graph state)

- :func:`sap_cloud_sdk.agent_memory.thread_registry.create_thread_registry`
  — returns a :class:`~sap_cloud_sdk.agent_memory.thread_registry.BaseThreadRegistry`
  for thread lifecycle, ownership, and TTL management

Usage:

    from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
    from sap_cloud_sdk.agent_memory.thread_registry import create_thread_registry
"""
