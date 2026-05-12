"""Decorator functions for exposing agent configuration fields.

Each decorator is a marker — it annotates a zero-argument function
whose return value is the coded default for a configuration field.
External tooling discovers these markers in source text and extracts
their arguments and return values.

At decoration time only the *key* is validated; the function is
returned unchanged.
"""

from typing import Any, Callable, Optional

from .exceptions import AgentDecoratorError


def _validate_key(key: str) -> None:
    """Validate a decorator key.

    Raises:
        AgentDecoratorError: If the key is empty or whitespace-only.
    """
    if not key or not key.strip():
        raise AgentDecoratorError(
            f"Decorator key must be a non-empty string, got {key!r}"
        )


def prompt_section(
    key: str,
    label: str,
    description: str,
    validation: Optional[dict[str, Any]] = None,
) -> Callable:
    """Expose a prompt section for editing.

    Args:
        key: Unique identifier for this prompt (e.g. ``"prompts.system"``).
        label: Human-readable label shown in the UI.
        description: Help text explaining what this prompt does.
        validation: Optional validation rules as a dict
            (e.g. ``{"format": "text", "max_length": 500}``).

    Returns:
        A decorator that validates the key and returns the function unchanged.

    Raises:
        AgentDecoratorError: If the key is empty or whitespace-only.

    Example::

        @prompt_section(
            key="prompts.identity",
            label="Agent Identity",
            description="Core identity and role definition",
            validation={"format": "text", "max_length": 500},
        )
        def get_identity_prompt() -> str:
            return "You are an expert assistant..."
    """
    _validate_key(key)

    def decorator(fn: Callable[[], str]) -> Callable[[], str]:
        return fn

    return decorator


def agent_config(
    key: str,
    label: str,
    description: str,
) -> Callable:
    """Expose an agent configuration value for editing.

    Args:
        key: Unique identifier (e.g. ``"config.temperature"``).
        label: Human-readable label.
        description: Help text.

    Returns:
        A decorator that validates the key and returns the function unchanged.

    Raises:
        AgentDecoratorError: If the key is empty or whitespace-only.

    Example::

        @agent_config(
            key="config.temperature",
            label="Temperature",
            description="The temperature setting for the language model",
        )
        def get_temperature() -> float:
            return 0.7
    """
    _validate_key(key)

    def decorator(fn: Callable) -> Callable:
        return fn

    return decorator


def agent_model(
    key: str,
    label: str,
    description: str = "",
) -> Callable:
    """Expose an agent model selection for editing.

    Args:
        key: Unique identifier (e.g. ``"config.model"``).
        label: Human-readable label.
        description: Help text (optional).

    Returns:
        A decorator that validates the key and returns the function unchanged.

    Raises:
        AgentDecoratorError: If the key is empty or whitespace-only.

    Example::

        @agent_model(
            key="config.model",
            label="LLM Model",
            description="The language model powering this agent",
        )
        def get_model_name() -> str:
            return "sap/gpt-4o"
    """
    _validate_key(key)

    def decorator(fn: Callable) -> Callable:
        return fn

    return decorator
