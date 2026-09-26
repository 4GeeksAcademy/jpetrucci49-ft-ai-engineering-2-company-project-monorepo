"""Deterministic desk-turn routing. No I/O."""

from __future__ import annotations

from agent.tools.incidents import IncidentLookupIn, classify_question, is_policy_question
from agent.tools.inventory import InventoryLookupIn, is_stock_ask, parse_inventory_lookup


def classify_turn(question: str) -> tuple[str, IncidentLookupIn, InventoryLookupIn]:
    intent, incident_query = classify_question(question)
    inventory_query = parse_inventory_lookup(question)
    if intent in {"incident", "both"}:
        return intent, incident_query, inventory_query
    if is_stock_ask(question):
        if is_policy_question(question):
            return "inventory_rag", incident_query, inventory_query
        return "inventory", incident_query, inventory_query
    return intent, incident_query, inventory_query
