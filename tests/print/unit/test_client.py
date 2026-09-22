"""Unit tests for PrintClient."""

import base64
import json
import pytest
from unittest.mock import MagicMock
from requests import Response
from requests.exceptions import RequestException

from sap_cloud_sdk.print.client import PrintClient, _resolve_username
from sap_cloud_sdk.print._models import PrintContent, PrintProfile, PrintQueue, PrintTask
from sap_cloud_sdk.print.exceptions import HttpError, PrintOperationError
from sap_cloud_sdk.print.config import PrintConfig


def _mock_response(status_code: int, json_data=None, text: str = "") -> Response:
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.text = text
    return resp


def _make_jwt(claims: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}."


def _make_config() -> PrintConfig:
    return PrintConfig(
        url="https://api.eu10.print.services.sap",
        token_url="https://tenant.authentication.eu10.hana.ondemand.com/oauth/token",
        client_id="client-id",
        client_secret="client-secret",
    )


def _make_client(mock_http=None, mock_auth=None, config=None) -> PrintClient:
    if mock_http is None:
        mock_http = MagicMock()
    if mock_auth is None:
        mock_auth = MagicMock()
    cfg = config or _make_config()
    return PrintClient(http=mock_http, auth_provider=mock_auth, config_factory=lambda: cfg)


class TestListQueues:

    def test_returns_queue_list(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(
            200,
            json_data=[
                {"qname": "q1", "qdescription": "Queue 1", "cleanupPrd": 3},
                {"qname": "q2", "qdescription": "Queue 2", "cleanupPrd": 1},
            ],
        )

        client = _make_client(mock_http)
        queues = client.list_queues()

        assert len(queues) == 2
        assert all(isinstance(q, PrintQueue) for q in queues)
        assert queues[0].qname == "q1"
        assert queues[1].qname == "q2"

    def test_returns_empty_list(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(200, json_data=[])

        client = _make_client(mock_http)
        assert client.list_queues() == []

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(500, text="server error")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to list queues"):
            client.list_queues()

    def test_parse_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(200, json_data="not-a-list")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to parse list queues response"):
            client.list_queues()

    def test_request_exception_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.side_effect = RequestException("connection refused")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to list queues"):
            client.list_queues()


class TestCreateQueue:

    def test_creates_queue_successfully(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)

        queue = PrintQueue(qname="my-queue", qdescription="Test", cleanup_prd=2)
        client = _make_client(mock_http)
        client.create_queue(queue)

        args, kwargs = mock_http.request.call_args
        assert args[0] == "PUT"
        assert "my-queue" in args[1]
        assert kwargs["json"]["qname"] == "my-queue"
        assert kwargs["headers"]["If-None-Match"] == "*"

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(412, text="conflict")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to create queue 'bad-q'"):
            client.create_queue(PrintQueue(qname="bad-q"))


class TestGetPrintProfiles:

    def test_returns_profile_list(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(
            200,
            json_data=[
                {"queueName": "q1", "profileName": "default", "profileStatus": "OK"},
            ],
        )

        client = _make_client(mock_http)
        profiles = client.get_print_profiles("q1")

        assert len(profiles) == 1
        assert isinstance(profiles[0], PrintProfile)
        assert profiles[0].profile_name == "default"
        assert profiles[0].profile_status == "OK"

    def test_correct_path_used(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(200, json_data=[])

        client = _make_client(mock_http)
        client.get_print_profiles("q1")

        args, _ = mock_http.request.call_args
        assert "q1/profiles" in args[1]

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(404, text="not found")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to get profiles"):
            client.get_print_profiles("no-queue")

    def test_parse_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(200, json_data="not-a-list")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to parse get profiles response"):
            client.get_print_profiles("q1")


class TestUploadDocument:

    def test_returns_document_id(self):
        mock_http = MagicMock()
        doc_id = "4056bb6c-f544-41d7-87e1-ffe818573e6e"
        mock_http.request.return_value = _mock_response(201, text=doc_id + "\n")

        client = _make_client(mock_http)
        result = client.upload_document(b"PDF content", filename="invoice.pdf")

        assert result == doc_id

    def test_scan_header_passed(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(201, text="some-id")

        client = _make_client(mock_http)
        client.upload_document(b"data", scan=False)

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["scan"] == "false"

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(413, text="too large")

        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to upload document"):
            client.upload_document(b"data")


class TestCreatePrintTask:

    def test_creates_task_successfully(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)

        task = PrintTask(
            item_id="doc-id-1",
            qname="q1",
            print_contents=[
                PrintContent(object_key="doc-id-1", document_name="main.pdf")
            ],
            number_of_copies=2,
            username="user@example.com",
        )
        client = _make_client(mock_http)
        client.create_print_task(task)

        args, kwargs = mock_http.request.call_args
        assert args[0] == "PUT"
        assert "doc-id-1" in args[1]
        body = kwargs["json"]
        assert body["qname"] == "q1"
        assert body["numberOfCopies"] == 2
        assert body["username"] == "user@example.com"
        assert len(body["printContents"]) == 1
        assert kwargs["headers"]["If-None-Match"] == "*"

    def test_optional_profile_name_included(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            profile_name="custom-profile",
        )
        client = _make_client(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["profileName"] == "custom-profile"

    def test_username_auto_resolved_when_empty(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)
        mock_auth = MagicMock()
        mock_auth.get_session.return_value.access_token = _make_jwt({"user_name": "auto@example.com"})

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
        )
        client = _make_client(mock_http, mock_auth)
        client.create_print_task(task)

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["username"] == "auto@example.com"
        assert task.username == "auto@example.com"

    def test_username_not_overwritten_when_provided(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)
        mock_auth = MagicMock()

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            username="explicit@example.com",
        )
        client = _make_client(mock_http, mock_auth)
        client.create_print_task(task)

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["username"] == "explicit@example.com"
        mock_auth.get_session.assert_not_called()

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(429, text="rate limited")

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
        )
        client = _make_client(mock_http)
        with pytest.raises(PrintOperationError, match="failed to create print task"):
            client.create_print_task(task)


class TestPrintTaskMetadata:

    def test_to_dict_includes_all_fields(self):
        from sap_cloud_sdk.print._models import PrintTaskMetadata
        meta = PrintTaskMetadata(version=1.0, business_user="user@example.com", object_node_type="Invoice")
        result = meta.to_dict()
        assert result["version"] == 1.0
        assert result["business_metadata"]["business_user"] == "user@example.com"
        assert result["business_metadata"]["object_node_type"] == "Invoice"

    def test_create_print_task_body_includes_metadata(self):
        from sap_cloud_sdk.print._models import PrintTaskMetadata
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(204)

        meta = PrintTaskMetadata(version=1.0, business_user="user@example.com")
        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            username="user@example.com",
            metadata=meta,
        )
        client = _make_client(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.request.call_args
        assert "metadata" in kwargs["json"]
        assert kwargs["json"]["metadata"]["version"] == 1.0


class TestResolveUsername:

    def test_returns_user_name_claim(self):
        token = _make_jwt({"user_name": "john@example.com", "client_id": "sb-app"})
        assert _resolve_username(token, "fallback") == "john@example.com"

    def test_falls_back_to_client_id_claim(self):
        token = _make_jwt({"client_id": "sb-app!t123"})
        assert _resolve_username(token, "fallback") == "sb-app!t123"

    def test_falls_back_to_fallback_client_id_on_bad_token(self):
        assert _resolve_username("not.a.jwt", "my-client-id") == "my-client-id"

    def test_falls_back_to_fallback_client_id_on_empty_token(self):
        assert _resolve_username("", "my-client-id") == "my-client-id"
