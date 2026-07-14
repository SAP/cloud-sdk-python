"""Unit tests for TimedInMemorySaver and create_checkpointer(ttl_seconds=...)."""

import time
from typing import Any, TypedDict
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from sap_cloud_sdk.agent_memory.factory._timed_memory import TimedInMemorySaver
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer


class TestCreateCheckpointerWithTTL:
    """Tests for create_checkpointer(ttl_seconds=...) factory."""

    def test_no_ttl_returns_in_memory_saver(self):
        """Default returns plain InMemorySaver when ttl_seconds is None."""
        result = create_checkpointer()
        assert isinstance(result, InMemorySaver)
        assert not isinstance(result, TimedInMemorySaver)

    def test_ttl_returns_timed_in_memory_saver(self):
        """ttl_seconds returns TimedInMemorySaver."""
        result = create_checkpointer(ttl_seconds=3600)
        assert isinstance(result, TimedInMemorySaver)

    def test_ttl_value_is_set(self):
        """ttl_seconds value is stored on the returned saver."""
        result = create_checkpointer(ttl_seconds=7200)
        assert isinstance(result, TimedInMemorySaver)
        assert result.ttl_seconds == 7200

    def test_timed_saver_is_also_in_memory_saver(self):
        """TimedInMemorySaver is a valid BaseCheckpointSaver subtype."""
        result = create_checkpointer(ttl_seconds=3600)
        assert isinstance(result, InMemorySaver)

    def test_compiles_with_langgraph_graph(self):
        """Timed checkpointer compiles a StateGraph correctly."""
        class State(TypedDict):
            value: str

        def noop(state: State) -> State:
            return state

        builder = StateGraph(State)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        app: Any = builder.compile(checkpointer=create_checkpointer(ttl_seconds=3600))
        assert app is not None


class TestTimedInMemorySaver:
    """Tests for TimedInMemorySaver behaviour."""

    def test_default_ttl(self):
        """Default TTL is 3600 seconds."""
        saver = TimedInMemorySaver()
        assert saver.ttl_seconds == 3600

    def test_custom_ttl(self):
        """Custom TTL is stored correctly."""
        saver = TimedInMemorySaver(ttl_seconds=1800)
        assert saver.ttl_seconds == 1800

    def test_sweeper_thread_is_daemon(self):
        """Background sweep thread is a daemon — dies with the process."""
        saver = TimedInMemorySaver()
        assert saver._sweeper.daemon is True
        assert saver._sweeper.is_alive()

    def test_put_updates_last_active(self):
        """put() updates last-active timestamp for the thread."""
        class State(TypedDict):
            x: int

        def noop(state: State) -> State:
            return state

        builder = StateGraph(State)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        saver = TimedInMemorySaver(ttl_seconds=3600)
        app: Any = builder.compile(checkpointer=saver)
        config: RunnableConfig = {"configurable": {"thread_id": "ttl-test-1"}}

        app.invoke({"x": 1}, config)

        assert "ttl-test-1" in saver._last_active

    def test_expired_thread_evicted(self):
        """Threads inactive beyond ttl_seconds are evicted by _evict_expired."""
        class State(TypedDict):
            x: int

        def noop(state: State) -> State:
            return state

        builder = StateGraph(State)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        saver = TimedInMemorySaver(ttl_seconds=1)
        app: Any = builder.compile(checkpointer=saver)
        config: RunnableConfig = {"configurable": {"thread_id": "evict-me"}}

        app.invoke({"x": 1}, config)
        assert "evict-me" in saver._last_active

        # Backdate last-active to simulate 2 seconds of inactivity
        with saver._lock:
            saver._last_active["evict-me"] = time.monotonic() - 2

        saver._evict_expired()

        assert "evict-me" not in saver._last_active
        assert saver.storage.get("evict-me") is None

    def test_active_thread_not_evicted(self):
        """Threads active within ttl_seconds are not evicted."""
        class State(TypedDict):
            x: int

        def noop(state: State) -> State:
            return state

        builder = StateGraph(State)  # type: ignore
        builder.add_node("noop", noop)
        builder.add_edge(START, "noop")
        builder.add_edge("noop", END)

        saver = TimedInMemorySaver(ttl_seconds=3600)
        app: Any = builder.compile(checkpointer=saver)
        config: RunnableConfig = {"configurable": {"thread_id": "keep-me"}}

        app.invoke({"x": 1}, config)
        saver._evict_expired()

        assert "keep-me" in saver._last_active
        assert saver.storage.get("keep-me") is not None

    def test_state_preserved_across_invocations(self):
        """TimedInMemorySaver preserves state across invocations."""
        class State(TypedDict):
            values: list

        def append_node(state: State) -> State:
            return {"values": state["values"] + ["tick"]}

        builder = StateGraph(State)  # type: ignore
        builder.add_node("append", append_node)
        builder.add_edge(START, "append")
        builder.add_edge("append", END)

        app: Any = builder.compile(checkpointer=TimedInMemorySaver(ttl_seconds=3600))
        config: RunnableConfig = {"configurable": {"thread_id": "persist-test"}}

        result1 = app.invoke({"values": []}, config)
        assert result1["values"] == ["tick"]

        result2 = app.invoke({"values": result1["values"]}, config)
        assert result2["values"] == ["tick", "tick"]
