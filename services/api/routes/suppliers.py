"""Supplier directory REST endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from database import get_suppliers_table
from models import (
    VALID_CATEGORIES,
    Supplier,
    SupplierCountry,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_supplier(document: dict) -> Supplier:
    return Supplier.model_validate(document)


def _get_document_or_404(supplier_id: int) -> dict:
    document = get_suppliers_table().get(doc_id=supplier_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return document


def _insert_supplier(payload: SupplierCreate) -> Supplier:
    table = get_suppliers_table()
    now = _utc_now()
    document = payload.model_dump(mode="json")
    document["updated_at"] = now.isoformat()
    doc_id = table.insert(document)
    table.update({"id": doc_id}, doc_ids=[doc_id])
    return _to_supplier({**document, "id": doc_id, "updated_at": now})


def _apply_filters(
    documents: list[dict],
    country: SupplierCountry | None,
    category: str | None,
) -> list[dict]:
    results = documents
    if country is not None:
        results = [doc for doc in results if doc.get("country") == country.value]
    if category is not None:
        results = [
            doc for doc in results if category in doc.get("categories", [])
        ]
    return results


@router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate) -> Supplier:
    """Register a new supplier."""
    return _insert_supplier(payload)


@router.get("", response_model=list[Supplier])
def list_suppliers(
    country: SupplierCountry | None = None,
    category: Annotated[str | None, Query(description="Filter by product/service category")] = None,
) -> list[Supplier]:
    """List suppliers with optional country and category filters."""
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category: {category}")

    documents = get_suppliers_table().all()
    filtered = _apply_filters(documents, country, category)
    filtered.sort(key=lambda doc: doc.get("name", "").casefold())
    return [_to_supplier(doc) for doc in filtered]


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: int) -> Supplier:
    """Return one supplier by TinyDB id."""
    return _to_supplier(_get_document_or_404(supplier_id))


@router.patch("/{supplier_id}/rate", response_model=Supplier)
def update_supplier_rate(supplier_id: int, payload: SupplierRateUpdate) -> Supplier:
    """Update monthly rate and record updated_at."""
    table = get_suppliers_table()
    document = _get_document_or_404(supplier_id)
    now = _utc_now()
    updates = {
        "monthly_rate": payload.monthly_rate,
        "updated_at": now.isoformat(),
    }
    table.update(updates, doc_ids=[supplier_id])
    return _to_supplier({**document, **updates, "updated_at": now})


@router.patch("/{supplier_id}/status", response_model=Supplier)
def update_supplier_status(supplier_id: int, payload: SupplierStatusUpdate) -> Supplier:
    """Activate or suspend a supplier without changing updated_at."""
    table = get_suppliers_table()
    document = _get_document_or_404(supplier_id)
    updates = {"status": payload.status.value}
    table.update(updates, doc_ids=[supplier_id])
    return _to_supplier({**document, **updates})


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int) -> Response:
    """Remove a supplier from the directory."""
    table = get_suppliers_table()
    if table.get(doc_id=supplier_id) is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    table.remove(doc_ids=[supplier_id])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
