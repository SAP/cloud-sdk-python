"""Unit tests for the create_checkpointer() LangGraph factory."""

import builtins
from typing import Any, TypedDict
from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
from sap_cloud_sdk.core.telemetry import Module, Operation

_REQUEST_METRIC = "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"

class TestCreateCheckpointer:
    """Tests for create_checkpointer() factory."""

    # ── Return type ───────────────────────────────────────────────────────────

    def test_returns_in_memory_saver(self):
        """Factory returns LangGraph's InMemorySaver."""
        result = create_checkpointer()
        assert isinstance(result, InMemorySaver)

    def test_ttl_returns_timed_in_memory_saver(self):
        """Passing ttl_seconds returns a TimedInMemorySaver (deprecated path)."""
        from sap_cloud_sdk.agent_memory.factory._timed_memory import TimedInMemorySaver

        with pytest.warns(DeprecationWarning, match="ttl_seconds parameter is deprecated"):
            result = create_checkpointer(ttl_seconds=3600)
        assert isinstance(result, TimedInMemorySaver)
        assert result.ttl_seconds == 3600

    def test_no_ttl_does_not_warn(self):
        """The default (no ttl_seconds) path is not deprecated and does not warn."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            create_checkpointer()

    # ── Deprecation telemetry ─────────────────────────────────────────────────

    def test_ttl_path_records_deprecated_metric(self):
        """The deprecated ttl_seconds path records a single deprecated=True metric."""
        with patch(_REQUEST_METRIC) as metric:
            create_checkpointer(ttl_seconds=3600)
        metric.assert_called_once_with(
            Module.AGENT_MEMORY,
            None,
            Operation.AGENT_MEMORY_CREATE_CHECKPOINTER,
            True,
        )

    def test_no_ttl_records_no_metric(self):
        """A bare create_checkpointer() is not deprecated and emits no metric."""
        with patch(_REQUEST_METRIC) as metric:
            create_checkpointer()
        metric.assert_not_called()

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
