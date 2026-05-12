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
