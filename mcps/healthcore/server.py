"""Streamable HTTP MCP server. Auth is mcpauth only — not FastMCP built-in OAuth."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcpauth.config import AuthServerConfig
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (str(_REPO_ROOT), str(_API_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(_API_ROOT / ".env", override=True)
except ImportError:
    pass

from mcps.healthcore.auth import build_mcp_auth
from mcps.healthcore.errors import raise_tool_error
from mcps.healthcore.runtime import bind_mcp_auth, require_scope
from mcps.healthcore.tools import incidents as incident_tools
from mcps.healthcore.tools import inventory as inventory_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# host=0.0.0.0 so FastMCP does not enable localhost-only DNS rebinding checks
# that would block the public Codespaces URL used by MCP Playground.
mcp = FastMCP(
    "healthcore",
    instructions=(
        "HealthCore operations tools: Incidents Manager tickets and medical-supply stock. "
        "Inventory writes are not allowed."
    ),
    host="0.0.0.0",
    stateless_http=True,
    streamable_http_path="/mcp",
)


def _unwrap_or_raise(payload: dict) -> dict:
    if payload.get("ok"):
        return payload
    raise_tool_error(payload["error"], payload.get("message") or payload["error"])
    raise AssertionError("unreachable")


@mcp.tool(name="incidents_get", description=incident_tools.INCIDENT_GET_DESCRIPTION)
def incidents_get(incident_id: int) -> dict:
    require_scope("incidents:read")
    return _unwrap_or_raise(incident_tools.incidents_get(incident_id))


@mcp.tool(name="incidents_create", description=incident_tools.INCIDENT_CREATE_DESCRIPTION)
def incidents_create(
    title: str,
    description: str,
    category: str,
    origin: str,
    branch: str,
    status: str = "open",
) -> dict:
    require_scope("incidents:write")
    return _unwrap_or_raise(
        incident_tools.incidents_create(
            title=title,
            description=description,
            category=category,
            origin=origin,
            branch=branch,
            status=status,
        )
    )


@mcp.tool(
    name="incidents_update_status",
    description=incident_tools.INCIDENT_UPDATE_DESCRIPTION,
)
def incidents_update_status(incident_id: int, status: str) -> dict:
    require_scope("incidents:write")
    return _unwrap_or_raise(
        incident_tools.incidents_update_status(incident_id, status)
    )


@mcp.tool(
    name="inventory_query",
    description=inventory_tools.INVENTORY_QUERY_DESCRIPTION,
)
def inventory_query(
    supply_id: int | None = None,
    sku: str | None = None,
    name_query: str | None = None,
) -> dict:
    require_scope("inventory:read")
    return _unwrap_or_raise(
        inventory_tools.inventory_query(
            supply_id=supply_id,
            sku=sku,
            name_query=name_query,
        )
    )


@mcp.tool(
    name="inventory_mutate",
    description=inventory_tools.INVENTORY_MUTATE_DESCRIPTION,
)
def inventory_mutate(
    supply_id: int | None = None,
    sku: str | None = None,
    quantity: int | None = None,
    action: str | None = None,
) -> dict:
    require_scope("inventory:read")
    return _unwrap_or_raise(
        inventory_tools.inventory_mutate(
            supply_id=supply_id,
            sku=sku,
            quantity=quantity,
            action=action,
        )
    )


def create_app(server_config: AuthServerConfig | None = None) -> Starlette:
    mcp_auth, resource = build_mcp_auth(server_config)
    bind_mcp_auth(mcp_auth)
    mcp_http = mcp.streamable_http_app()
    bearer = mcp_auth.bearer_auth_middleware(
        "jwt",
        resource=resource,
        audience=resource,
        required_scopes=["incidents:read"],
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        async with mcp.session_manager.run():
            yield

    return Starlette(
        routes=[
            *mcp_auth.resource_metadata_router().routes,
            Mount("/", app=mcp_http, middleware=[Middleware(bearer)]),
        ],
        lifespan=lifespan,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=["*"],
                expose_headers=["WWW-Authenticate", "Mcp-Session-Id"],
            )
        ],
    )


def __getattr__(name: str):
    if name == "app":
        built = create_app()
        globals()["app"] = built
        return built
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
