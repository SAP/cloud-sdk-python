"""SAP Cloud SDK for Python - Agent Decorators module.

Decorator-based configuration-as-code for SAP AI agents. Developers
annotate functions with decorators to expose configuration fields
(prompts, models, settings) to a low-code UI.

Usage:
    from sap_cloud_sdk.agent_decorators import (
        prompt_section,
        agent_config,
        agent_model,
    )

    @prompt_section(
        key="prompts.system",
        label="System Prompt",
        description="Main system prompt for the agent",
    )
    def system_prompt() -> str:
        return "You are a helpful assistant."
"""

from sap_cloud_sdk.agent_decorators.decorators import (
    agent_config,
    agent_model,
    prompt_section,
)
from sap_cloud_sdk.agent_decorators.exceptions import (
    AgentDecoratorError,
)

__all__ = [
    # Decorators
    "prompt_section",
    "agent_config",
    "agent_model",
    # Exceptions
    "AgentDecoratorError",
]
