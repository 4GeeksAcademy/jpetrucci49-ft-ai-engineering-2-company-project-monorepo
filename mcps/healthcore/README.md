# HealthCore MCP server

Independent Streamable HTTP MCP server for Incidents Manager and inventory. Auth is [MCP Auth](https://mcp-auth.dev/) (`mcpauth`) in **resource-server** mode — not FastMCP’s built-in `AuthSettings` / `token_verifier`.

## Run

From the repository root (needs `MCP_AUTH_ISSUER` and `MCP_RESOURCE` in gitignored `.env`):

```bash
PYTHONPATH=".:services/api" uv run --env-file .env --env-file services/api/.env \
  uvicorn mcps.healthcore.server:app --host 0.0.0.0 --port 8100
```

Or `npm run dev:mcp`. The desk API stays on port **8000**.

In Codespaces: Ports tab → forward **8100** → visibility **Public**. `MCP_RESOURCE` must be that public origin plus `/mcp` (no fragment), and it must match the token `aud`.

## URLs

| What | Path |
| --- | --- |
| MCP (Streamable HTTP) | `/mcp` |
| Protected Resource Metadata (RFC 9728) | `/.well-known/oauth-protected-resource/mcp` when `MCP_RESOURCE` ends in `/mcp` |

Unauthenticated `tools/list` or `tools/call` → **401** + `WWW-Authenticate` pointing at the PRM URL.

## Scopes

| Scope | Tools |
| --- | --- |
| `incidents:read` | `incidents_get` (also required by HTTP middleware to list/call) |
| `incidents:write` | `incidents_create`, `incidents_update_status` |
| `inventory:read` | `inventory_query`, `inventory_mutate` (so a client can see the deny) |

There is no `inventory:write`. The desk agent M2M token only needs `incidents:read` (and `inventory:read` if the graph uses `inventory_query`).

## Tools

| Tool | Input | Output |
| --- | --- | --- |
| `incidents_get` | `incident_id` (int) | `IncidentPublic` JSON |
| `incidents_create` | `title`, `description`, `category`, `origin`, `branch`, optional `status` (default `open`) | `IncidentPublic` JSON |
| `incidents_update_status` | `incident_id`, `status` | `IncidentPublic` JSON — lifecycle only |
| `inventory_query` | `supply_id` and/or `sku` and/or `name_query` | up to 5 `MedicalSupplyResponse` rows (`current_stock` computed) |
| `inventory_mutate` | optional dummy write fields | **always** tool error `inventory_read_only` |

Status lifecycle: `open` → `in_progress` \| `discarded`; `in_progress` → `resolved` \| `discarded`; terminals have no next.

## Error codes

| Code | When | Layer |
| --- | --- | --- |
| `invalid_token` | Missing or bad JWT | HTTP **401** |
| `insufficient_scope` | Valid JWT, wrong scopes | HTTP **403** or tool error naming the missing scope |
| `incident_not_found` | Unknown ticket id | tool error |
| `invalid_status_transition` | Illegal status change | tool error |
| `validation_error` | Bad enum / empty title | tool error |
| `inventory_not_found` | No matching SKU / name / id | tool error |
| `inventory_read_only` | Any `inventory_mutate` call | tool error |
| `unavailable` | TinyDB / inventory DB down | tool error |

Each call logs `tool`, `client_id`, `subject`, `result` (`ok` or the error code). Tokens, PHI, and full descriptions are not logged.

## Env

| Variable | Who | Purpose |
| --- | --- | --- |
| `MCP_AUTH_ISSUER` | Server | OIDC/OAuth issuer (JWKS via discovery) |
| `MCP_AUTH_SERVER_TYPE` | Server | `oidc` (default) or `oauth` |
| `MCP_RESOURCE` | Server | Resource id + expected `aud` (public URL in Codespaces) |
| `MCP_SERVER_URL` | Desk agent | e.g. `http://127.0.0.1:8100/mcp` locally |
| `MCP_CLIENT_ID` / `MCP_CLIENT_SECRET` | Desk agent | M2M client credentials |

`JWT_SECRET` is the desk API HS256 secret. It is **not** an MCP OAuth token.

## Dependencies

Root + `services/api`: `mcpauth`, `mcp` (FastMCP), `langchain-mcp-adapters` (agent client only).
