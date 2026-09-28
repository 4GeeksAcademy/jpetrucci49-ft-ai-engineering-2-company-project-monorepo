"""Shared request-time helpers: auth context and invocation logs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcps.healthcore.errors import raise_tool_error

if TYPE_CHECKING:
    from mcpauth import MCPAuth

logger = logging.getLogger("mcps.healthcore")

_mcp_auth: MCPAuth | None = None


def bind_mcp_auth(mcp_auth: MCPAuth) -> None:
    global _mcp_auth
    _mcp_auth = mcp_auth


def current_auth() -> tuple[str | None, str | None, list[str]]:
    if _mcp_auth is None:
        return None, None, []
    info = _mcp_auth.auth_info
    if info is None:
        return None, None, []
    return info.client_id, info.subject, list(info.scopes or [])


def require_scope(scope: str) -> None:
    _client_id, _subject, scopes = current_auth()
    if scope not in scopes:
        raise_tool_error("insufficient_scope", f"missing {scope}")


def log_invocation(tool: str, result: str) -> None:
    client_id, subject, _scopes = current_auth()
    logger.info(
        "tool=%s client_id=%s subject=%s result=%s",
        tool,
        client_id or "-",
        subject or "-",
        result,
    )
