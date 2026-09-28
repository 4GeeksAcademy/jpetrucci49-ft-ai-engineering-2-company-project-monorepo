"""Read-only inventory lookup. Calls MCP inventory_query — not the service."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Literal

from pydantic import BaseModel, Field

from agent.mcp_client import McpClientError, call_inventory_query

logger = logging.getLogger(__name__)

INVENTORY_LOOKUP_TIMEOUT_SECONDS = 5
STOCK_FALLBACK = "I couldn't confirm that supply's stock right now"
LIST_CAP = 5

InventoryError = Literal["not_found", "timeout", "unavailable"]

_SKU = re.compile(r"\b(HCR-[A-Z0-9]+-\d+)\b", re.IGNORECASE)
_SUPPLY_ID = re.compile(r"\b(?:supply|product)\s*#?\s*(\d+)\b", re.IGNORECASE)
_STOCK_WORDS = re.compile(
    r"\b(?:stock|inventory|sku|supply|supplies|gloves|in stock)\b",
    re.IGNORECASE,
)
_NAME_HINTS = re.compile(
    r"\b(?:nitrile|strep|dressing|saline|glucose|mask)\b",
    re.IGNORECASE,
)
_STOP = frozenset(
    {
        "a",
        "an",
        "any",
        "do",
        "for",
        "have",
        "in",
        "inventory",
        "is",
        "of",
        "on",
        "our",
        "please",
        "sku",
        "stock",
        "supplies",
        "supply",
        "the",
        "there",
        "we",
        "hand",
        "product",
    }
)
COUNTRY_LABELS: dict[str, str] = {
    "US": "United States",
    "UK": "United Kingdom",
}


class InventoryLookupIn(BaseModel):
    supply_id: int | None = None
    sku: str | None = None
    name_query: str | None = None


class SupplyRecord(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class InventoryLookupOut(BaseModel):
    ok: bool
    supplies: list[SupplyRecord] = Field(default_factory=list)
    error: InventoryError | None = None


def lookup_timeout_seconds() -> int:
    raw = os.environ.get("INVENTORY_LOOKUP_TIMEOUT_SECONDS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return INVENTORY_LOOKUP_TIMEOUT_SECONDS


def is_stock_ask(question: str) -> bool:
    return bool(_STOCK_WORDS.search(question) or _SKU.search(question) or _NAME_HINTS.search(question))


def parse_inventory_lookup(question: str) -> InventoryLookupIn:
    text = question.strip()
    sku_match = _SKU.search(text)
    id_match = _SUPPLY_ID.search(text)
    supply_id = int(id_match.group(1)) if id_match else None
    sku = sku_match.group(1).upper() if sku_match else None
    cleaned = text
    if sku_match:
        cleaned = cleaned.replace(sku_match.group(0), " ")
    if id_match:
        cleaned = cleaned.replace(id_match.group(0), " ")
    tokens = [tok for tok in re.findall(r"[A-Za-z0-9%./]+", cleaned) if tok.lower() not in _STOP]
    name_query = " ".join(tokens).strip() or None
    if supply_id is not None:
        return InventoryLookupIn(supply_id=supply_id, sku=None, name_query=None)
    return InventoryLookupIn(supply_id=None, sku=sku, name_query=name_query)


def lookup_inventory(query: InventoryLookupIn) -> InventoryLookupOut:
    timeout = lookup_timeout_seconds()
    if query.supply_id is None and not query.sku and not query.name_query:
        return InventoryLookupOut(ok=False, supplies=[], error="not_found")
    try:
        payload = _call(
            lambda: call_inventory_query(
                supply_id=query.supply_id,
                sku=query.sku,
                name_query=query.name_query,
            ),
            timeout,
        )
        if isinstance(payload, dict) and payload.get("error"):
            return InventoryLookupOut(
                ok=False,
                supplies=[],
                error=_map_error(payload["error"]),
            )
        rows = payload.get("supplies") if isinstance(payload, dict) else payload
        records = [_to_record(row) for row in (rows or [])[:LIST_CAP]]
        if not records:
            return InventoryLookupOut(ok=False, supplies=[], error="not_found")
        return InventoryLookupOut(ok=True, supplies=records, error=None)
    except TimeoutError:
        return InventoryLookupOut(ok=False, supplies=[], error="timeout")
    except McpClientError as exc:
        return InventoryLookupOut(ok=False, supplies=[], error=_map_error(exc.code))
    except Exception:
        logger.exception("inventory lookup unavailable")
        return InventoryLookupOut(ok=False, supplies=[], error="unavailable")


def stock_sentence(result: InventoryLookupOut | dict) -> str:
    payload = (
        result
        if isinstance(result, InventoryLookupOut)
        else InventoryLookupOut.model_validate(result or {})
    )
    if not payload.ok or not payload.supplies:
        return STOCK_FALLBACK
    return format_inventory_answer(payload)


def format_inventory_answer(result: InventoryLookupOut) -> str:
    return "\n".join(_format_one(row) for row in result.supplies)


def _format_one(row: SupplyRecord) -> str:
    country = COUNTRY_LABELS.get(row.country, row.country)
    return (
        f"{row.name} ({row.sku}): {row.current_stock} {row.unit} on hand ({country})."
    )


def _to_record(row: dict | SupplyRecord) -> SupplyRecord:
    if isinstance(row, SupplyRecord):
        return row
    if hasattr(row, "model_dump"):
        return SupplyRecord.model_validate(row.model_dump())
    return SupplyRecord.model_validate(row)


def _map_error(code: str) -> InventoryError:
    if code in {"inventory_not_found", "not_found"}:
        return "not_found"
    if code == "timeout":
        return "timeout"
    return "unavailable"


def _call(fn, timeout: float):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            raise TimeoutError("inventory lookup timed out") from exc
