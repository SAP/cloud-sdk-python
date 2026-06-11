"""LangGraph test agent used by the telemetry integration tests."""

import os

import pytest


def build_langgraph_agent():
    """Build a minimal single-node LangGraph agent backed by LiteLLM via AI Core.

    Requires AICORE_MODEL env var (e.g. "anthropic--claude-3-5-haiku") in addition
    to the AICORE_* credentials set by set_aicore_config(). LiteLLM uses the
    "sap/<model>" prefix to route through the SAP AI Core provider.
    """
    try:
        from dataclasses import dataclass
        from typing import Annotated

        from langchain_core.messages import BaseMessage
        from langchain_litellm import ChatLiteLLM  # ty: ignore[unresolved-import]
        from langgraph.graph import END, StateGraph  # ty: ignore[unresolved-import]
        from langgraph.graph.message import add_messages  # ty: ignore[unresolved-import]
    except ImportError:
        pytest.skip("langchain-litellm or langgraph not installed")

    @dataclass
    class State:
        messages: Annotated[list[BaseMessage], add_messages]

    model_name = os.environ.get("AICORE_MODEL") or "anthropic--claude-4.5-sonnet"
    llm = ChatLiteLLM(model=f"sap/{model_name}")

    def call_llm(state: State) -> State:
        return State(messages=[llm.invoke(state.messages)])

    graph = StateGraph(State)
    graph.add_node("llm", call_llm)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)
    return graph.compile()
