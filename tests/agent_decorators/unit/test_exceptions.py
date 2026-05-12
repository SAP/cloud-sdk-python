"""Tests for agent decorator exception classes."""

from sap_cloud_sdk.agent_decorators.exceptions import (
    AgentDecoratorError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_base_error_is_exception(self):
        """Test that AgentDecoratorError inherits from Exception."""
        assert issubclass(AgentDecoratorError, Exception)


class TestExceptionInstantiation:
    """Tests for exception creation and message handling."""

    def test_base_error_with_message(self):
        """Test creating AgentDecoratorError with a message."""
        error = AgentDecoratorError("something went wrong")
        assert str(error) == "something went wrong"
