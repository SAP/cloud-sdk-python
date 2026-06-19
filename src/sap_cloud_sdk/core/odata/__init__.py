"""Shared OData v4 abstractions for the SAP Cloud SDK."""

from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.core.odata._factory import odata_transport_from_destination
from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._models import ODataEntity
from sap_cloud_sdk.core.odata._pagination import ODataPageIterator
from sap_cloud_sdk.core.odata._query import OrderDirection, StructuredQuery
from sap_cloud_sdk.core.odata._request_builders import (
    CreateRequestBuilder,
    DeleteRequestBuilder,
    GetAllRequestBuilder,
    GetByKeyRequestBuilder,
    UpdateRequestBuilder,
)
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataConnectionError,
    ODataCsrfError,
    ODataDeserializationError,
    ODataError,
    ODataNotFoundError,
    ODataRequestError,
)

__all__ = [
    "AsyncODataHttpTransport",
    "CreateRequestBuilder",
    "DeleteRequestBuilder",
    "FilterExpression",
    "GetAllRequestBuilder",
    "GetByKeyRequestBuilder",
    "ODataAuthError",
    "ODataConnectionError",
    "ODataCsrfError",
    "ODataDeserializationError",
    "ODataEntity",
    "ODataError",
    "ODataHttpTransport",
    "ODataNotFoundError",
    "ODataPageIterator",
    "ODataRequestError",
    "OrderDirection",
    "StructuredQuery",
    "UpdateRequestBuilder",
    "odata_transport_from_destination",
]
