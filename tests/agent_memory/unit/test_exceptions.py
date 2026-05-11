import pytest

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryConfigError,
    AgentMemoryError,
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
)


class TestAgentMemoryError:

    def test_is_base_exception(self):
        assert issubclass(AgentMemoryError, Exception)

    def test_message(self):
        exc = AgentMemoryError("base error")
        assert str(exc) == "base error"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(AgentMemoryError, match="test error"):
            raise AgentMemoryError("test error")


class TestAgentMemoryConfigError:

    def test_is_agent_memory_error(self):
        assert issubclass(AgentMemoryConfigError, AgentMemoryError)

    def test_message(self):
        exc = AgentMemoryConfigError("missing base_url")
        assert str(exc) == "missing base_url"

    def test_caught_as_base_error(self):
        with pytest.raises(AgentMemoryError):
            raise AgentMemoryConfigError("config problem")


class TestAgentMemoryHttpError:

    def test_is_agent_memory_error(self):
        assert issubclass(AgentMemoryHttpError, AgentMemoryError)

    def test_message(self):
        exc = AgentMemoryHttpError("request failed")
        assert str(exc) == "request failed"

    def test_status_code_defaults_to_none(self):
        exc = AgentMemoryHttpError("error")
        assert exc.status_code is None

    def test_response_text_defaults_to_none(self):
        exc = AgentMemoryHttpError("error")
        assert exc.response_text is None

    def test_status_code_is_set(self):
        exc = AgentMemoryHttpError("error", status_code=500)
        assert exc.status_code == 500

    def test_response_text_is_set(self):
        exc = AgentMemoryHttpError("error", response_text="Internal Server Error")
        assert exc.response_text == "Internal Server Error"

    def test_both_attrs_set(self):
        exc = AgentMemoryHttpError("error", status_code=422, response_text="Bad input")
        assert exc.status_code == 422
        assert exc.response_text == "Bad input"

    def test_caught_as_base_error(self):
        with pytest.raises(AgentMemoryError):
            raise AgentMemoryHttpError("http failure", status_code=503)


class TestAgentMemoryNotFoundError:

    def test_is_http_error(self):
        assert issubclass(AgentMemoryNotFoundError, AgentMemoryHttpError)

    def test_is_agent_memory_error(self):
        assert issubclass(AgentMemoryNotFoundError, AgentMemoryError)

    def test_message_and_status_code(self):
        exc = AgentMemoryNotFoundError("not found", status_code=404)
        assert str(exc) == "not found"
        assert exc.status_code == 404

    def test_caught_as_http_error(self):
        with pytest.raises(AgentMemoryHttpError):
            raise AgentMemoryNotFoundError("not found", status_code=404)

    def test_caught_as_base_error(self):
        with pytest.raises(AgentMemoryError):
            raise AgentMemoryNotFoundError("not found")
