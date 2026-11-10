"""Regression tests for Print identifier URL encoding."""

import json
from unittest.mock import Mock, patch

import pytest
from requests import Response, Session

from sap_cloud_sdk.core.protocol.http import HttpClient, XsuaaAuthProvider
from sap_cloud_sdk.print._models import PrintContent, PrintQueue, PrintTask
from sap_cloud_sdk.print.client import PrintClient
from sap_cloud_sdk.print.exceptions import HttpError, PrintOperationError


BASE_URL = "https://print.example.invalid"
OPERATIONS = [
    ("create_queue", "PUT", "/qm/api/v1/rest/queues/{identifier}"),
    ("get_print_profiles", "GET", "/qm/api/v1/rest/queues/{identifier}/profiles"),
    ("create_print_task", "PUT", "/qm/api/v1/rest/print-tasks/{identifier}"),
]


def _task(identifier):
    return PrintTask(
        item_id=identifier,
        qname="queue",
        username="user",
        print_contents=[PrintContent(object_key=identifier, document_name="main.pdf")],
    )


def _invoke(client, operation, identifier):
    if operation == "create_queue":
        client.create_queue(PrintQueue(qname=identifier))
    elif operation == "get_print_profiles":
        client.get_print_profiles(identifier)
    else:
        client.create_print_task(_task(identifier))


@pytest.mark.parametrize("operation,method,path", OPERATIONS)
@pytest.mark.parametrize(
    "identifier,encoded",
    [
        ("../other?param=x#frag", "..%2Fother%3Fparam%3Dx%23frag"),
        ("%2e%2e%2fother", "%252e%252e%252fother"),
    ],
)
def test_prepared_urls_contain_identifiers_without_changing_bodies(
    operation, method, path, identifier, encoded
):
    with Session() as session:
        auth = Mock(spec=XsuaaAuthProvider)
        auth.base_url = BASE_URL
        auth.get_session.return_value = session
        client = PrintClient(HttpClient(BASE_URL, auth), auth, lambda: Mock())
        response = Response()
        response.status_code = 200
        response._content = b"[]"
        with patch.object(session, "send", return_value=response) as send:
            _invoke(client, operation, identifier)

        prepared = send.call_args.args[0]
        assert prepared.method == method
        assert prepared.url == BASE_URL + path.format(identifier=encoded)
        if operation != "get_print_profiles":
            body = json.loads(prepared.body)
            if operation == "create_queue":
                assert body["qname"] == identifier
            else:
                assert body["printContents"][0]["objectKey"] == identifier


@pytest.mark.parametrize("operation,method,path", OPERATIONS)
@pytest.mark.parametrize("identifier", [".", ".."])
def test_dot_segments_raise_existing_operation_error_without_http(
    operation, method, path, identifier
):
    http = Mock(spec=HttpClient)
    client = PrintClient(http, Mock(), lambda: Mock())
    with pytest.raises(PrintOperationError) as error:
        _invoke(client, operation, identifier)
    assert isinstance(error.value.__cause__, HttpError)
    http.request.assert_not_called()


def test_task_uuid_spelling_and_document_reference_are_preserved():
    identifier = "4056BB6C-F544-41D7-87E1-FFE818573E6E"
    http = Mock(spec=HttpClient)
    response = Response()
    response.status_code = 204
    http.request.return_value = response
    client = PrintClient(http, Mock(), lambda: Mock())
    task = _task(identifier)

    client.create_print_task(task)

    assert http.request.call_args.args[1] == f"/qm/api/v1/rest/print-tasks/{identifier}"
    assert (
        http.request.call_args.kwargs["json"]["printContents"][0]["objectKey"]
        == identifier
    )
    assert task.item_id == identifier
