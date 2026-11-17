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


class HookShortCircuit(ExtensibilityError):
    """Raised when a hook stops execution.

    This can happen when:

    - A hook returns ``stop_execution=true`` in its response metadata and the
      hook has ``can_short_circuit=true`` set in its configuration.
    - A hook fails or times out and its ``on_failure`` policy is ``BLOCK``.

    Attributes:
        reason: Human-readable explanation of why execution was stopped.
        hook_name: Name (or ID) of the hook that triggered the short-circuit.
        capability_id: Extension capability ID the hook belongs to.
    """

    def __init__(
        self, reason: str, hook_name: str = "", capability_id: str = ""
    ) -> None:
        self.reason = reason
        self.hook_name = hook_name
        self.capability_id = capability_id
        super().__init__(reason)
