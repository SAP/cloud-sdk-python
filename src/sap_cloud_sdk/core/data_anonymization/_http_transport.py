"""HTTP transport for the SAP Data Anonymization Service.

Authentication uses a Key Store (client certificate / mTLS) only.
Two key store sources are supported, selected automatically from the config:

1. **Inline Key Store** (``cert`` + ``key``)
    Base64-encoded PEM certificate and private key are materialized to temporary
    files for the underlying HTTP client.

2. **BTP Destination Key Store** (``destination_name``)
    The certificate and key are fetched at runtime from the BTP Destination
    service using ``sap_cloud_sdk.destination``.

API endpoints
-------------
POST {service_url}/anonymization/api/v1.0/unstructureddata/text
POST {service_url}/anonymization/api/v1.0/unstructureddata/file
POST {service_url}/anonymization/api/v1.0/unstructureddata/pseudonymize/text
POST {service_url}/anonymization/api/v1.0/unstructureddata/pseudonymize/file
"""

import base64
import binascii
import os
import tempfile
from typing import Any, BinaryIO, Mapping, Optional, Protocol, TypeAlias

import requests

from sap_cloud_sdk.core.data_anonymization._transport import Transport
from sap_cloud_sdk.core.data_anonymization.config import DataAnonymizationConfig
from sap_cloud_sdk.core.data_anonymization.exceptions import (
    AuthenticationError,
    TransportError,
)
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeRequest,
    AnonymizeResult,
    FileOperationResult,
    PseudonymizeFileRequest,
    PseudonymizeRequest,
    PseudonymizeResult,
)

_ANONYMIZE_TEXT_PATH = "/anonymization/api/v1.0/unstructureddata/text"
_ANONYMIZE_FILE_PATH = "/anonymization/api/v1.0/unstructureddata/file"
_PSEUDONYMIZE_TEXT_PATH = "/anonymization/api/v1.0/unstructureddata/pseudonymize/text"
_PSEUDONYMIZE_FILE_PATH = "/anonymization/api/v1.0/unstructureddata/pseudonymize/file"
_REQUEST_TIMEOUT = 30


class _ResponseLike(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> Any: ...


_FileRequest: TypeAlias = AnonymizeFileRequest | PseudonymizeFileRequest


class HttpTransport(Transport):
    """HTTP transport authenticated via Key Store (mTLS client certificate)."""

    def __init__(self, config: DataAnonymizationConfig) -> None:
        self._config = config
        self._tmp_cert_file: Optional[Any] = None
        self._tmp_key_file: Optional[Any] = None

        cert = self._resolve_cert()
        self._session = self._build_session(cert)

    # ------------------------------------------------------------------
    # Transport interface
    # ------------------------------------------------------------------

    def anonymize_text(self, request: AnonymizeRequest) -> AnonymizeResult:
        """Call the text anonymization endpoint."""
        url = self._url(_ANONYMIZE_TEXT_PATH)
        try:
            response = self._session.post(
                url,
                data=request.to_form_fields(),
                timeout=_REQUEST_TIMEOUT,
            )
            self._raise_for_status(url, response)
            return self._parse_anonymize_text_result(response)
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Network error calling anonymize_text: {e}")
        except TransportError:
            raise
        except Exception as e:
            raise TransportError(f"Unexpected error calling anonymize_text: {e}")

    def anonymize_file(self, request: AnonymizeFileRequest) -> FileOperationResult:
        """Call the file anonymization endpoint with multipart upload."""
        url = self._url(_ANONYMIZE_FILE_PATH)
        try:
            response = self._post_file_request(url, request)
            self._raise_for_status(url, response)
            return self._parse_file_result(response)
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Network error calling anonymize_file: {e}")
        except TransportError:
            raise
        except Exception as e:
            raise TransportError(f"Unexpected error calling anonymize_file: {e}")

    def pseudonymize_text(self, request: PseudonymizeRequest) -> PseudonymizeResult:
        """Call the text pseudonymization endpoint."""
        url = self._url(_PSEUDONYMIZE_TEXT_PATH)
        try:
            response = self._session.post(
                url,
                data=request.to_form_fields(),
                timeout=_REQUEST_TIMEOUT,
            )
            self._raise_for_status(url, response)
            return self._parse_pseudonymize_text_result(response)
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Network error calling pseudonymize_text: {e}")
        except TransportError:
            raise
        except Exception as e:
            raise TransportError(f"Unexpected error calling pseudonymize_text: {e}")

    def pseudonymize_file(
        self,
        request: PseudonymizeFileRequest,
    ) -> FileOperationResult:
        """Call the file pseudonymization endpoint with multipart upload."""
        url = self._url(_PSEUDONYMIZE_FILE_PATH)
        try:
            response = self._post_file_request(url, request)
            self._raise_for_status(url, response)
            return self._parse_file_result(response)
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Network error calling pseudonymize_file: {e}")
        except TransportError:
            raise
        except Exception as e:
            raise TransportError(f"Unexpected error calling pseudonymize_file: {e}")

    def close(self) -> None:
        self._session.close()
        for tmp in (self._tmp_cert_file, self._tmp_key_file):
            if tmp is not None:
                try:
                    tmp.close()
                    os.unlink(tmp.name)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Build an absolute service URL for the given API path."""
        return f"{self._config.service_url.rstrip('/')}{path}"

    @staticmethod
    def _raise_for_status(
        url: str, response: requests.Response | _ResponseLike
    ) -> None:
        status_code = response.status_code
        if not isinstance(status_code, int):
            raise TransportError(f"POST {url} returned an invalid status code")
        if not (200 <= status_code < 300):
            raise TransportError(f"POST {url} returned {status_code}: {response.text}")

    def _post_file_request(
        self,
        url: str,
        request: _FileRequest,
    ) -> requests.Response:
        """Submit a multipart request with either a file path or in-memory bytes."""
        file_handle: Optional[BinaryIO] = None
        try:
            if request.file_path is not None:
                file_handle = open(request.file_path, "rb")
                file_value = file_handle
            else:
                file_value = request.file_content

            files = {
                "file": (
                    request.resolved_file_name(),
                    file_value,
                )
            }

            return self._session.post(
                url,
                data=request.to_form_fields(),
                files=files,
                timeout=_REQUEST_TIMEOUT,
            )
        finally:
            if file_handle is not None:
                file_handle.close()

    @staticmethod
    def _parse_json_payload(
        response: requests.Response | _ResponseLike,
    ) -> Optional[Any]:
        """Return parsed JSON if the response body is JSON, else `None`."""
        try:
            return response.json()
        except ValueError:
            return None

    def _parse_anonymize_text_result(
        self,
        response: requests.Response | _ResponseLike,
    ) -> AnonymizeResult:
        """Normalize text anonymization responses to `AnonymizeResult`."""
        payload = self._parse_json_payload(response)
        if isinstance(payload, dict):
            return AnonymizeResult.from_dict(payload)
        if isinstance(payload, str):
            return AnonymizeResult(result=payload, raw={"result": payload})
        return AnonymizeResult(result=response.text, raw={"result": response.text})

    def _parse_pseudonymize_text_result(
        self,
        response: requests.Response | _ResponseLike,
    ) -> PseudonymizeResult:
        """Normalize text pseudonymization responses to `PseudonymizeResult`."""
        payload = self._parse_json_payload(response)
        if isinstance(payload, dict):
            return PseudonymizeResult.from_dict(payload)
        if isinstance(payload, str):
            return PseudonymizeResult(result=payload, raw={"result": payload})
        return PseudonymizeResult(result=response.text, raw={"result": response.text})

    def _parse_file_result(
        self,
        response: requests.Response | _ResponseLike,
    ) -> FileOperationResult:
        """Normalize file endpoint responses across sync, async, and ZIP modes."""
        payload = self._parse_json_payload(response)
        content_type = response.headers.get("Content-Type", "")
        filename = self._extract_filename(response)

        if isinstance(payload, dict):
            if "job_id" in payload:
                return FileOperationResult(
                    job_id=payload.get("job_id"),
                    content_type=content_type,
                    filename=filename,
                    raw=payload,
                )
            if "result" in payload:
                return FileOperationResult(
                    result=str(payload.get("result") or ""),
                    content_type=content_type,
                    filename=filename,
                    raw=payload,
                )
            return FileOperationResult(
                content_type=content_type,
                filename=filename,
                raw=payload,
            )

        if isinstance(payload, str):
            return FileOperationResult(
                result=payload,
                content_type=content_type,
                filename=filename,
                raw={"result": payload},
            )

        if content_type.startswith("text/"):
            return FileOperationResult(
                result=response.text,
                content_type=content_type,
                filename=filename,
                raw={"result": response.text},
            )

        return FileOperationResult(
            content=response.content,
            content_type=content_type,
            filename=filename,
            raw={},
        )

    @staticmethod
    def _extract_filename(
        response: requests.Response | _ResponseLike,
    ) -> Optional[str]:
        """Extract the server-provided filename from `Content-Disposition`."""
        content_disposition = response.headers.get("Content-Disposition", "")
        for part in content_disposition.split(";"):
            part = part.strip()
            if part.startswith("filename="):
                return part.split("=", 1)[1].strip('"')
        return None

    def _resolve_cert(self) -> str | tuple[str, str]:
        """Return requests-compatible client certificate configuration."""
        cfg = self._config

        if cfg.cert and cfg.key:
            return self._cert_from_inline_values(cfg.cert, cfg.key)

        if cfg.cert_path and cfg.key_path:
            return (cfg.cert_path, cfg.key_path)

        if cfg.destination_name:
            return self._cert_from_destination(cfg.destination_name)

        raise AuthenticationError(
            "No Key Store configured: set cert + key, cert_path + key_path, or destination_name"
        )

    def _cert_from_inline_values(
        self, cert_content: str, key_content: str
    ) -> tuple[str, str]:
        """Decode inline certificate values and write them to temporary PEM files."""
        cert_pem = self._decode_inline_pem_content(
            cert_content,
            field_name="cert",
            expected_marker="-----BEGIN CERTIFICATE-----",
            error_suffix="certificate",
        )
        key_pem = self._decode_inline_pem_content(
            key_content,
            field_name="key",
            expected_marker="PRIVATE KEY-----",
            error_suffix="private key",
        )

        cert_tmp = tempfile.NamedTemporaryFile(
            suffix=".crt", delete=False, mode="w", encoding="utf-8"
        )
        cert_tmp.write(cert_pem)
        cert_tmp.flush()
        cert_tmp.close()
        self._tmp_cert_file = cert_tmp

        key_tmp = tempfile.NamedTemporaryFile(
            suffix=".key", delete=False, mode="w", encoding="utf-8"
        )
        key_tmp.write(key_pem)
        key_tmp.flush()
        key_tmp.close()
        self._tmp_key_file = key_tmp

        return (cert_tmp.name, key_tmp.name)

    def _cert_from_destination(self, name: str) -> str:
        """Resolve a combined PEM bundle via Destination and write it to a temp file."""
        try:
            from sap_cloud_sdk.core.telemetry import Module
            from sap_cloud_sdk.destination import (
                AccessStrategy,
                create_certificate_client,
                create_client,
            )

            destination_client = create_client(
                _telemetry_source=Module.DATA_ANONYMIZATION,
            )
            destination = destination_client.get_instance_destination(name)
            if destination is None:
                destination = destination_client.get_subaccount_destination(
                    name,
                    access_strategy=AccessStrategy.PROVIDER_ONLY,
                )
            if destination is None:
                raise AuthenticationError(f"Destination '{name}' not found")

            key_store_location = self._get_destination_keystore_location(
                destination, name
            )
            cert_client = create_certificate_client(
                _telemetry_source=Module.DATA_ANONYMIZATION,
            )
            cert = cert_client.get_instance_certificate(key_store_location)
            if cert is None:
                cert = cert_client.get_subaccount_certificate(
                    key_store_location,
                    access_strategy=AccessStrategy.PROVIDER_ONLY,
                )
            if cert is None:
                raise AuthenticationError(
                    f"Certificate '{key_store_location}' referenced by Destination '{name}' was not found"
                )

            pem_bundle = self._decode_destination_certificate_content(cert.content)

            cert_tmp = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="w", encoding="utf-8"
            )
            cert_tmp.write(pem_bundle)
            cert_tmp.flush()
            cert_tmp.close()
            self._tmp_cert_file = cert_tmp

            return cert_tmp.name

        except AuthenticationError:
            raise

        except Exception as e:
            raise AuthenticationError(
                f"Failed to fetch Key Store from Destination '{name}': {e}"
            )

    @staticmethod
    def _get_destination_keystore_location(destination: Any, name: str) -> str:
        """Read the certificate bundle reference from a Destination entity."""
        auth = getattr(destination, "authentication", None)
        auth_value = getattr(auth, "value", auth)
        if auth_value and str(auth_value) != "ClientCertificateAuthentication":
            raise AuthenticationError(
                f"Destination '{name}' is not configured with ClientCertificateAuthentication"
            )

        properties = getattr(destination, "properties", {}) or {}
        key_store_location = (
            properties.get("KeyStoreLocation")
            or properties.get("keyStoreLocation")
            or properties.get("keystoreLocation")
        )
        if not isinstance(key_store_location, str) or not key_store_location.strip():
            raise AuthenticationError(
                f"Destination '{name}' does not define KeyStoreLocation"
            )
        return key_store_location.strip()

    @staticmethod
    def _decode_destination_certificate_content(content: str) -> str:
        """Normalize Destination certificate content to a combined PEM bundle."""
        if not content or not content.strip():
            raise AuthenticationError("Destination certificate content is empty")

        pem_bundle = content.strip()
        if "-----BEGIN " not in pem_bundle:
            try:
                decoded = base64.b64decode(pem_bundle, validate=True)
            except (binascii.Error, ValueError) as e:
                raise AuthenticationError(
                    f"Destination certificate content is not valid base64-encoded PEM: {e}"
                ) from e
            try:
                pem_bundle = decoded.decode("utf-8")
            except UnicodeDecodeError as e:
                raise AuthenticationError(
                    "Destination certificate content is not valid UTF-8 PEM text"
                ) from e

        if "-----BEGIN CERTIFICATE-----" not in pem_bundle:
            raise AuthenticationError(
                "Destination certificate bundle does not contain a certificate"
            )
        if "PRIVATE KEY-----" not in pem_bundle:
            raise AuthenticationError(
                "Destination certificate bundle does not contain a private key"
            )

        return pem_bundle

    @staticmethod
    def _decode_inline_pem_content(
        content: str,
        *,
        field_name: str,
        expected_marker: str,
        error_suffix: str,
    ) -> str:
        """Decode base64-encoded inline PEM content and validate its type."""
        if not content or not content.strip():
            raise AuthenticationError(f"Client {field_name} content is empty")

        pem_content = content.strip()
        if "-----BEGIN " not in pem_content:
            try:
                decoded = base64.b64decode(pem_content, validate=True)
            except (binascii.Error, ValueError) as e:
                raise AuthenticationError(
                    f"Client {field_name} content is not valid base64-encoded PEM: {e}"
                ) from e

            try:
                pem_content = decoded.decode("utf-8")
            except UnicodeDecodeError as e:
                raise AuthenticationError(
                    f"Client {field_name} content is not valid UTF-8 PEM text"
                ) from e

        if expected_marker not in pem_content:
            raise AuthenticationError(
                f"Client {field_name} content does not contain a {error_suffix}"
            )

        return pem_content

    @staticmethod
    def _build_session(cert: str | tuple[str, str]) -> requests.Session:
        """Build a requests.Session with the mTLS client certificate attached."""
        session = requests.Session()
        session.cert = cert
        return session
