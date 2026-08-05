"""Constants for the Output Management SDK."""

from enum import Enum


class Constants:
    """SDK constants."""

    # API Endpoints
    API_OUTPUT_CONTROL = "/api/output-control-api/v1/"

    # Headers
    AUTHORIZATION = "Authorization"
    BEARER = "Bearer"
    HEADER_CONTENT_TYPE = "Content-Type"
    HEADER_ACCEPT = "Accept"
    APPFND_CONHOS_SUBACCOUNTID = "APPFND_CONHOS_SUBACCOUNTID"
    HEADER_SENDER_PROVIDER_SUBACCOUNT_ID = "sender-provider-subaccount-id"
    HEADER_TRACE_PARENT = "traceparent"
    CONTENT_TYPE_JSON = "application/json"
    CONTENT_TYPE_PDF = "application/pdf"


class FileFormat(Enum):
    """Supported file formats."""

    PDF = "PDF"
    DOCX = "DOCX"
    HTML = "HTML"
    XML = "XML"


class Channel(Enum):
    """Output channels."""

    EMAIL = "EMAIL"
    INTERNAL_EMAIL = "INTERNAL_EMAIL"
    DIRECT_SHARE = "DIRECT_SHARE"
    FORM = "FORM"
