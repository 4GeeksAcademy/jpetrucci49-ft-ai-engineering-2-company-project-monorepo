"""Read-only inventory lookup. Calls the existing service — no fake catalogue."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Literal

from pydantic import BaseModel, Field

from inventory.schemas import MedicalSupplyResponse

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


def list_supplies() -> list[MedicalSupplyResponse]:
    from inventory.database import get_session_factory
    from inventory.service import list_supplies as _list_supplies

    session = get_session_factory()()
    try:
        return _list_supplies(session)
    finally:
        session.close()


def get_supply(supply_id: int) -> MedicalSupplyResponse:
    from inventory.database import get_session_factory
    from inventory.service import get_supply as _get_supply

    session = get_session_factory()()
    try:
        return _get_supply(session, supply_id)
    finally:
        session.close()


def lookup_inventory(query: InventoryLookupIn) -> InventoryLookupOut:
    timeout = lookup_timeout_seconds()
    try:
        if query.supply_id is not None:
            row = _call(lambda: get_supply(query.supply_id), timeout)
            return InventoryLookupOut(ok=True, supplies=[_to_record(row)], error=None)
        if not query.sku and not query.name_query:
            return InventoryLookupOut(ok=False, supplies=[], error="not_found")
        rows = _call(list_supplies, timeout)
        matched = _filter_rows(rows or [], query)
        if not matched:
            return InventoryLookupOut(ok=False, supplies=[], error="not_found")
        return InventoryLookupOut(ok=True, supplies=matched, error=None)
    except TimeoutError:
        return InventoryLookupOut(ok=False, supplies=[], error="timeout")
    except Exception as exc:
        if _is_not_found(exc):
            return InventoryLookupOut(ok=False, supplies=[], error="not_found")
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


def _filter_rows(
    rows: list[MedicalSupplyResponse], query: InventoryLookupIn
) -> list[SupplyRecord]:
    if query.sku:
        sku = query.sku.casefold()
        exact = [row for row in rows if row.sku.casefold() == sku]
        if exact:
            return [_to_record(row) for row in exact[:LIST_CAP]]
    if query.name_query:
        needle = query.name_query.casefold()
        named = [row for row in rows if needle in row.name.casefold()]
        return [_to_record(row) for row in named[:LIST_CAP]]
    return []


def _to_record(row: MedicalSupplyResponse) -> SupplyRecord:
    return SupplyRecord.model_validate(row.model_dump())


def _is_not_found(exc: Exception) -> bool:
    from inventory.exceptions import SupplyNotFoundError

    return isinstance(exc, SupplyNotFoundError)


def _call(fn, timeout: float):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            raise TimeoutError("inventory lookup timed out") from exc
