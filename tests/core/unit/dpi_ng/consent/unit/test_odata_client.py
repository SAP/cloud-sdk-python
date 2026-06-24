"""Unit tests for client.py — _ODataClient._raise_for_status, call_action, context manager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.core.dpi_ng.consent.auth import AuthProvider
from sap_cloud_sdk.core.dpi_ng.consent.client import _ODataClient
from sap_cloud_sdk.core.dpi_ng.consent.config import ConsentSDKConfig
from sap_cloud_sdk.core.dpi_ng.consent.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ODataError,
    ValidationError,
)


def _mock_response(status_code, json_body=None, text="", content=b"body"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


def _make_config():
    auth = MagicMock(spec=AuthProvider)
    return ConsentSDKConfig(base_url="https://consent.example.com", auth=auth)


class TestRaiseForStatus:
    def test_200_does_not_raise(self):
        resp = _mock_response(200, json_body={}, text="ok", content=b"ok")
        _ODataClient._raise_for_status(resp)

    def test_401_raises_authentication_error(self):
        resp = _mock_response(
            401,
            json_body={"error": {"message": "Unauthorized"}},
            text="Unauthorized",
        )
        with pytest.raises(AuthenticationError, match="Unauthorized"):
            _ODataClient._raise_for_status(resp)

    def test_403_raises_authorization_error(self):
        resp = _mock_response(
            403,
            json_body={"error": {"message": "Forbidden"}},
            text="Forbidden",
        )
        with pytest.raises(AuthorizationError, match="Forbidden"):
            _ODataClient._raise_for_status(resp)

    def test_404_raises_not_found_error(self):
        resp = _mock_response(
            404,
            json_body={"error": {"message": "Not Found"}},
            text="Not Found",
        )
        with pytest.raises(NotFoundError, match="Not Found"):
            _ODataClient._raise_for_status(resp)

    def test_409_raises_conflict_error(self):
        resp = _mock_response(
            409,
            json_body={"error": {"message": "Conflict"}},
            text="Conflict",
        )
        with pytest.raises(ConflictError, match="Conflict"):
            _ODataClient._raise_for_status(resp)

    def test_400_raises_validation_error(self):
        resp = _mock_response(
            400,
            json_body={"error": {"message": "Bad Request"}},
            text="Bad Request",
        )
        with pytest.raises(ValidationError, match="Bad Request"):
            _ODataClient._raise_for_status(resp)

    def test_422_raises_validation_error(self):
        resp = _mock_response(
            422,
            json_body={"error": {"message": "Unprocessable"}},
            text="Unprocessable",
        )
        with pytest.raises(ValidationError, match="Unprocessable"):
            _ODataClient._raise_for_status(resp)

    def test_500_raises_odata_error_with_status_code(self):
        resp = _mock_response(
            500,
            json_body={"error": {"message": "Server Error"}},
            text="Server Error",
        )
        with pytest.raises(ODataError) as exc_info:
            _ODataClient._raise_for_status(resp)
        assert exc_info.value.status_code == 500

    def test_odata_error_message_extracted_from_body(self):
        resp = _mock_response(
            401,
            json_body={"error": {"message": "Token expired"}},
            text="raw text",
        )
        with pytest.raises(AuthenticationError, match="Token expired"):
            _ODataClient._raise_for_status(resp)

    def test_details_appended_to_message(self):
        resp = _mock_response(
            400,
            json_body={
                "error": {
                    "message": "Validation failed",
                    "details": [{"target": "name", "message": "too long"}],
                }
            },
            text="Validation failed",
        )
        with pytest.raises(ValidationError, match="name: too long"):
            _ODataClient._raise_for_status(resp)

    def test_non_json_body_falls_back_to_resp_text(self):
        resp = _mock_response(403, text="plain text error", content=b"plain text error")
        resp.json.side_effect = ValueError("not json")
        with pytest.raises(AuthorizationError, match="plain text error"):
            _ODataClient._raise_for_status(resp)

    def test_odata_error_stores_odata_error_dict(self):
        odata_payload = {"message": "Unauthorized", "code": "AUTH_001"}
        resp = _mock_response(
            401,
            json_body={"error": odata_payload},
            text="Unauthorized",
        )
        with pytest.raises(AuthenticationError) as exc_info:
            _ODataClient._raise_for_status(resp)
        assert exc_info.value.odata_error == odata_payload


@patch("sap_cloud_sdk.core.dpi_ng.consent.client.ODataService")
@patch("sap_cloud_sdk.core.dpi_ng.consent.client.requests.Session")
class TestCallAction:
    def test_returns_parsed_json_on_200(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_svc_instance = MagicMock()
        mock_svc_instance.url = "https://consent.example.com/sap/cp/kernel/dpi/consent/odata/v4/consentServices/"
        mock_odata_svc_cls.return_value = mock_svc_instance

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.content = b'{"value": "ok"}'
        post_resp.json.return_value = {"value": "ok"}
        mock_session.post.return_value = post_resp

        config = _make_config()
        client = _ODataClient(config)
        result = client.call_action("consentServices", "myAction", body={"key": "val"})

        assert result == {"value": "ok"}
        mock_session.post.assert_called_once()

    def test_returns_none_on_204(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_svc_instance = MagicMock()
        mock_svc_instance.url = "https://consent.example.com/sap/cp/kernel/dpi/consent/odata/v4/consentServices/"
        mock_odata_svc_cls.return_value = mock_svc_instance

        post_resp = MagicMock()
        post_resp.status_code = 204
        post_resp.content = b""
        mock_session.post.return_value = post_resp

        config = _make_config()
        client = _ODataClient(config)
        result = client.call_action("consentServices", "myAction")

        assert result is None

    def test_returns_none_on_empty_content(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_svc_instance = MagicMock()
        mock_svc_instance.url = "https://consent.example.com/sap/cp/kernel/dpi/consent/odata/v4/consentServices/"
        mock_odata_svc_cls.return_value = mock_svc_instance

        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.content = b""
        mock_session.post.return_value = post_resp

        config = _make_config()
        client = _ODataClient(config)
        result = client.call_action("consentServices", "myAction")

        assert result is None

    def test_raises_on_4xx(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_svc_instance = MagicMock()
        mock_svc_instance.url = "https://consent.example.com/sap/cp/kernel/dpi/consent/odata/v4/consentServices/"
        mock_odata_svc_cls.return_value = mock_svc_instance

        post_resp = MagicMock()
        post_resp.status_code = 404
        post_resp.content = b"Not Found"
        post_resp.text = "Not Found"
        post_resp.json.return_value = {"error": {"message": "Resource not found"}}
        mock_session.post.return_value = post_resp

        config = _make_config()
        client = _ODataClient(config)
        with pytest.raises(NotFoundError, match="Resource not found"):
            client.call_action("consentServices", "missingAction")


@patch("sap_cloud_sdk.core.dpi_ng.consent.client.ODataService")
@patch("sap_cloud_sdk.core.dpi_ng.consent.client.requests.Session")
class TestOrmMethods:
    def test_get_entity_classes_calls_factory_on_cache_miss(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        mock_svc = MagicMock()
        mock_odata_svc_cls.return_value = mock_svc
        mock_entities = (MagicMock(),)
        mock_factory = MagicMock(return_value=mock_entities)
        config = _make_config()
        client = _ODataClient(config)
        with patch.dict("sap_cloud_sdk.core.dpi_ng.consent.client._ENTITY_FACTORIES", {"testSvc": mock_factory}):
            result = client.get_entity_classes("testSvc")
        mock_factory.assert_called_once_with(mock_svc)
        assert result is mock_entities

    def test_get_entity_classes_returns_cached_on_second_call(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        mock_odata_svc_cls.return_value = MagicMock()
        mock_factory = MagicMock(return_value=(MagicMock(),))
        config = _make_config()
        client = _ODataClient(config)
        with patch.dict("sap_cloud_sdk.core.dpi_ng.consent.client._ENTITY_FACTORIES", {"testSvc": mock_factory}):
            client.get_entity_classes("testSvc")
            client.get_entity_classes("testSvc")
        mock_factory.assert_called_once()

    def test_query_delegates_to_odata_service(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        mock_svc = MagicMock()
        mock_odata_svc_cls.return_value = mock_svc
        entity_cls = MagicMock()
        config = _make_config()
        client = _ODataClient(config)
        result = client.query("consentServices", entity_cls)
        mock_svc.query.assert_called_once_with(entity_cls)
        assert result is mock_svc.query.return_value

    def test_save_delegates_to_entity_odata_service(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        mock_odata_svc_cls.return_value = MagicMock()
        entity = MagicMock()
        entity.__odata_service__ = MagicMock()
        config = _make_config()
        client = _ODataClient(config)
        client.save(entity)
        entity.__odata_service__.save.assert_called_once_with(entity)

    def test_delete_entity_delegates_to_entity_odata_service(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        mock_odata_svc_cls.return_value = MagicMock()
        entity = MagicMock()
        entity.__odata_service__ = MagicMock()
        config = _make_config()
        client = _ODataClient(config)
        client.delete_entity(entity)
        entity.__odata_service__.delete.assert_called_once_with(entity)


@patch("sap_cloud_sdk.core.dpi_ng.consent.client.ODataService")
@patch("sap_cloud_sdk.core.dpi_ng.consent.client.requests.Session")
class TestContextManager:
    def test_enter_returns_self(self, mock_session_cls, mock_odata_svc_cls):
        mock_session_cls.return_value = MagicMock()
        config = _make_config()
        client = _ODataClient(config)
        assert client.__enter__() is client

    def test_exit_calls_session_close(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        config = _make_config()
        client = _ODataClient(config)
        client.__exit__(None, None, None)
        mock_session.close.assert_called_once()

    def test_context_manager_closes_on_exit(self, mock_session_cls, mock_odata_svc_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        config = _make_config()
        with _ODataClient(config) as client:
            assert isinstance(client, _ODataClient)
        mock_session.close.assert_called_once()
