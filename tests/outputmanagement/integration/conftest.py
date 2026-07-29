# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company and Cloud SDK contributors
# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for Output Management integration tests."""

import logging
import os
import json
import uuid
from pathlib import Path
from typing import Optional
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest
from dotenv import load_dotenv

from sap_cloud_sdk.outputmanagement import create_client, OutputManagementClient, DestinationCredentialConfig
from sap_cloud_sdk.outputmanagement._service_client import OutputManagementServiceClient
from sap_cloud_sdk.destination.config import DestinationConfig

logger = logging.getLogger(__name__)

# Mock server configuration for local mode
MOCK_HOST = "localhost"
MOCK_PORT = 18080
MOCK_BASE_URL = f"http://{MOCK_HOST}:{MOCK_PORT}"


class MockOutputManagementHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler for Output Management service."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/api/output-control-api/v1/outputRequest":
            self._handle_output_request()
        else:
            self._send_error_response(404, f"Path not found: {self.path}")

    def _handle_output_request(self):
        """Handle output request submission."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            # Parse request
            request_data = json.loads(body)
            logger.info(
                f"Received output request: {request_data.get('type', 'unknown')}"
            )

            # Generate mock response
            response = {
                "requestId": str(uuid.uuid4()),
                "timestamp": "2024-01-01T00:00:00Z",
            }

            # Send successful response (202 Accepted)
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        except Exception as e:
            logger.error(f"Error handling output request: {e}")
            self._send_error_response(500, str(e))

    def _send_error_response(self, status_code: int, message: str):
        """Send error response."""
        error_response = {"error": {"code": str(status_code), "message": message}}
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode("utf-8"))


class MockOutputManagementServer:
    """Mock Output Management server for local testing."""

    def __init__(self, host: str = MOCK_HOST, port: int = MOCK_PORT):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None

    def start(self):
        """Start the mock server."""
        self.server = HTTPServer((self.host, self.port), MockOutputManagementHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(
            f"Mock Output Management server started at http://{self.host}:{self.port}"
        )

    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Mock Output Management server stopped")


@pytest.fixture(scope="session")
def output_management_client():
    """Create an Output Management client for testing.

    Supports two modes:
    1. Cloud mode (default): Uses real BTP Output Management service
    2. Local mode (CLOUD_SDK_OMS_TEST_MODE=local): Uses mock HTTP server

    Cloud mode is the default for proper integration testing.
    Set CLOUD_SDK_OMS_TEST_MODE=local for development without credentials.
    """
    _setup_environment()

    test_mode = os.getenv("CLOUD_SDK_OMS_TEST_MODE", "cloud").lower()

    if test_mode == "local":
        logger.info("Using LOCAL mode for Output Management integration tests")
        return _create_local_client()
    else:
        logger.info("Using CLOUD mode for Output Management integration tests")
        return _create_cloud_client()


def _create_cloud_client():
    """Create client for cloud testing using secret resolver."""
    try:
        # Secret resolver handles configuration automatically from /etc/secrets/appfnd or CLOUD_SDK_CFG
        client = create_client(instance="default")
        return client
    except Exception as e:
        pytest.skip(
            f"Output Management cloud integration tests require credentials: {e}"
        )


def _create_local_client():
    """Create client for local testing with mock server."""
    # Start mock server
    server = MockOutputManagementServer()
    server.start()

    # Create service client pointing to mock server
    service_client = OutputManagementServiceClient(
        base_url=MOCK_BASE_URL, destination=None, destination_instance=None
    )

    # Create high-level client
    client = OutputManagementClient(service_client=service_client)
    logger.info(
        f"Created Output Management client for local testing at {MOCK_BASE_URL}"
    )
    return client


def _setup_environment():
    """Load environment variables from .env_integration_tests if present."""
    env_file = Path(__file__).parents[3] / ".env_integration_tests"
    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded environment from {env_file}")
