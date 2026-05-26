"""Unit tests for OData v4 $batch builder and response parser."""

import json
import pytest

from sap_cloud_sdk.core.http._batch import (
    ODataBatchBuilder,
    ODataBatchResponse,
    ODataBatchPart,
    _build_path,
    _extract_boundary,
)


class TestODataBatchBuilderBuild:
    def test_build_returns_tuple(self):
        builder = ODataBatchBuilder()
        ct, body = builder.build()
        assert isinstance(ct, str)
        assert isinstance(body, str)

    def test_content_type_contains_boundary(self):
        builder = ODataBatchBuilder(boundary="batch_test123")
        ct, _ = builder.build()
        assert ct == "multipart/mixed; boundary=batch_test123"

    def test_custom_boundary(self):
        builder = ODataBatchBuilder(boundary="my-boundary")
        ct, body = builder.build()
        assert "my-boundary" in ct
        assert "--my-boundary--" in body

    def test_empty_batch_has_closing_delimiter(self):
        builder = ODataBatchBuilder(boundary="b1")
        _, body = builder.build()
        assert "--b1--" in body


class TestODataBatchBuilderGet:
    def test_add_get_produces_get_part(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_get("Documents")
        _, body = builder.build()
        assert "GET Documents HTTP/1.1" in body

    def test_add_get_with_params(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_get("Documents", params={"$top": "5", "$select": "ID"})
        _, body = builder.build()
        assert "GET Documents?" in body
        assert "$top=5" in body

    def test_add_get_inside_changeset_raises(self):
        builder = ODataBatchBuilder()
        builder.begin_change_set()
        with pytest.raises(RuntimeError, match="change set"):
            builder.add_get("Documents")

    def test_add_multiple_gets(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_get("Documents").add_get("DocumentRelations")
        _, body = builder.build()
        assert body.count("GET Documents HTTP/1.1") == 1
        assert body.count("GET DocumentRelations HTTP/1.1") == 1

    def test_chaining_returns_self(self):
        builder = ODataBatchBuilder()
        result = builder.add_get("Documents")
        assert result is builder


class TestODataBatchBuilderPost:
    def test_add_post_produces_post_part(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_post("DocumentRelations", body={"ID": "abc"})
        _, body = builder.build()
        assert "POST DocumentRelations HTTP/1.1" in body
        assert '"ID": "abc"' in body

    def test_add_post_outside_changeset(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_post("Items", body={"x": 1})
        _, body = builder.build()
        assert "POST Items HTTP/1.1" in body


class TestODataBatchBuilderPatchDelete:
    def test_add_patch(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_patch("Items('1')", body={"name": "new"})
        _, body = builder.build()
        assert "PATCH Items('1') HTTP/1.1" in body

    def test_add_delete(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_delete("Items('1')")
        _, body = builder.build()
        assert "DELETE Items('1') HTTP/1.1" in body

    def test_add_put(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.add_put("Items('1')", body={"full": "body"})
        _, body = builder.build()
        assert "PUT Items('1') HTTP/1.1" in body


class TestODataBatchBuilderChangeSet:
    def test_changeset_wrapped_in_multipart(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.begin_change_set("cs1")
        builder.add_post("Items", body={"x": 1})
        builder.end_change_set()
        _, body = builder.build()
        assert "multipart/mixed; boundary=cs1" in body
        assert "--cs1" in body

    def test_begin_twice_raises(self):
        builder = ODataBatchBuilder()
        builder.begin_change_set()
        with pytest.raises(RuntimeError, match="already open"):
            builder.begin_change_set()

    def test_end_without_begin_raises(self):
        builder = ODataBatchBuilder()
        with pytest.raises(RuntimeError, match="No change set"):
            builder.end_change_set()

    def test_build_with_open_changeset_raises(self):
        builder = ODataBatchBuilder()
        builder.begin_change_set()
        with pytest.raises(RuntimeError, match="Unclosed"):
            builder.build()

    def test_changeset_write_operations(self):
        builder = ODataBatchBuilder(boundary="b")
        builder.begin_change_set("cs")
        builder.add_post("Items", body={"k": "v"})
        builder.add_patch("Items('1')", body={"k2": "v2"})
        builder.add_delete("Items('2')")
        builder.end_change_set()
        _, body = builder.build()
        assert "POST Items HTTP/1.1" in body
        assert "PATCH Items('1') HTTP/1.1" in body
        assert "DELETE Items('2') HTTP/1.1" in body


class TestODataBatchPartOk:
    def test_ok_true_for_2xx(self):
        part = ODataBatchPart(status=200, headers={}, body=None)
        assert part.ok is True
        part2 = ODataBatchPart(status=201, headers={}, body=None)
        assert part2.ok is True

    def test_ok_false_for_4xx(self):
        part = ODataBatchPart(status=404, headers={}, body=None)
        assert part.ok is False

    def test_ok_false_for_5xx(self):
        part = ODataBatchPart(status=500, headers={}, body=None)
        assert part.ok is False


class TestODataBatchResponseParse:
    def _make_batch_response(self, status: int, body_dict: dict | None = None) -> tuple[str, str]:
        """Build a minimal OData batch response string for testing."""
        boundary = "batchresp_1"
        body_json = json.dumps(body_dict) if body_dict else ""
        response_body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/http\r\n"
            f"\r\n"
            f"HTTP/1.1 {status} {'OK' if status < 400 else 'Error'}\r\n"
            f"Content-Type: application/json\r\n"
            f"\r\n"
            f"{body_json}\r\n"
            f"--{boundary}--"
        )
        content_type = f"multipart/mixed; boundary={boundary}"
        return content_type, response_body

    def test_parse_single_200_part(self):
        ct, body = self._make_batch_response(200, {"value": [{"ID": "abc"}]})
        resp = ODataBatchResponse.parse(ct, body)
        assert len(resp) == 1
        assert resp.parts[0].status == 200
        assert resp.parts[0].ok is True

    def test_parse_json_body(self):
        ct, body = self._make_batch_response(201, {"ID": "new-id"})
        resp = ODataBatchResponse.parse(ct, body)
        assert resp.parts[0].body == {"ID": "new-id"}

    def test_parse_404_part(self):
        ct, body = self._make_batch_response(404)
        resp = ODataBatchResponse.parse(ct, body)
        assert resp.parts[0].status == 404
        assert not resp.parts[0].ok

    def test_missing_boundary_raises(self):
        with pytest.raises(ValueError, match="boundary"):
            ODataBatchResponse.parse("multipart/mixed", "--nobound--")

    def test_empty_batch_response(self):
        boundary = "b"
        ct = f"multipart/mixed; boundary={boundary}"
        body = f"--{boundary}--"
        resp = ODataBatchResponse.parse(ct, body)
        assert len(resp) == 0

    def test_iteration(self):
        ct, body = self._make_batch_response(200, {"id": 1})
        resp = ODataBatchResponse.parse(ct, body)
        parts = list(resp)
        assert len(parts) == 1


class TestBuildPath:
    def test_no_params(self):
        assert _build_path("Documents", None) == "Documents"

    def test_with_params(self):
        result = _build_path("Documents", {"$top": "5"})
        assert result == "Documents?$top=5"

    def test_empty_params(self):
        assert _build_path("Documents", {}) == "Documents"


class TestExtractBoundary:
    def test_simple_boundary(self):
        assert _extract_boundary("multipart/mixed; boundary=batch_abc") == "batch_abc"

    def test_quoted_boundary(self):
        assert _extract_boundary('multipart/mixed; boundary="batch xyz"') == "batch xyz"

    def test_no_boundary_raises(self):
        with pytest.raises(ValueError, match="boundary"):
            _extract_boundary("multipart/mixed")
