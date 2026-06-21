"""General-purpose HTTP client for the SAP Cloud SDK."""

from sap_cloud_sdk.core.http_client._client import HttpClient
from sap_cloud_sdk.core.http_client._factory import http_client_for_destination
from sap_cloud_sdk.core.http_client.exceptions import (
    HttpClientError,
    HttpConnectionError,
    HttpNotFoundError,
    HttpResponseError,
    HttpUnauthorizedError,
)

__all__ = [
    "HttpClient",
    "HttpClientError",
    "HttpConnectionError",
    "HttpNotFoundError",
    "HttpResponseError",
    "HttpUnauthorizedError",
    "http_client_for_destination",
]
