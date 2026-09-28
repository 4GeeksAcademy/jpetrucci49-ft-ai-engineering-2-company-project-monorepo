"""Desk-agent MCP client. Streamable HTTP + cached client-credentials token."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcpauth.config import AuthServerType
from mcpauth.utils import fetch_server_config

logger = logging.getLogger(__name__)

SERVER_NAME = "healthcore"
_TOKEN_SKEW_SECONDS = 60

_token_lock = threading.Lock()
_cached_token: str | None = None
_cached_expires_at = 0.0


class McpClientError(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def call_incidents_get(incident_id: int) -> dict:
    payload = _call_tool("incidents_get", {"incident_id": incident_id})
    if payload.get("error"):
        return payload
    return payload.get("incident") or payload


def call_inventory_query(
    *,
    supply_id: int | None = None,
    sku: str | None = None,
    name_query: str | None = None,
) -> dict:
    arguments: dict[str, Any] = {}
    if supply_id is not None:
        arguments["supply_id"] = supply_id
    if sku:
        arguments["sku"] = sku
    if name_query:
        arguments["name_query"] = name_query
    return _call_tool("inventory_query", arguments)


def _call_tool(name: str, arguments: dict[str, Any]) -> dict:
    return _run(_acall_tool(name, arguments))


async def _acall_tool(name: str, arguments: dict[str, Any]) -> dict:
    token = get_access_token()
    url = os.environ.get("MCP_SERVER_URL", "").strip()
    if not url:
        raise McpClientError("unavailable", "MCP_SERVER_URL is not set")
    client = MultiServerMCPClient(
        {
            SERVER_NAME: {
                "transport": "streamable_http",
                "url": url,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        }
    )
    async with client.session(SERVER_NAME) as session:
        result = await session.call_tool(name, arguments)
    return _parse_tool_result(result)


def _parse_tool_result(result: Any) -> dict:
    text = _result_text(result)
    parsed = _maybe_json(text)
    if getattr(result, "isError", False):
        if isinstance(parsed, dict) and parsed.get("error"):
            return parsed
        code, message = _split_error_text(text)
        return {"ok": False, "error": code, "message": message}
    if isinstance(parsed, dict):
        return parsed
    raise McpClientError("unavailable", "MCP tool returned a non-JSON payload")


def _result_text(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _maybe_json(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _split_error_text(text: str) -> tuple[str, str]:
    if ":" in text:
        code, message = text.split(":", 1)
        code = code.strip()
        if code:
            return code, message.strip() or code
    return "unavailable", text or "MCP tool failed"


def get_access_token() -> str:
    global _cached_token, _cached_expires_at
    now = time.time()
    with _token_lock:
        if _cached_token and now < _cached_expires_at - _TOKEN_SKEW_SECONDS:
            return _cached_token
        token, expires_in = _fetch_client_credentials()
        _cached_token = token
        _cached_expires_at = now + max(expires_in, 60)
        return token


def reset_token_cache() -> None:
    global _cached_token, _cached_expires_at
    with _token_lock:
        _cached_token = None
        _cached_expires_at = 0.0


def _fetch_client_credentials() -> tuple[str, int]:
    client_id = os.environ.get("MCP_CLIENT_ID", "").strip()
    client_secret = os.environ.get("MCP_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise McpClientError("unavailable", "MCP client credentials are not set")
    token_url = _token_endpoint()
    resource = os.environ.get("MCP_RESOURCE", "").strip()
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": os.environ.get(
            "MCP_CLIENT_SCOPE", "incidents:read inventory:read"
        ).strip(),
    }
    if resource:
        data["resource"] = resource
        data["audience"] = resource
    response = httpx.post(token_url, data=data, timeout=10.0)
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise McpClientError("unavailable", "token endpoint returned no access_token")
    expires_in = int(payload.get("expires_in") or 3600)
    return str(token), expires_in


def _token_endpoint() -> str:
    configured = os.environ.get("MCP_TOKEN_URL", "").strip()
    if configured:
        return configured
    issuer = os.environ.get("MCP_AUTH_ISSUER", "").strip()
    if not issuer:
        raise McpClientError("unavailable", "MCP_AUTH_ISSUER is not set")
    server_type = (
        AuthServerType.OAUTH
        if os.environ.get("MCP_AUTH_SERVER_TYPE", "oidc").strip().lower() == "oauth"
        else AuthServerType.OIDC
    )
    return fetch_server_config(issuer, server_type).metadata.token_endpoint


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    result: dict[str, Any] = {}

    def _worker() -> None:
        result["value"] = asyncio.run(coro)

    thread = threading.Thread(target=_worker, name="mcp-client")
    thread.start()
    thread.join()
    if "value" not in result:
        raise McpClientError("unavailable", "MCP client thread failed")
    return result["value"]
