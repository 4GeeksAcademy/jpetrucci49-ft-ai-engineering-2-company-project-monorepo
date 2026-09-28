"""MCP Auth resource-server wiring. FastMCP is not given `auth=` or `token_verifier`."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from mcpauth import MCPAuth
from mcpauth.config import AuthServerConfig, AuthServerType
from mcpauth.types import ResourceServerConfig, ResourceServerMetadata
from mcpauth.utils import fetch_server_config

SCOPES_SUPPORTED = ("incidents:read", "incidents:write", "inventory:read")


def mcp_resource() -> str:
    value = os.environ.get("MCP_RESOURCE", "").strip()
    if not value:
        raise RuntimeError("MCP_RESOURCE is required (public resource URL, no fragment).")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.fragment:
        raise RuntimeError(
            "MCP_RESOURCE must be an http(s) URL without a fragment, e.g. "
            "https://<codespace>-8100.app.github.dev/mcp"
        )
    return value


def mcp_issuer() -> str:
    value = os.environ.get("MCP_AUTH_ISSUER", "").strip()
    if not value:
        raise RuntimeError("MCP_AUTH_ISSUER is required (OIDC/OAuth issuer URL).")
    return value.rstrip("/")


def load_auth_server_config() -> AuthServerConfig:
    issuer = mcp_issuer()
    server_type = (
        AuthServerType.OAUTH
        if os.environ.get("MCP_AUTH_SERVER_TYPE", "oidc").strip().lower() == "oauth"
        else AuthServerType.OIDC
    )
    return fetch_server_config(issuer, server_type)


def build_mcp_auth(server_config: AuthServerConfig | None = None) -> tuple[MCPAuth, str]:
    resource = mcp_resource()
    config = server_config or load_auth_server_config()
    mcp_auth = MCPAuth(
        protected_resources=[
            ResourceServerConfig(
                metadata=ResourceServerMetadata(
                    resource=resource,
                    authorization_servers=[config],
                    scopes_supported=list(SCOPES_SUPPORTED),
                )
            )
        ]
    )
    return mcp_auth, resource
