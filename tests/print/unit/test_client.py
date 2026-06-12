"""Unit tests for PrintClient."""

import pytest
from unittest.mock import MagicMock
from requests import Response

from sap_cloud_sdk.print.client import PrintClient
from sap_cloud_sdk.print._models import PrintContent, PrintProfile, PrintQueue, PrintTask
from sap_cloud_sdk.print.exceptions import HttpError, PrintOperationError


def _mock_response(status_code: int, json_data=None, text: str = "") -> Response:
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.text = text
    return resp


class TestListQueues:

    def test_returns_queue_list(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(
            200,
            json_data=[
                {"qname": "q1", "qdescription": "Queue 1", "cleanupPrd": 3},
                {"qname": "q2", "qdescription": "Queue 2", "cleanupPrd": 1},
            ],
        )

        client = PrintClient(mock_http)
        queues = client.list_queues()

        assert len(queues) == 2
        assert all(isinstance(q, PrintQueue) for q in queues)
        assert queues[0].qname == "q1"
        assert queues[1].qname == "q2"

    def test_returns_empty_list(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(200, json_data=[])

        client = PrintClient(mock_http)
        assert client.list_queues() == []

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("server error", status_code=500)

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to list queues"):
            client.list_queues()

    def test_parse_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(200, json_data="not-a-list")

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to parse list queues response"):
            client.list_queues()


class TestCreateQueue:

    def test_creates_queue_successfully(self):
        mock_http = MagicMock()
        mock_http.put.return_value = _mock_response(204)

        queue = PrintQueue(qname="my-queue", qdescription="Test", cleanup_prd=2)
        client = PrintClient(mock_http)
        client.create_queue(queue)

        args, kwargs = mock_http.put.call_args
        assert "my-queue" in args[0]
        assert kwargs["json"]["qname"] == "my-queue"
        assert kwargs["headers"]["If-None-Match"] == "*"

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.put.side_effect = HttpError("conflict", status_code=412)

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to create queue 'bad-q'"):
            client.create_queue(PrintQueue(qname="bad-q"))


class TestGetPrintProfiles:

    def test_returns_profile_list(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(
            200,
            json_data=[
                {"queueName": "q1", "profileName": "default", "profileStatus": "OK"},
            ],
        )

        client = PrintClient(mock_http)
        profiles = client.get_print_profiles("q1")

        assert len(profiles) == 1
        assert isinstance(profiles[0], PrintProfile)
        assert profiles[0].profile_name == "default"
        assert profiles[0].profile_status == "OK"

    def test_correct_path_used(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(200, json_data=[])

        client = PrintClient(mock_http)
        client.get_print_profiles("q1")

        args, _ = mock_http.get.call_args
        assert "q1/profiles" in args[0]

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("not found", status_code=400)

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to get profiles"):
            client.get_print_profiles("no-queue")

    def test_parse_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.get.return_value = _mock_response(200, json_data="not-a-list")

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to parse get profiles response"):
            client.get_print_profiles("q1")


class TestUploadDocument:

    def test_returns_document_id(self):
        mock_http = MagicMock()
        doc_id = "4056bb6c-f544-41d7-87e1-ffe818573e6e"
        mock_http.post.return_value = _mock_response(201, text=doc_id + "\n")

        client = PrintClient(mock_http)
        result = client.upload_document(b"PDF content", filename="invoice.pdf")

        assert result == doc_id

    def test_scan_header_passed(self):
        mock_http = MagicMock()
        mock_http.post.return_value = _mock_response(
            201, text="some-id"
        )

        client = PrintClient(mock_http)
        client.upload_document(b"data", scan=False)

        _, kwargs = mock_http.post.call_args
        assert kwargs["headers"]["scan"] == "false"

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = HttpError("too large", status_code=413)

        client = PrintClient(mock_http)
        with pytest.raises(PrintOperationError, match="failed to upload document"):
            client.upload_document(b"data")


class TestCreatePrintTask:

    def test_creates_task_successfully(self):
        mock_http = MagicMock()
        mock_http.put.return_value = _mock_response(204)

        task = PrintTask(
            item_id="doc-id-1",
            qname="q1",
            print_contents=[
                PrintContent(object_key="doc-id-1", document_name="main.pdf")
            ],
            number_of_copies=2,
            username="user@example.com",
        )
        client = PrintClient(mock_http)
        client.create_print_task(task)

        args, kwargs = mock_http.put.call_args
        assert "doc-id-1" in args[0]
        body = kwargs["json"]
        assert body["qname"] == "q1"
        assert body["numberOfCopies"] == 2
        assert body["username"] == "user@example.com"
        assert len(body["printContents"]) == 1
        assert kwargs["headers"]["If-None-Match"] == "*"

    def test_optional_profile_name_included(self):
        mock_http = MagicMock()
        mock_http.put.return_value = _mock_response(204)

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            profile_name="custom-profile",
        )
        client = PrintClient(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.put.call_args
        assert kwargs["json"]["profileName"] == "custom-profile"

    def test_username_auto_resolved_when_empty(self):
        mock_http = MagicMock()
        mock_http.put.return_value = _mock_response(204)
        mock_http.get_username.return_value = "auto@example.com"

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
        )
        client = PrintClient(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.put.call_args
        assert kwargs["json"]["username"] == "auto@example.com"
        assert task.username == "auto@example.com"

    def test_username_not_overwritten_when_provided(self):
        mock_http = MagicMock()
        mock_http.put.return_value = _mock_response(204)
        mock_http.get_username.return_value = "auto@example.com"

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            username="explicit@example.com",
        )
        client = PrintClient(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.put.call_args
        assert kwargs["json"]["username"] == "explicit@example.com"
        mock_http.get_username.assert_not_called()

    def test_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.put.side_effect = HttpError("rate limited", status_code=429)

        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
        )
        client = PrintClient(mock_http)
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
        mock_http.put.return_value = _mock_response(204)

        meta = PrintTaskMetadata(version=1.0, business_user="user@example.com")
        task = PrintTask(
            item_id="doc-id",
            qname="q1",
            print_contents=[PrintContent(object_key="doc-id", document_name="f.pdf")],
            username="user@example.com",
            metadata=meta,
        )
        client = PrintClient(mock_http)
        client.create_print_task(task)

        _, kwargs = mock_http.put.call_args
        assert "metadata" in kwargs["json"]
        assert kwargs["json"]["metadata"]["version"] == 1.0
