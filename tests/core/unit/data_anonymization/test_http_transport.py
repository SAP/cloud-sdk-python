"""Unit tests for the HTTP transport."""

import base64
from collections.abc import Mapping
from pathlib import Path
import importlib
import types
from unittest.mock import MagicMock

import sap_cloud_sdk.core.data_anonymization._http_transport as http_transport_module
from sap_cloud_sdk.core.data_anonymization._http_transport import HttpTransport
from sap_cloud_sdk.core.data_anonymization._transport import Transport
from sap_cloud_sdk.core.data_anonymization.config import DataAnonymizationConfig
from sap_cloud_sdk.core.data_anonymization.exceptions import (
    AuthenticationError,
    TransportError,
)
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeTextRequest,
    PseudonymizeFileRequest,
    PseudonymizeTextRequest,
)
from sap_cloud_sdk.destination._models import Authentication, Certificate, Destination


destination_module = importlib.import_module("sap_cloud_sdk.destination")

CLIENT_CERT_PEM = "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
CLIENT_KEY_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\nKEY\n-----END RSA PRIVATE KEY-----\n"
)
CLIENT_CERT_BASE64 = base64.b64encode(CLIENT_CERT_PEM.encode("utf-8")).decode("utf-8")
CLIENT_KEY_BASE64 = base64.b64encode(CLIENT_KEY_PEM.encode("utf-8")).decode("utf-8")


def assert_raises(exception_type, match, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception_type as error:
        assert match in str(error)
        return error
    raise AssertionError(f"Expected {exception_type.__name__} to be raised")


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data=...,
        text: str = "",
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers: Mapping[str, str] = headers or {}
        self.content = content

    def json(self):
        if self._json_data is ...:
            raise ValueError("not json")
        return self._json_data


def make_transport(
    monkeypatch,
    response: DummyResponse,
) -> tuple[HttpTransport, MagicMock]:
    session = MagicMock()
    session.post.return_value = response
    monkeypatch.setattr(
        HttpTransport,
        "_resolve_cert",
        lambda self: ("client.crt", "client.key"),
    )
    monkeypatch.setattr(
        HttpTransport,
        "_build_session",
        staticmethod(lambda cert: session),
    )

    transport = HttpTransport(
        DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )
    )
    return transport, session


class TestHttpTransport:
    def test_inherits_from_transport(self) -> None:
        assert issubclass(HttpTransport, Transport)

    def test_anonymize_text_posts_form_data(
        self,
        monkeypatch,
    ) -> None:
        response = DummyResponse(json_data={"result": "<person>"})
        transport, session = make_transport(monkeypatch, response)
        request = AnonymizeTextRequest(
            text="John Doe",
            entities=["profile-person"]
        )

        result = transport.anonymize_text(request)

        assert result.result == "<person>"
        session.post.assert_called_once_with(
            "https://service.example.com/anonymization/api/v1.0/unstructureddata/text",
            data=[("text", "John Doe"), ("entities", "profile-person")],
            timeout=30,
        )

    def test_pseudonymize_text_parses_metadata(
        self,
        monkeypatch,
    ) -> None:
        response = DummyResponse(
            json_data={
                "result": "TOKEN-1",
                "metadata": [
                    {
                        "original": "John Doe",
                        "pseudonym": "TOKEN-1",
                        "entity_type": "PERSON",
                    }
                ],
            }
        )
        transport, _ = make_transport(monkeypatch, response)

        result = transport.pseudonymize_text(PseudonymizeTextRequest(text="John Doe"))

        assert result.result == "TOKEN-1"
        assert result.metadata[0].original == "John Doe"

    def test_anonymize_file_posts_multipart_bytes(
        self,
        monkeypatch,
    ) -> None:
        response = DummyResponse(json_data={"job_id": "job-1"})
        transport, session = make_transport(monkeypatch, response)
        request = AnonymizeFileRequest(
            file_content=b"hello",
            file_name="sample.txt"
        )

        result = transport.anonymize_file(request)

        assert result.job_id == "job-1"
        session.post.assert_called_once_with(
            "https://service.example.com/anonymization/api/v1.0/unstructureddata/file",
            data=[],
            files={"file": ("sample.txt", b"hello")},
            timeout=30,
        )

    def test_pseudonymize_file_returns_binary_content(
        self,
        monkeypatch,
    ) -> None:
        response = DummyResponse(
            text="",
            headers={
                "Content-Type": "application/zip",
                "Content-Disposition": 'attachment; filename="result.zip"',
            },
            content=b"zip-bytes",
        )
        transport, _ = make_transport(monkeypatch, response)
        request = PseudonymizeFileRequest(
            file_content=b"{}",
            file_name="sample.json",
            pseudonymization_secret="12345678901234567890123456789012",
        )

        result = transport.pseudonymize_file(request)

        assert result.content == b"zip-bytes"
        assert result.filename == "result.zip"
        assert result.content_type == "application/zip"

    def test_anonymize_file_opens_file_path(
        self,
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        sample_file = tmp_path / "sample.txt"
        sample_file.write_text("hello", encoding="utf-8")
        response = DummyResponse(json_data={"result": "done"})
        transport, session = make_transport(monkeypatch, response)

        result = transport.anonymize_file(
            AnonymizeFileRequest(file_path=str(sample_file))
        )

        assert result.result == "done"
        files_arg = session.post.call_args.kwargs["files"]
        assert files_arg["file"][0] == "sample.txt"

    def test_raise_for_status_raises_transport_error(self) -> None:
        response = DummyResponse(status_code=400, text="bad request")

        assert_raises(
            TransportError,
            "returned 400",
            HttpTransport._raise_for_status,
            "https://service.example.com/test",
            response,
        )

    def test_resolve_cert_from_inline_config(self) -> None:
        transport = object.__new__(HttpTransport)
        transport._config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )
        transport._tmp_cert_file = None
        transport._tmp_key_file = None

        cert_path, key_path = transport._resolve_cert()

        assert Path(cert_path).exists()
        assert Path(key_path).exists()
        assert Path(cert_path).read_text(encoding="utf-8") == CLIENT_CERT_PEM
        assert Path(key_path).read_text(encoding="utf-8") == CLIENT_KEY_PEM

        transport._session = MagicMock()
        transport.close()

        assert not Path(cert_path).exists()
        assert not Path(key_path).exists()

    def test_resolve_cert_from_destination(
        self,
        monkeypatch,
    ) -> None:
        pem_bundle = (
            "-----BEGIN RSA PRIVATE KEY-----\nKEY\n-----END RSA PRIVATE KEY-----\n"
            "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
        )
        destination = Destination(
            name="anon-destination",
            type="HTTP",
            authentication=Authentication.CLIENT_CERTIFICATE_AUTHENTICATION,
            properties={"KeyStoreLocation": "keystore.pem"},
        )
        certificate = Certificate(name="keystore.pem", content=pem_bundle, type="PEM")
        destination_client = types.SimpleNamespace(
            get_instance_destination=lambda name: destination,
            get_subaccount_destination=lambda *args, **kwargs: None,
        )
        cert_client = types.SimpleNamespace(
            get_instance_certificate=lambda name: certificate
        )
        monkeypatch.setattr(
            destination_module,
            "create_client",
            lambda **_: destination_client,
        )
        monkeypatch.setattr(
            destination_module,
            "create_certificate_client",
            lambda **_: cert_client,
        )

        transport = object.__new__(HttpTransport)
        transport._config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            destination_name="anon-destination",
        )
        transport._tmp_cert_file = None
        transport._tmp_key_file = None

        cert_path = transport._resolve_cert()

        assert Path(cert_path).exists()
        assert "BEGIN RSA PRIVATE KEY" in Path(cert_path).read_text(encoding="utf-8")
        transport._session = MagicMock()
        transport.close()
        assert not Path(cert_path).exists()

    def test_resolve_cert_from_destination_with_base64_bundle(
        self,
        monkeypatch,
    ) -> None:
        pem_bundle = (
            "-----BEGIN RSA PRIVATE KEY-----\nKEY\n-----END RSA PRIVATE KEY-----\n"
            "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
        )
        destination = Destination(
            name="anon-destination",
            type="HTTP",
            authentication=Authentication.CLIENT_CERTIFICATE_AUTHENTICATION,
            properties={"KeyStoreLocation": "keystore.pem"},
        )
        certificate = Certificate(
            name="keystore.pem",
            content=base64.b64encode(pem_bundle.encode("utf-8")).decode("utf-8"),
            type="PEM",
        )
        destination_client = types.SimpleNamespace(
            get_instance_destination=lambda name: destination,
            get_subaccount_destination=lambda *args, **kwargs: None,
        )
        cert_client = types.SimpleNamespace(
            get_instance_certificate=lambda name: certificate
        )
        monkeypatch.setattr(destination_module, "create_client", lambda **_: destination_client)
        monkeypatch.setattr(
            destination_module,
            "create_certificate_client",
            lambda **_: cert_client,
        )

        transport = object.__new__(HttpTransport)
        transport._config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            destination_name="anon-destination",
        )
        transport._tmp_cert_file = None
        transport._tmp_key_file = None

        cert_path = transport._resolve_cert()

        assert Path(cert_path).exists()
        assert "BEGIN CERTIFICATE" in Path(cert_path).read_text(encoding="utf-8")
        transport._session = MagicMock()
        transport.close()

    def test_get_destination_keystore_location_requires_property(self) -> None:
        destination = Destination(name="anon", type="HTTP", properties={})

        assert_raises(
            AuthenticationError,
            "does not define KeyStoreLocation",
            HttpTransport._get_destination_keystore_location,
            destination,
            "anon",
        )

    def test_get_destination_keystore_location_requires_client_cert_auth(self) -> None:
        destination = Destination(
            name="anon",
            type="HTTP",
            authentication="NoAuthentication",
            properties={"KeyStoreLocation": "keystore.pem"},
        )

        assert_raises(
            AuthenticationError,
            "ClientCertificateAuthentication",
            HttpTransport._get_destination_keystore_location,
            destination,
            "anon",
        )

    def test_decode_destination_certificate_content_rejects_missing_key(self) -> None:
        pem_bundle = "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"

        assert_raises(
            AuthenticationError,
            "does not contain a private key",
            HttpTransport._decode_destination_certificate_content,
            pem_bundle,
        )

    def test_resolve_cert_without_config_raises(self) -> None:
        transport = object.__new__(HttpTransport)
        transport._config = types.SimpleNamespace(
            cert=None,
            key=None,
            cert_path=None,
            key_path=None,
            destination_name=None,
        )

        assert_raises(
            AuthenticationError,
            "No Key Store configured",
            transport._resolve_cert,
        )

    def test_network_error_is_wrapped(
        self,
        monkeypatch,
    ) -> None:
        requests_module = http_transport_module.requests
        response_error = requests_module.exceptions.ConnectionError("network down")
        session = MagicMock()
        session.post.side_effect = response_error
        monkeypatch.setattr(
            HttpTransport,
            "_resolve_cert",
            lambda self: ("client.crt", "client.key"),
        )
        monkeypatch.setattr(
            HttpTransport,
            "_build_session",
            staticmethod(lambda cert: session),
        )

        transport = HttpTransport(
            DataAnonymizationConfig(
                service_url="https://service.example.com",
                cert=CLIENT_CERT_BASE64,
                key=CLIENT_KEY_BASE64,
            )
        )

        assert_raises(
            TransportError,
            "Network error calling anonymize_text",
            transport.anonymize_text,
            AnonymizeTextRequest(text="hello"),
        )

    def test_anonymize_text_unexpected_error_is_wrapped(
        self,
        monkeypatch,
    ) -> None:
        session = MagicMock()
        session.post.side_effect = RuntimeError("boom")
        monkeypatch.setattr(
            HttpTransport,
            "_resolve_cert",
            lambda self: ("client.crt", "client.key"),
        )
        monkeypatch.setattr(
            HttpTransport,
            "_build_session",
            staticmethod(lambda cert: session),
        )

        transport = HttpTransport(
            DataAnonymizationConfig(
                service_url="https://service.example.com",
                cert=CLIENT_CERT_BASE64,
                key=CLIENT_KEY_BASE64,
            )
        )

        assert_raises(
            TransportError,
            "Unexpected error calling anonymize_text",
            transport.anonymize_text,
            AnonymizeTextRequest(text="hello"),
        )

    def test_pseudonymize_file_network_error_is_wrapped(
        self,
        monkeypatch,
    ) -> None:
        requests_module = http_transport_module.requests
        session = MagicMock()
        session.post.side_effect = requests_module.exceptions.ConnectionError(
            "network down"
        )
        monkeypatch.setattr(
            HttpTransport,
            "_resolve_cert",
            lambda self: ("client.crt", "client.key"),
        )
        monkeypatch.setattr(
            HttpTransport,
            "_build_session",
            staticmethod(lambda cert: session),
        )

        transport = HttpTransport(
            DataAnonymizationConfig(
                service_url="https://service.example.com",
                cert=CLIENT_CERT_BASE64,
                key=CLIENT_KEY_BASE64,
            )
        )

        request = PseudonymizeFileRequest(
            file_content=b"{}",
            file_name="sample.json",
            pseudonymization_secret="12345678901234567890123456789012",
        )

        assert_raises(
            TransportError,
            "Network error calling pseudonymize_file",
            transport.pseudonymize_file,
            request,
        )

    def test_resolve_cert_from_inline_config_rejects_invalid_base64(self) -> None:
        transport = object.__new__(HttpTransport)
        transport._config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert="not-base64",
            key=CLIENT_KEY_BASE64,
        )
        transport._tmp_cert_file = None
        transport._tmp_key_file = None

        assert_raises(
            AuthenticationError,
            "Client cert content is not valid base64-encoded PEM",
            transport._resolve_cert,
        )

    def test_parse_anonymize_text_result_from_string_payload(self, monkeypatch) -> None:
        response = DummyResponse(json_data="<person>")
        transport, _ = make_transport(monkeypatch, response)

        result = transport._parse_anonymize_text_result(response)

        assert result.result == "<person>"
        assert result.raw == {"result": "<person>"}

    def test_parse_pseudonymize_text_result_from_plain_text(self, monkeypatch) -> None:
        response = DummyResponse(json_data=..., text="TOKEN-1")
        transport, _ = make_transport(monkeypatch, response)

        result = transport._parse_pseudonymize_text_result(response)

        assert result.result == "TOKEN-1"
        assert result.raw == {"result": "TOKEN-1"}

    def test_parse_file_result_for_plain_text_response(self, monkeypatch) -> None:
        response = DummyResponse(
            json_data=..., text="processed", headers={"Content-Type": "text/plain"}
        )
        transport, _ = make_transport(monkeypatch, response)

        result = transport._parse_file_result(response)

        assert result.result == "processed"
        assert result.content is None

    def test_parse_file_result_for_json_payload_without_known_fields(
        self,
        monkeypatch,
    ) -> None:
        response = DummyResponse(json_data={"status": "ok"})
        transport, _ = make_transport(monkeypatch, response)

        result = transport._parse_file_result(response)

        assert result.result is None
        assert result.raw == {"status": "ok"}

    def test_extract_filename_returns_none_when_missing(self) -> None:
        response = DummyResponse(headers={"Content-Type": "application/json"})

        assert HttpTransport._extract_filename(response) is None

    def test_cert_from_destination_failure_is_wrapped(self, monkeypatch) -> None:
        monkeypatch.setattr(
            destination_module,
            "create_client",
            lambda: (_ for _ in ()).throw(RuntimeError("destination boom")),
        )
        monkeypatch.setattr(
            destination_module,
            "create_certificate_client",
            lambda: (_ for _ in ()).throw(RuntimeError("destination boom")),
        )

        transport = object.__new__(HttpTransport)
        transport._config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            destination_name="anon-destination",
        )
        transport._tmp_cert_file = None
        transport._tmp_key_file = None

        assert_raises(
            AuthenticationError,
            "Failed to fetch Key Store from Destination",
            transport._cert_from_destination,
            "anon-destination",
        )

    def test_build_session_sets_cert_tuple(self) -> None:
        session = HttpTransport._build_session(("client.crt", "client.key"))

        assert session.cert == ("client.crt", "client.key")
        session.close()
