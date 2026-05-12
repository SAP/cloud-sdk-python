"""Tests for decorator functionality."""

import pytest

from sap_cloud_sdk.agent_decorators.decorators import (
    agent_config,
    agent_model,
    prompt_section,
)
from sap_cloud_sdk.agent_decorators.exceptions import AgentDecoratorError


class TestPromptSection:
    """Tests for @prompt_section decorator."""

    def test_function_still_callable(self):
        @prompt_section(
            key="prompts.system",
            label="System Prompt",
            description="Main system prompt",
        )
        def system_prompt():
            return "You are a helpful assistant."

        assert system_prompt() == "You are a helpful assistant."

    def test_with_validation_dict(self):
        @prompt_section(
            key="prompts.validated",
            label="Validated",
            description="A validated prompt",
            validation={"format": "text", "max_length": 500},
        )
        def validated():
            return "Hello"

        assert validated() == "Hello"


class TestAgentConfig:
    """Tests for @agent_config decorator."""

    def test_function_still_callable(self):
        @agent_config(
            key="config.temperature",
            label="Temperature",
            description="Model temperature",
        )
        def temperature():
            return 0.7

        assert temperature() == 0.7


class TestAgentModel:
    """Tests for @agent_model decorator."""

    def test_function_still_callable(self):
        @agent_model(key="config.model", label="Model")
        def model():
            return "gpt-4"

        assert model() == "gpt-4"

    def test_no_description_required(self):
        @agent_model(key="config.model2", label="Model")
        def model():
            return "claude-3"

        assert model() == "claude-3"

class TestKeyValidation:
    """Tests for decorator key validation."""

    def test_empty_key_raises_error(self):
        with pytest.raises(AgentDecoratorError, match="non-empty string"):

            @prompt_section(key="", label="L", description="D")
            def bad():
                return ""

    def test_whitespace_key_raises_error(self):
        with pytest.raises(AgentDecoratorError, match="non-empty string"):

            @agent_config(key="   ", label="L", description="D")
            def bad():
                return {}

    def test_none_key_raises_error(self):
        with pytest.raises(AgentDecoratorError, match="non-empty string"):

            @agent_model(key=None, label="L")  # ty: ignore[invalid-argument-type]
            def bad():
                return {}

    def test_valid_key_does_not_raise(self):
        @agent_model(key="valid_key", label="L")
        def good():
            return "model"

        assert good() == "model"

    def test_all_decorators_validate_key(self):
        decorators = [
            lambda fn: prompt_section(key="", label="L", description="D")(fn),
            lambda fn: agent_config(key="", label="L", description="D")(fn),
            lambda fn: agent_model(key="", label="L")(fn),
        ]

        for dec in decorators:
            with pytest.raises(AgentDecoratorError):
                dec(lambda: None)
