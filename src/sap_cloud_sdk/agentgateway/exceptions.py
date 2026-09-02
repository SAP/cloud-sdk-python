"""Exception classes for the Agent Gateway module."""


class AgentGatewaySDKError(Exception):
    """Base exception for Agent Gateway SDK errors.

    Raised for errors originating from the SDK itself,
    such as validation errors.
    """

    pass


class MCPServerNotFoundError(AgentGatewaySDKError):
    """Raised when an MCP server is not found.

    This error occurs when:
    - No destination fragment exists with the specified ORD ID
    - The fragment exists but has no URL property
    - The corresponding destination cannot be resolved
    - The destination has no auth tokens
    """

    pass


class AgentGatewayServerError(AgentGatewaySDKError):
    """Raised when the Agent Gateway server returns an error response.

    This error occurs when:
    - The MCP server card is not found in the registry
    - The server returns a JSON-RPC error (e.g. code -32600)
    - A tool invocation returns an error result (isError=True)

    Attributes:
        error_code: JSON-RPC error code, if available.
        server_message: The raw error message from the server.
    """

    def __init__(self, message: str, error_code: int | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.server_message = message
