"""Pydantic request/response models for RFP intake HTTP."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreated(BaseModel):
    ticket_id: str
    status: str = "analyzing"


class RfpMetadataOut(BaseModel):
    client_name: str | None = None
    client_country: str = "unknown"
    program_type: str = "unknown"
    covered_population: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    currency: str | None = None
    departments_needed: list[str] = Field(default_factory=list)
    readability: dict[str, float] = Field(default_factory=dict)


class TicketOut(BaseModel):
    ticket_id: str
    rfp_id: str | None = None
    status: str
    discard_reason: str | None = None
    error_code: str | None = None
    phi_detected: bool = False
    created_at: datetime
    updated_at: datetime
    metadata: RfpMetadataOut | None = None
    handoff_json: dict | None = None
    part2_handoff_json: dict | None = None


class DepartmentSectionOut(BaseModel):
    department_id: str
    owner: str
    key_aspects: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    draft_content: str | None = None
    evaluation_results: dict | None = None


class TicketSectionsOut(BaseModel):
    ticket_id: str
    sections: list[DepartmentSectionOut]
