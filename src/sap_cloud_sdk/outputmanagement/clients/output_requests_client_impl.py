"""Implementation of output requests client."""

import logging
import os
import uuid
from typing import Dict, Optional

import requests
from sap_cloud_sdk.destination import Destination

from .output_requests_client import OutputRequestsClient
from ..constants import Constants
from ..models.output_request import OutputRequest
from ..models.output_response import (
    OutputResponse,
)
from ..utils.request_validator import RequestValidator

logger = logging.getLogger(__name__)


class OutputRequestsClientImpl(OutputRequestsClient):
    """
    Implementation of OutputRequestsClient for managing output requests.
    
    This implementation provides HTTP-based communication with the Output Management service
    for submitting, tracking, and retrieving output requests and generated documents.
    """

    def __init__(
        self,
        http_session: requests.Session,
        base_url: str,
        destination: Optional[Destination] = None,
        destination_instance: Optional[str] = None,
    ):
        """
        Constructs a new OutputRequestsClientImpl.
        
        Args:
            http_session: The requests Session for making HTTP requests
            base_url: The base URL of the Output Management service
            destination: Optional Cloud SDK destination object for making authenticated requests
            destination_instance: Optional Destination Service instance name (defaults to "default")
        """
        self._http_session = http_session
        self._base_url = base_url.rstrip("/")
        self._destination = destination
        self._destination_instance = destination_instance
        
        # Get sender-provider-subaccount-id from environment variable
        self._sender_provider_subaccount_id = os.getenv("APPFND_CONHOS_SUBACCOUNTID")
        if self._sender_provider_subaccount_id:
            logger.info(f"Loaded SENDER_PROVIDER_SUBACCOUNT_ID: {self._sender_provider_subaccount_id}")
        else:
            logger.debug("SENDER_PROVIDER_SUBACCOUNT_ID environment variable not set")

    def send_output_request(self, output_request: OutputRequest) -> OutputResponse:
        """Submits an output request to the Output Management service."""
        logger.info("Sending output request")

        if output_request is None:
            logger.error("OutputRequest cannot be None")
            return self._create_output_error_response(
                "INVALID_REQUEST",
                "OutputRequest cannot be None"
            )

        # Validate the output request
        validation_error = RequestValidator.validate(output_request)
        if validation_error:
            logger.error(f"Validation failed: {validation_error}")
            return self._create_output_error_response(
                "INVALID_REQUEST",
                validation_error
            )

        endpoint = f"{self._base_url}{Constants.API_OUTPUT_CONTROL}outputRequest"
        logger.debug(f"Endpoint: {endpoint}")

        headers = self._get_headers()
        headers[Constants.HEADER_CONTENT_TYPE] = Constants.CONTENT_TYPE_JSON
        headers[Constants.HEADER_ACCEPT] = Constants.CONTENT_TYPE_JSON
        
        # Add sender-provider-subaccount-id header if available
        if self._sender_provider_subaccount_id:
            headers[Constants.HEADER_SENDER_PROVIDER_SUBACCOUNT_ID] = self._sender_provider_subaccount_id
            logger.debug(f"Added sender-provider-subaccount-id header")

        try:
            request_body = output_request.model_dump(by_alias=True, exclude_none=True)

            response = self._http_session.request('POST', endpoint, json=request_body, headers=headers)
            status_code = response.status_code

            logger.debug(f"Response status: {status_code}")

            if status_code == 202:
                response_data = response.json()
                request_id = response_data.get("requestId")
                logger.info(f"Request submitted successfully with ID: {request_id}")
                return OutputResponse(output_request_id=request_id, error=None)

            # Handle error responses
            response_body = response.text
            if self._is_retryable(status_code):
                logger.error(f"Retryable error with status: {status_code}, body: {response_body}")
            else:
                logger.error(f"Non-retryable error with status: {status_code}, body: {response_body}")

            error_type = self._map_status_code_to_error(status_code)
            if error_type:
                return self._create_output_error_response(error_type, status_code)
            else:
                logger.warning(f"Unhandled status code: {status_code}. Using original status code and message.")
                return self._create_output_error_response(status_code, response_body)

        except Exception as e:
            logger.error(f"Exception occurred: {e}", exc_info=True)
            return self._create_output_error_response(
                "OUTPUT_REQUEST_FAILED",
                f"Failed to send output request: {str(e)}"
            )

    def _fetch_oauth_token_from_destination(self) -> Optional[str]:
        """Fetch OAuth token using destination's OAuth configuration with mTLS.
        
        Uses SAP Cloud SDK to retrieve certificates from the Destination Service.
        
        Returns:
            OAuth access token or None if fetch fails
        """
        if not self._destination or not hasattr(self._destination, 'properties'):
            return None
            
        props = self._destination.properties
        if not isinstance(props, dict):
            return None
        
        # Log destination properties for debugging
        logger.debug(f"Destination properties keys: {list(props.keys())}")
        
        # Extract OAuth configuration from destination properties
        token_url = props.get('tokenServiceURL')
        client_id = props.get('client_id') or props.get('clientId') or props.get('tokenService.body.client_id')
        grant_type = props.get('tokenService.body.grant_type', 'client_credentials')
        app_tid = props.get('tokenService.body.app_tid')
        
        # Certificate name to lookup in Destination Service
        # The certificate must be uploaded to Destination Service first using:
        # certificate_client.create_certificate(Certificate(name="my-cert.p12", content=base64_content, type="PKCS12"))
        cert_name = props.get('tokenService.KeyStoreLocation')
        cert_password = props.get('tokenService.KeyStorePassword')
        
        if not token_url or not client_id:
            logger.error(f"Missing OAuth config: tokenServiceURL={token_url}, clientId={client_id}")
            return None
        
        if not cert_name:
            logger.error("✗ No certificate name in destination properties (tokenService.certificate)")
            logger.error("✗ Please upload your keystore to Destination Service and reference it")
            logger.error("✗ Example: certificate_client.create_certificate(Certificate(name='my-cert.p12', content=base64_content, type='PKCS12'))")
            return None
        
        # Track temp files for cleanup
        temp_files_created = False
        cert_file = None
        key_file = None
        
        try:
            # Build OAuth token request
            token_data = {
                'grant_type': grant_type,
                'client_id': client_id
            }
            if app_tid:
                token_data['app_tid'] = app_tid
            
            logger.info(f"Fetching OAuth token from {token_url} using mTLS")
            logger.info(f"✓ Using certificate from Destination Service: {cert_name}")
            
            # Get certificate from Cloud SDK Destination Service
            try:
                from sap_cloud_sdk.destination import create_certificate_client, AccessStrategy
                import tempfile
                import base64
                from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
                
                # Resolve instance name: use provided value or default to "default" (following DMS pattern)
                inst = self._destination_instance or "default"
                logger.info(f"✓ Creating certificate client for instance '{inst}'")
                
                try:
                    certificate_client = create_certificate_client(instance=inst)
                    logger.info(f"✓ Certificate client created successfully for instance '{inst}'")
                except Exception as e:
                    logger.error(f"✗ Failed to create certificate client for instance '{inst}': {e}")
                    logger.error("✗ Ensure the Destination Service is properly bound and configured")
                    return None
                
                logger.info(f"✓ Retrieving certificate '{cert_name}' from Destination Service")
                cert = certificate_client.get_subaccount_certificate(cert_name, access_strategy=AccessStrategy.PROVIDER_ONLY)
                
                # Check if certificate was found
                if cert is None:
                    logger.error(f"✗ Certificate '{cert_name}' not found in Destination Service")
                    logger.error("✗ Please ensure the certificate is uploaded to Destination Service")
                    logger.error("✗ Example: certificate_client.create_certificate(Certificate(name='my-cert.p12', content=base64_content, type='PKCS12'))")
                    return None
                
                logger.info(f"✓ Retrieved certificate '{cert.name}' (type: {cert.type})")
                
                # Decode base64 content
                cert_binary = base64.b64decode(cert.content)
                logger.debug(f"✓ Decoded certificate content ({len(cert_binary)} bytes)")
                
                # Parse certificate - try PKCS12 format first (most common for mTLS)
                password = cert_password.encode('utf-8') if cert_password else None
                
                try:
                    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                        cert_binary,
                        password
                    )
                    
                    if not (certificate and private_key):
                        logger.error("✗ No certificate or key found in PKCS12")
                        return None
                    
                    logger.info("✓ Successfully parsed certificate and extracted keys")
                    
                    # Write certificate to temp file (include chain)
                    cert_fd, cert_file = tempfile.mkstemp(suffix='.pem')
                    with os.fdopen(cert_fd, 'wb') as f:
                        f.write(certificate.public_bytes(Encoding.PEM))
                        if additional_certs:
                            for c in additional_certs:
                                f.write(c.public_bytes(Encoding.PEM))
                    
                    # Write private key to temp file
                    key_fd, key_file = tempfile.mkstemp(suffix='.key')
                    with os.fdopen(key_fd, 'wb') as f:
                        f.write(private_key.private_bytes(
                            encoding=Encoding.PEM,
                            format=PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=NoEncryption()
                        ))
                    
                    temp_files_created = True
                    
                except Exception as e:
                    logger.error(f"✗ Failed to parse certificate: {e}")
                    logger.error("✗ Certificate must be in PKCS12 format (.p12/.pfx) containing both certificate and private key")
                    return None
                
            except ImportError as e:
                logger.error("✗ sap-cloud-sdk or cryptography library not installed")
                logger.error("✗ Install with: pip install sap-cloud-sdk cryptography")
                logger.error(f"✗ ImportError details: {e}")
                return None
            except Exception as e:
                logger.error(f"✗ Failed to retrieve/process certificate '{cert_name}': {e}", exc_info=True)
                return None
            
            # Make token request with mTLS
            if not(cert_file and key_file):
                logger.error("✗ No client certificates available")
                return None
            
            request_kwargs = {
                'data': token_data,
                'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
                'timeout': 30,
                'verify': True,
                'cert': (cert_file, key_file)
            }
            
            logger.info("✓ Configuring mTLS with certificate files")
            logger.debug(f"  Cert file: {cert_file}")
            logger.debug(f"  Key file: {key_file}")
            
            response = requests.post(token_url, **request_kwargs)
            
            # Clean up temp files
            if temp_files_created:
                try:
                    os.unlink(cert_file)
                    if key_file != cert_file:
                        os.unlink(key_file)
                    logger.debug("✓ Cleaned up temporary certificate files")
                except Exception as e:
                    logger.warning(f"⚠ Failed to cleanup temp files: {e}")
            
            # Handle response
            if response.status_code == 200:
                token_response = response.json()
                access_token = token_response.get('access_token')
                if access_token:
                    logger.info(f"✓ Successfully fetched OAuth token (length: {len(access_token)})")
                    return access_token
                else:
                    logger.error(f"✗ No access_token in response: {list(token_response.keys())}")
            else:
                # Parse OAuth error response
                try:
                    error_response = response.json()
                    error_type = error_response.get('error', 'unknown')
                    error_desc = error_response.get('error_description', 'No description')
                    logger.error(f"✗ Token fetch failed with status {response.status_code}")
                    logger.error(f"✗ OAuth error: {error_type} - {error_desc}")
                except:
                    logger.error(f"✗ Token fetch failed with status {response.status_code}: {response.text}")
                
                logger.error("✗ mTLS authentication failed - check certificates and credentials")
                
        except Exception as e:
            logger.error(f"✗ Exception fetching OAuth token: {e}", exc_info=True)
            # Clean up temp files even on exception
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
            logger.debug(f"Using destination for authentication. Destination type: {type(self._destination)}")
            
            # Try to fetch OAuth token using destination's OAuth configuration
            token = self._fetch_oauth_token_from_destination()
            if token:
                headers[Constants.AUTHORIZATION] = f"{Constants.BEARER} {token}"
                logger.info("✓ Authorization header added to request")
            else:
                logger.error("✗ Failed to fetch OAuth token from destination")
                logger.error("✗ NO Authorization header - request will fail")
        else:
            logger.error("✗ No destination available for authentication")
        
        return headers

    @staticmethod
    def _generate_trace_id() -> str:
        """
        Generate traceparent header in W3C Trace Context format.
        
        Format: version-trace-id-parent-id-trace-flags
        - version: 2 hex digits (00)
        - trace-id: 32 hex digits (16 bytes)
        - parent-id: 16 hex digits (8 bytes)
        - trace-flags: 2 hex digits (01 = sampled)
        
        Returns:
            Traceparent header value in format: 00-{trace_id}-{parent_id}-01
        """
        trace_id = uuid.uuid4().hex  # 32 hex chars
        parent_id = uuid.uuid4().hex[:16]  # 16 hex chars
        return f"00-{trace_id}-{parent_id}-01"

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        """
        Checks if the HTTP status code represents a retryable error.
        
        Args:
            status_code: The HTTP status code
            
        Returns:
            True if the status code is 5xx (server error) or 429 (Too Many Requests)
        """
        return status_code >= 500 or status_code == 429

    @staticmethod
    def _map_status_code_to_error(status_code: int) -> Optional[str]:
        """
        Maps HTTP error status codes to appropriate error types.
        
        Note: This method returns None for unhandled status codes.
        
        Args:
            status_code: The HTTP error status code
            
        Returns:
            The corresponding error type, or None if not mapped
        """
        error_mapping = {
            # Client errors (4xx)
            400: "INVALID_REQUEST",
            401: "AUTHENTICATION_FAILED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            409: "CONFLICT",
            429: "INVALID_REQUEST",  # Too Many Requests
            
            # Server errors (5xx)
            500: "INTERNAL_SERVER_ERROR",
            502: "INTERNAL_SERVER_ERROR",  # Bad Gateway
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }
        return error_mapping.get(status_code)

    @staticmethod
    def _create_output_error_response(error_type, message) -> OutputResponse:
        """Create an OutputResponse with error information."""
        from ..models.output_response import ErrorResponse
        return OutputResponse(
            output_request_id=None,
            error=ErrorResponse(message=str(message), code=error_type)
        )


