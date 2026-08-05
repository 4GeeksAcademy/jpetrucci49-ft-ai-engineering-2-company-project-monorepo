"""Pydantic models for the HealthCore supplier directory."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

VALID_CATEGORIES = [
    "medical_supplies",
    "laboratory_services",
    "pharmaceutical",
    "clinical_software",
    "it_infrastructure",
    "hr_and_payroll_software",
    "cleaning_and_facilities",
    "patient_communication",
    "billing_and_coding_software",
    "training_platforms",
]

VALID_STATUSES = ["active", "suspended"]


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SupplierCountry(StrEnum):
    USA = "USA"
    UK = "UK"


class SupplierCurrency(StrEnum):
    USD = "USD"
    GBP = "GBP"


class ComplianceAgreement(StrEnum):
    BAA = "BAA"
    DPA = "DPA"
    BOTH = "both"


COUNTRY_CURRENCY = {
    SupplierCountry.USA: SupplierCurrency.USD,
    SupplierCountry.UK: SupplierCurrency.GBP,
}


def _validate_categories(categories: list[str]) -> list[str]:
    if not categories:
        raise ValueError("categories must contain at least one item")
    invalid = [category for category in categories if category not in VALID_CATEGORIES]
    if invalid:
        raise ValueError(f"invalid categories: {', '.join(invalid)}")
    return categories


def _validate_country_currency_pair(
    country: SupplierCountry,
    currency: SupplierCurrency,
) -> None:
    expected = COUNTRY_CURRENCY[country]
    if currency != expected:
        raise ValueError(
            f"currency must be {expected.value} for country {country.value}, got {currency.value}"
        )


class SupplierBase(BaseModel):
    name: str
    country: SupplierCountry
    categories: list[str]
    monthly_rate: float = Field(gt=0)
    currency: SupplierCurrency
    status: SupplierStatus
    compliance_agreement: ComplianceAgreement | None = None
    contract_renewal_date: date | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("name must not be empty")
            return stripped
        return value

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, categories: list[str]) -> list[str]:
        return _validate_categories(categories)

    @model_validator(mode="after")
    def validate_country_currency(self) -> Self:
        _validate_country_currency_pair(self.country, self.currency)
        return self


class SupplierCreate(SupplierBase):
    """Request body for registering a new supplier."""


class SupplierUpdate(BaseModel):
    """Partial update payload — merged and re-validated by the service before save."""

    name: str | None = None
    country: SupplierCountry | None = None
    categories: list[str] | None = None
    monthly_rate: float | None = Field(default=None, gt=0)
    currency: SupplierCurrency | None = None
    status: SupplierStatus | None = None
    compliance_agreement: ComplianceAgreement | None = None
    contract_renewal_date: date | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        if value is None:
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("name must not be empty")
            return stripped
        return value

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, categories: list[str] | None) -> list[str] | None:
        if categories is None:
            return categories
        return _validate_categories(categories)

    @model_validator(mode="after")
    def validate_country_currency(self) -> Self:
        if self.country is not None and self.currency is not None:
            _validate_country_currency_pair(self.country, self.currency)
        return self


class SupplierRateUpdate(BaseModel):
    """Dedicated payload for monthly rate changes."""

    monthly_rate: float = Field(gt=0)


class SupplierStatusUpdate(BaseModel):
    """Dedicated payload for activate / suspend."""

    status: SupplierStatus


class Supplier(SupplierBase):
    """Full supplier record returned by the API and stored in TinyDB."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
