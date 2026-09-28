"""Inventory tools. Reads only; mutate is registered so clients can see the deny."""

from __future__ import annotations

from inventory.database import get_session_factory
from inventory.exceptions import SupplyNotFoundError
from inventory.schemas import MedicalSupplyResponse
from inventory.service import get_supply, list_supplies
from mcps.healthcore.errors import tool_error
from mcps.healthcore.runtime import log_invocation

LIST_CAP = 5

INVENTORY_QUERY_DESCRIPTION = (
    "Read HealthCore medical-supply stock. Query by supply_id and/or sku and/or name_query. "
    "Returns MedicalSupplyResponse fields including computed current_stock. "
    "At most 5 rows. Does not create supplies, deliveries, or consumptions."
)
INVENTORY_MUTATE_DESCRIPTION = (
    "HealthCore inventory is query-only. This tool always fails. "
    "Registered so clients can discover that writes are rejected (inventory_read_only). "
    "Does not change stock."
)


def inventory_query(
    supply_id: int | None = None,
    sku: str | None = None,
    name_query: str | None = None,
) -> dict:
    session = None
    try:
        session = get_session_factory()()
        if supply_id is not None:
            row = get_supply(session, supply_id)
            log_invocation("inventory_query", "ok")
            return {"ok": True, "supplies": [row.model_dump(mode="json")]}
        if not sku and not name_query:
            log_invocation("inventory_query", "inventory_not_found")
            return tool_error(
                "inventory_not_found",
                "Provide supply_id, sku, or name_query.",
            )
        matched = _filter_rows(list_supplies(session), sku=sku, name_query=name_query)
        if not matched:
            log_invocation("inventory_query", "inventory_not_found")
            return tool_error("inventory_not_found", "No matching supply.")
        log_invocation("inventory_query", "ok")
        return {
            "ok": True,
            "supplies": [row.model_dump(mode="json") for row in matched],
        }
    except SupplyNotFoundError:
        log_invocation("inventory_query", "inventory_not_found")
        return tool_error("inventory_not_found", f"Supply {supply_id} was not found.")
    except Exception:
        log_invocation("inventory_query", "unavailable")
        return tool_error("unavailable", "Inventory store is unavailable.")
    finally:
        if session is not None:
            session.close()


def inventory_mutate(
    supply_id: int | None = None,
    sku: str | None = None,
    quantity: int | None = None,
    action: str | None = None,
) -> dict:
    del supply_id, sku, quantity, action
    log_invocation("inventory_mutate", "inventory_read_only")
    return tool_error(
        "inventory_read_only",
        "HealthCore inventory is query-only. This tool always fails.",
    )


def _filter_rows(
    rows: list[MedicalSupplyResponse],
    *,
    sku: str | None,
    name_query: str | None,
) -> list[MedicalSupplyResponse]:
    if sku:
        needle = sku.casefold()
        exact = [row for row in rows if row.sku.casefold() == needle]
        if exact:
            return exact[:LIST_CAP]
    if name_query:
        needle = name_query.casefold()
        named = [row for row in rows if needle in row.name.casefold()]
        return named[:LIST_CAP]
    return []
