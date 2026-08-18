"""Tests for supplier directory logic (API-042)."""

import pytest
from fastapi import HTTPException
from models import (
    SupplierCountry,
    SupplierCreate,
    SupplierCurrency,
    SupplierRateUpdate,
    SupplierStatus,
    SupplierStatusUpdate,
)
from pydantic import ValidationError
from routes.suppliers import (
    _get_document_or_404,
    _insert_supplier,
    update_supplier_rate,
    update_supplier_status,
)


def _sample_supplier(**overrides) -> SupplierCreate:
    payload = {
        "name": "Acme Medical Supplies",
        "country": SupplierCountry.USA,
        "categories": ["medical_supplies"],
        "monthly_rate": 4200.0,
        "currency": SupplierCurrency.USD,
        "status": SupplierStatus.ACTIVE,
    }
    payload.update(overrides)
    return SupplierCreate(**payload)


def test_sp1_valid_supplier_create_persisted_active():
    supplier = _insert_supplier(_sample_supplier())
    assert supplier.status == SupplierStatus.ACTIVE
    assert supplier.country == SupplierCountry.USA
    assert supplier.currency == SupplierCurrency.USD
    assert supplier.name == "Acme Medical Supplies"


def test_sp2_rate_update_changes_updated_at():
    supplier = _insert_supplier(_sample_supplier())
    first_updated_at = supplier.updated_at
    updated = update_supplier_rate(
        supplier.id,
        SupplierRateUpdate(monthly_rate=5000.0),
        None,
    )
    assert updated.monthly_rate == 5000.0
    assert updated.updated_at >= first_updated_at


def test_sp3_suspend_supplier_retains_row():
    supplier = _insert_supplier(_sample_supplier())
    suspended = update_supplier_status(
        supplier.id,
        SupplierStatusUpdate(status=SupplierStatus.SUSPENDED),
        None,
    )
    assert suspended.status == SupplierStatus.SUSPENDED
    loaded = _get_document_or_404(supplier.id)
    assert loaded["status"] == SupplierStatus.SUSPENDED.value


def test_sp4_invalid_category_rejected_by_model():
    with pytest.raises(ValidationError):
        _sample_supplier(categories=["not_a_real_category"])


def test_sp5_usa_supplier_with_gbp_rejected():
    with pytest.raises(ValidationError):
        _sample_supplier(currency=SupplierCurrency.GBP)


def test_sp6_missing_supplier_raises_not_found():
    with pytest.raises(HTTPException) as exc:
        _get_document_or_404(99999)
    assert exc.value.status_code == 404
