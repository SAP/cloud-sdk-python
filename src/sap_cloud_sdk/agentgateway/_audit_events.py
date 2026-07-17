"""Audit event name constants for Agent Gateway."""

from enum import StrEnum


class McpToolEvent(StrEnum):
    INVOKED = "MCP_TOOL_INVOKED"
    COMPLETED = "MCP_TOOL_COMPLETED"
    FAILED = "MCP_TOOL_FAILED"
