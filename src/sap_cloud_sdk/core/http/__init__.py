"""SAP Cloud SDK — core HTTP primitives.

Provides generic, service-agnostic HTTP building blocks:

Async HTTP:
    - :class:`AsyncHttpClient` — async HTTP client with Bearer token injection
    - :class:`HttpError` — raised for non-2xx responses
    - :class:`NotFoundError` — raised specifically for HTTP 404

OData ``$batch``:
    - :class:`ODataBatchBuilder` — build a ``$batch`` multipart request body
    - :class:`ODataBatchResponse` — parse a ``$batch`` multipart response
    - :class:`ODataBatchPart` — a single parsed response part from a batch
"""

from sap_cloud_sdk.core.http._async_client import (
    AsyncHttpClient,
    HttpError,
    NotFoundError,
)
from sap_cloud_sdk.core.http._batch import (
    ODataBatchBuilder,
    ODataBatchPart,
    ODataBatchResponse,
)

__all__ = [
    # async HTTP
    "AsyncHttpClient",
    "HttpError",
    "NotFoundError",
    # OData batch
    "ODataBatchBuilder",
    "ODataBatchPart",
    "ODataBatchResponse",
]
