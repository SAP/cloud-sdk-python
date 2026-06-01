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
        from langchain_litellm import ChatLiteLLM
        from langgraph.graph import END, StateGraph
    except ImportError:
        pytest.skip("langchain-litellm or langgraph not installed")

    model_name = os.environ.get("AICORE_MODEL")
    if not model_name:
        model_name = "anthropic--claude-4.5-sonnet"

    llm = ChatLiteLLM(model=f"sap/{model_name}")

    def call_llm(state):
        return {"messages": [llm.invoke(state["messages"])]}

    graph = StateGraph(dict)
    graph.add_node("llm", call_llm)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)
    return graph.compile()
