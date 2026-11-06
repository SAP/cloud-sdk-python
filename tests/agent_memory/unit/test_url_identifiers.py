"""Regression tests for Agent Memory entity-key URL encoding."""

import json
from unittest.mock import Mock, patch

import pytest
from requests import Response, Session

from sap_cloud_sdk.agent_memory.client import AgentMemoryClient
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryHttpError
from sap_cloud_sdk.core.protocol.http import AuthProvider, HttpClient


ENTITY_ID = "4056bb6c-f544-41d7-87e1-ffe818573e6e"
OPERATIONS = [
    ("get_memory", "GET", "memories"),
    ("update_memory", "PATCH", "memories"),
    ("delete_memory", "DELETE", "memories"),
    ("get_message", "GET", "messages"),
    ("delete_message", "DELETE", "messages"),
]


def _response():
    response = Response()
    response.status_code = 200
    response._content = json.dumps(
        {
            "id": ENTITY_ID,
            "agentID": "agent",
            "invokerID": "invoker",
            "content": "memory",
            "messageGroup": "group",
            "role": "USER",
        }
    ).encode()
    return response


@pytest.mark.parametrize("operation,method,entity", OPERATIONS)
@pytest.mark.parametrize(
    "identifier,encoded",
    [
        (
            "x)/../OtherEntity?injected=yes#fragment",
            "x%29%2F..%2FOtherEntity%3Finjected%3Dyes%23fragment",
        ),
        ("%29%2F%2e%2e%2Fother", "%2529%252F%252e%252e%252Fother"),
    ],
)
def test_prepared_urls_contain_ids_without_changing_odata_syntax(
    operation, method, entity, identifier, encoded
):
    with Session() as session:
        auth = Mock(spec=AuthProvider)
        auth.get_session.return_value = session
        http = HttpClient("https://memory.example.invalid/agent-memory", auth)
        client = AgentMemoryClient(http, tenant="subscriber")
        kwargs = {"content": "updated"} if operation == "update_memory" else {}
        with patch.object(session, "send", return_value=_response()) as send:
            getattr(client, operation)(identifier, **kwargs)

        prepared = send.call_args.args[0]
        assert prepared.method == method
        assert (
            prepared.url
            == f"https://memory.example.invalid/agent-memory/v1/{entity}({encoded})"
        )
        if operation == "update_memory":
            assert json.loads(prepared.body) == {"content": "updated"}
        else:
            assert prepared.body is None


def test_uuid_spelling_is_preserved():
    identifier = ENTITY_ID.upper()
    http = Mock(spec=HttpClient)
    http.request.return_value = _response()
    client = AgentMemoryClient(http, tenant="subscriber")

    client.get_memory(identifier)

    assert http.request.call_args.args[1] == f"/v1/memories({identifier})"


def test_dot_values_remain_inside_odata_keys():
    http = Mock(spec=HttpClient)
    http.request.return_value = _response()
    client = AgentMemoryClient(http, tenant="subscriber")

    client.delete_memory("..")

    assert http.request.call_args.args[1] == "/v1/memories(..)"


def test_unencodable_ids_raise_the_existing_http_exception():
    http = Mock(spec=HttpClient)
    client = AgentMemoryClient(http, tenant="subscriber")
    with pytest.raises(AgentMemoryHttpError) as error:
        client.delete_memory("\ud800")
    assert isinstance(error.value.__cause__, UnicodeEncodeError)
    http.request.assert_not_called()
