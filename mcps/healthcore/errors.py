"""Typed MCP tool error codes. HTTP auth errors stay on the middleware."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp.exceptions import ToolError

ToolErrorCode = Literal[
    "incident_not_found",
    "invalid_status_transition",
    "validation_error",
    "inventory_not_found",
    "inventory_read_only",
    "unavailable",
    "insufficient_scope",
]


def tool_error(code: ToolErrorCode, message: str) -> dict:
    return {"ok": False, "error": code, "message": message}


def raise_tool_error(code: ToolErrorCode, message: str) -> None:
    """Fail the MCP tool call so clients see `isError` plus the code."""
    raise ToolError(f"{code}: {message}")
