"""Unit tests for the create_checkpointer() LangGraph factory."""

import builtins
from typing import Any, TypedDict
from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer


class TestCreateCheckpointer:
    """Tests for create_checkpointer() factory."""

    # ── Return type ───────────────────────────────────────────────────────────

    def test_returns_in_memory_saver(self):
        """Factory returns LangGraph's InMemorySaver."""
        result = create_checkpointer()
        assert isinstance(result, InMemorySaver)

    def test_ttl_seconds_still_returns_in_memory_saver(self):
        """ttl_seconds returns TimedInMemorySaver."""
        from sap_cloud_sdk.agent_memory.factory._timed_memory import TimedInMemorySaver
        result = create_checkpointer(ttl_seconds=3600)
        assert isinstance(result, TimedInMemorySaver)

    def test_ttl_seconds_logs_warning(self, caplog):
        """ttl_seconds logs a warning about in-process state."""
        import logging
        with caplog.at_level(
            logging.WARNING,
            logger="sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint",
        ):
            create_checkpointer(ttl_seconds=3600)
        assert "TimedInMemorySaver" in caplog.text

    # ── Missing langgraph ─────────────────────────────────────────────────────

    def test_missing_langgraph_raises_import_error(self):
        """Clear ImportError when langgraph is not installed."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langgraph.checkpoint.memory":
                raise ImportError("No module named 'langgraph'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="langgraph is required"):
                create_checkpointer()

    # ── LangGraph integration ─────────────────────────────────────────────────

    def test_checkpointer_compiles_with_langgraph_graph(self):
        """Returned checkpointer can compile a LangGraph StateGraph."""
        class SimpleState(TypedDict):
            value: str

        def noop(state: SimpleState) -> SimpleState:
            return state

        builder = StateGraph(SimpleState)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        app: Any = builder.compile(checkpointer=create_checkpointer())
        assert app is not None

    def test_checkpointer_persists_state_across_invocations(self):
        """State is preserved across invocations on the same thread_id."""
        class TickState(TypedDict):
            values: list

        def append_node(state: TickState) -> TickState:
            return {"values": state["values"] + ["tick"]}

        builder = StateGraph(TickState)  # type: ignore
        builder.add_node("append", append_node)
        builder.add_edge(START, "append")
        builder.add_edge("append", END)

        app: Any = builder.compile(checkpointer=create_checkpointer())
        config: RunnableConfig = {"configurable": {"thread_id": "test-thread-persist"}}

        result1 = app.invoke({"values": []}, config)
        assert result1["values"] == ["tick"]

        result2 = app.invoke({"values": result1["values"]}, config)
        assert result2["values"] == ["tick", "tick"]

    def test_different_thread_ids_are_isolated(self):
        """Two thread IDs maintain independent state."""
        class NameState(TypedDict):
            name: str

        def noop(state: NameState) -> NameState:
            return state

        builder = StateGraph(NameState)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        app: Any = builder.compile(checkpointer=create_checkpointer())
        config_a: RunnableConfig = {"configurable": {"thread_id": "thread-isolation-a"}}
        config_b: RunnableConfig = {"configurable": {"thread_id": "thread-isolation-b"}}

        app.invoke({"name": "alice"}, config_a)
        app.invoke({"name": "bob"}, config_b)

        assert app.get_state(config_a).values["name"] == "alice"
        assert app.get_state(config_b).values["name"] == "bob"
