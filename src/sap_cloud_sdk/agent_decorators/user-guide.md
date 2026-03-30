# Agent Decorators User Guide

This module provides a decorator-based configuration-as-code system for SAP AI agents. Developers annotate functions with decorators to expose configuration fields — prompts, model selections, and agent settings — to a low-code UI. External tooling discovers these markers in source text and extracts their arguments and return values.

## Installation

The agent decorators module is part of the Cloud SDK for Python and is automatically available when the SDK is installed.

## Import

```python
from sap_cloud_sdk.agent_decorators import (
    prompt_section,
    agent_config,
    agent_model,
)
```

## Quick Start

```python
from sap_cloud_sdk.agent_decorators import prompt_section, agent_model

# Define a prompt with a coded default
@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="Main system prompt for the agent",
)
def system_prompt() -> str:
    return "You are a helpful assistant."

# Define the model selection
@agent_model(key="config.model", label="LLM Model")
def model_name() -> str:
    return "gpt-4"
```

## Decorators

### @prompt_section

Expose a prompt section for editing.

```python
from sap_cloud_sdk.agent_decorators import prompt_section

@prompt_section(
    key="prompts.identity",
    label="Agent Identity",
    description="Core identity and role definition",
    validation={"format": "text", "max_length": 500},
)
def identity_prompt() -> str:
    return "You are an expert assistant specializing in SAP systems."
```

### @agent_config

Expose a configuration value for editing.

```python
from sap_cloud_sdk.agent_decorators import agent_config

@agent_config(
    key="config.temperature",
    label="Temperature",
    description="Controls randomness (0.0 = deterministic, 1.0 = creative)",
)
def temperature() -> float:
    return 0.7
```

### @agent_model

Expose a model selection. The `description` parameter is optional.

```python
from sap_cloud_sdk.agent_decorators import agent_model

@agent_model(
    key="config.model",
    label="Default Model",
    description="The LLM model to use",
)
def default_model() -> str:
    return "gpt-4"
```

## Error Handling

```python
from sap_cloud_sdk.agent_decorators.exceptions import AgentDecoratorError

try:
    @prompt_section(key="", label="L", description="D")
    def bad():
        return ""
except AgentDecoratorError as e:
    # Raised when decorator arguments are invalid (e.g. empty key)
    print(f"Decorator error: {e}")
```
