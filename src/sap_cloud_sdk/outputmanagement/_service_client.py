"""Output Management service client implementation."""

import base64
import logging
import os
import requests
import tempfile
import uuid
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from sap_cloud_sdk.destination import (
    Destination,
    create_certificate_client,
    AccessStrategy,
)

from ._models import OutputRequest, OutputResponse, ErrorResponse
from .constants import Constants
from .utils import RequestValidator

logger = logging.getLogger(__name__)


class OutputManagementServiceClient:
    """Service client for Output Management.

    Handles low-level HTTP communication, authentication (OAuth with mTLS),
    certificate management, and request/response processing.
    """

    def __init__(
        self,
        base_url: str,
        destination: Optional[Destination] = None,
        destination_instance: Optional[str] = None,
    ):
        """Initialize client.

        Args:
            base_url: Base URL of the service
            destination: Optional Cloud SDK destination object for making requests
            destination_instance: Optional Destination Service instance name
        """
        self._base_url = base_url.rstrip("/")
        self._destination = destination
        self._destination_instance = destination_instance
        self._session = requests.Session()

        # Get sender-provider-subaccount-id from environment variable
        self._sender_provider_subaccount_id = os.getenv(
            Constants.APPFND_CONHOS_SUBACCOUNTID
        )
        if self._sender_provider_subaccount_id:
            logger.info(
                f"Loaded SENDER_PROVIDER_SUBACCOUNT_ID: {self._sender_provider_subaccount_id}"
            )

        logger.info(f"Initialized Output Management Service client for {base_url}")

    def send_output_request(self, output_request: OutputRequest) -> OutputResponse:
        """Send an output request to the Output Management service.

        Args:
            output_request: The output request to submit

        Returns:
            OutputResponse containing the request ID if successful, or error details
        """
        logger.info("Sending output request")

        if output_request is None:
            logger.error("OutputRequest cannot be None")
            return self._create_output_error_response(
                "INVALID_REQUEST", "OutputRequest cannot be None"
            )

        # Validate the output request
        validation_error = RequestValidator.validate(output_request)
        if validation_error:
            logger.error(f"Validation failed: {validation_error}")
            return self._create_output_error_response(
                "INVALID_REQUEST", validation_error
            )

        endpoint = f"{self._base_url}{Constants.API_OUTPUT_CONTROL}outputRequest"
        logger.debug(f"Endpoint: {endpoint}")

        headers = self._get_headers()
        headers[Constants.HEADER_CONTENT_TYPE] = Constants.CONTENT_TYPE_JSON
        headers[Constants.HEADER_ACCEPT] = Constants.CONTENT_TYPE_JSON

        # Add sender-provider-subaccount-id header if available
        if self._sender_provider_subaccount_id:
            headers[Constants.HEADER_SENDER_PROVIDER_SUBACCOUNT_ID] = (
                self._sender_provider_subaccount_id
            )
            logger.debug("Added sender-provider-subaccount-id header")

        try:
            request_body = output_request.model_dump(by_alias=True, exclude_none=True)

            response = self._session.request(
                "POST", endpoint, json=request_body, headers=headers
            )
            status_code = response.status_code

            logger.debug(f"Response status: {status_code}")

            if status_code == 202:
                response_data = response.json()
                request_id = response_data.get("requestId")
                logger.info(f"Request submitted successfully with ID: {request_id}")
                return OutputResponse(outputRequestId=request_id, error=None)

            # Handle error responses
            response_body = response.text
            if self._is_retryable(status_code):
                logger.error(
                    f"Retryable error with status: {status_code}, body: {response_body}"
                )
            else:
                logger.error(
                    f"Non-retryable error with status: {status_code}, body: {response_body}"
                )

            error_type = self._map_status_code_to_error(status_code)
            if error_type:
                return self._create_output_error_response(error_type, str(status_code))
            else:
                logger.warning(
                    f"Unhandled status code: {status_code}. Using original status code and message."
                )
                return self._create_output_error_response(str(status_code), response_body)

        except Exception as e:
            logger.error(f"Exception occurred: {e}", exc_info=True)
            return self._create_output_error_response(
                "OUTPUT_REQUEST_FAILED", f"Failed to send output request: {str(e)}"
            )

    def _fetch_oauth_token_from_destination(self) -> Optional[str]:
        """Fetch OAuth token using destination's OAuth configuration with mTLS."""
        if not self._destination or not hasattr(self._destination, "properties"):
            return None

        props = self._destination.properties
        if not isinstance(props, dict):
            return None

        # Extract OAuth configuration from destination properties
        token_url = props.get("tokenServiceURL")
        client_id = (
            props.get("client_id")
            or props.get("clientId")
            or props.get("tokenService.body.client_id")
        )
        grant_type = props.get("tokenService.body.grant_type", "client_credentials")
        app_tid = props.get("tokenService.body.app_tid")

        # Certificate name to lookup in Destination Service
        cert_name = props.get("tokenService.KeyStoreLocation")
        cert_password = props.get("tokenService.KeyStorePassword")

        if not token_url or not client_id:
            logger.error(
                f"Missing OAuth config: tokenServiceURL={token_url}, clientId={client_id}"
            )
            return None

        if not cert_name:
            logger.error(
                "No certificate name in destination properties (tokenService.certificate)"
            )
            return None

        # Track temp files for cleanup
        temp_files_created = False
        cert_file = None
        key_file = None

        try:
            # Build OAuth token request
            token_data = {"grant_type": grant_type, "client_id": client_id}
            if app_tid:
                token_data["app_tid"] = app_tid

            logger.info(f"Fetching OAuth token from {token_url} using mTLS")

            # Get certificate from Cloud SDK Destination Service
            try:
                inst = self._destination_instance or "default"
                certificate_client = create_certificate_client(instance=inst)

                cert = certificate_client.get_subaccount_certificate(
                    cert_name, access_strategy=AccessStrategy.PROVIDER_ONLY
                )

                if cert is None:
                    logger.error(
                        f"Certificate '{cert_name}' not found in Destination Service"
                    )
                    return None

                # Decode base64 content
                cert_binary = base64.b64decode(cert.content)

                # Parse certificate - PKCS12 format
                password = cert_password.encode("utf-8") if cert_password else None

                private_key, certificate, additional_certs = (
                    pkcs12.load_key_and_certificates(cert_binary, password)
                )

                if not (certificate and private_key):
                    logger.error("No certificate or key found in PKCS12")
                    return None

                # Write certificate to temp file
                cert_fd, cert_file = tempfile.mkstemp(suffix=".pem")
                with os.fdopen(cert_fd, "wb") as f:
                    f.write(certificate.public_bytes(Encoding.PEM))
                    if additional_certs:
                        for c in additional_certs:
                            f.write(c.public_bytes(Encoding.PEM))

                # Write private key to temp file
                key_fd, key_file = tempfile.mkstemp(suffix=".key")
                with os.fdopen(key_fd, "wb") as f:
                    f.write(
                        private_key.private_bytes(
                            encoding=Encoding.PEM,
                            format=PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=NoEncryption(),
                        )
                    )

                temp_files_created = True

            except Exception as e:
                logger.error(
                    f"Failed to retrieve/process certificate '{cert_name}': {e}",
                    exc_info=True,
                )
                return None

            # Make token request with mTLS
            if not (cert_file and key_file):
                logger.error("No client certificates available")
                return None

            request_kwargs: Dict[str, Any] = {
                "data": token_data,
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "timeout": 30,
                "verify": True,
                "cert": (cert_file, key_file),
            }

            response = requests.post(token_url, **request_kwargs)

            # Clean up temp files
            if temp_files_created:
                try:
                    os.unlink(cert_file)
                    if key_file != cert_file:
                        os.unlink(key_file)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp files: {e}")

            # Handle response
            if response.status_code == 200:
                token_response = response.json()
                access_token = token_response.get("access_token")
                if access_token:
                    logger.info(
                        f"Successfully fetched OAuth token (length: {len(access_token)})"
                    )
                    return access_token
                else:
                    logger.error(
                        f"No access_token in response: {list(token_response.keys())}"
                    )
            else:
                logger.error(
                    f"Token fetch failed with status {response.status_code}: {response.text}"
                )

        except Exception as e:
            logger.error(f"Exception fetching OAuth token: {e}", exc_info=True)
            if temp_files_created:
                try:
                    if cert_file:
                        os.unlink(cert_file)
                    if key_file and key_file != cert_file:
                        os.unlink(key_file)
                except:
                    pass

        return None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {}

        # Add trace parent header for distributed tracing
        headers[Constants.HEADER_TRACE_PARENT] = self._generate_trace_id()

        # If using destination, get auth token from it
        if self._destination:
            token = self._fetch_oauth_token_from_destination()
            if token:
                headers[Constants.AUTHORIZATION] = f"{Constants.BEARER} {token}"
                logger.info("Authorization header added to request")
            else:
                logger.error("Failed to fetch OAuth token from destination")

        return headers

    @staticmethod
    def _generate_trace_id() -> str:
        """Generate traceparent header in W3C Trace Context format."""
        trace_id = uuid.uuid4().hex  # 32 hex chars
        parent_id = uuid.uuid4().hex[:16]  # 16 hex chars
        return f"00-{trace_id}-{parent_id}-01"

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        """Checks if the HTTP status code represents a retryable error."""
        return status_code >= 500 or status_code == 429

    @staticmethod
    def _map_status_code_to_error(status_code: int) -> Optional[str]:
        """Maps HTTP error status codes to appropriate error types."""
        error_mapping = {
            400: "INVALID_REQUEST",
            401: "AUTHENTICATION_FAILED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            409: "CONFLICT",
            429: "INVALID_REQUEST",
            500: "INTERNAL_SERVER_ERROR",
            502: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }
        return error_mapping.get(status_code)

    @staticmethod
    def _create_output_error_response(error_type: str, message: str) -> OutputResponse:
        """Create an OutputResponse with error information."""
        return OutputResponse(
            outputRequestId=None,
            error=ErrorResponse(message=str(message), code=error_type),
        )

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        logger.info("Output Management Service client closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
