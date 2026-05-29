"""SAP Cloud SDK — core HTTP primitives.

Provides generic, service-agnostic HTTP building blocks:

Async HTTP:
    - :class:`AsyncHttpClient` — async HTTP client with Bearer token injection
    - :class:`HttpError` — raised for non-2xx responses
    - :class:`NotFoundError` — raised specifically for HTTP 404
"""

from sap_cloud_sdk.core.http._async_client import (
    AsyncHttpClient,
    HttpError,
    NotFoundError,
)

__all__ = [
    "AsyncHttpClient",
    "HttpError",
    "NotFoundError",
]
