"""Exception classes for the extensibility module."""


class ExtensibilityError(Exception):
    """Base exception for all extensibility module errors."""

    pass


class ClientCreationError(ExtensibilityError):
    """Raised when :func:`create_client` fails to construct the client."""

    pass


class TransportError(ExtensibilityError):
    """Raised when transport operations fail.

    This includes network errors, unexpected status codes,
    and response parsing failures when communicating with the
    extensibility backend service.
    """

    pass
