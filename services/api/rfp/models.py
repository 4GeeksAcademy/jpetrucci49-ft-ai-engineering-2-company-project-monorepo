"""SQLModel tables for RFP tickets, metadata, and department sections.

Source of truth is Postgres (same engine as inventory). Never store PHI.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

JsonCol = JSONB().with_variant(JSON(), "sqlite")

TICKET_STATUSES = ("analyzing", "discarded", "intake_complete")
DISCARD_REASONS = ("not_an_rfp", "pipeline_error")
DEPARTMENT_IDS = ("revenue", "clinical", "compliance")
CLIENT_COUNTRIES = ("US", "UK", "unknown")
PROGRAM_TYPES = (
    "occupational_health",
    "corporate_wellness",
    "referral_network",
    "unknown",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RfpTicket(SQLModel, table=True):
    __tablename__ = "rfp_tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('analyzing', 'discarded', 'intake_complete')",
            name="ck_rfp_tickets_status",
        ),
        CheckConstraint(
            "discard_reason IS NULL OR discard_reason IN ('not_an_rfp', 'pipeline_error')",
            name="ck_rfp_tickets_discard_reason",
        ),
    )

    ticket_id: str = Field(primary_key=True, max_length=36)
    rfp_id: str | None = Field(default=None, max_length=36, index=True)
    status: str = Field(default="analyzing", max_length=32)
    discard_reason: str | None = Field(default=None, max_length=32)
    error_code: str | None = Field(default=None, max_length=32)
    phi_detected: bool = Field(default=False)
    raw_pdf_path: str = Field(max_length=512)
    markdown_path: str | None = Field(default=None, max_length=512)
    handoff_json: dict | None = Field(default=None, sa_column=Column(JsonCol, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_by: str = Field(max_length=64)


class RfpMetadata(SQLModel, table=True):
    __tablename__ = "rfp_metadata"
    __table_args__ = (
        UniqueConstraint("ticket_id", name="uq_rfp_metadata_ticket_id"),
        CheckConstraint(
            "client_country IN ('US', 'UK', 'unknown')",
            name="ck_rfp_metadata_client_country",
        ),
        CheckConstraint(
            "program_type IN ('occupational_health', 'corporate_wellness', "
            "'referral_network', 'unknown')",
            name="ck_rfp_metadata_program_type",
        ),
    )

    id: str = Field(primary_key=True, max_length=36)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, max_length=36)
    client_name: str | None = Field(default=None, max_length=200)
    client_country: str = Field(default="unknown", max_length=16)
    program_type: str = Field(default="unknown", max_length=32)
    covered_population: int | None = Field(default=None)
    deadline: str | None = Field(default=None, max_length=64)
    budget_range: str | None = Field(default=None, max_length=128)
    currency: str | None = Field(default=None, max_length=8)
    departments_needed: list = Field(default_factory=list, sa_column=Column(JsonCol, nullable=False))
    readability: dict = Field(default_factory=dict, sa_column=Column(JsonCol, nullable=False))


class RfpDepartmentSection(SQLModel, table=True):
    __tablename__ = "rfp_department_sections"
    __table_args__ = (
        UniqueConstraint("ticket_id", "department_id", name="uq_rfp_section_ticket_dept"),
        CheckConstraint(
            "department_id IN ('revenue', 'clinical', 'compliance')",
            name="ck_rfp_section_department_id",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, max_length=36)
    department_id: str = Field(max_length=32)
    key_aspects: list = Field(default_factory=list, sa_column=Column(JsonCol, nullable=False))
    open_questions: list = Field(default_factory=list, sa_column=Column(JsonCol, nullable=False))
    draft_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    evaluation_results: dict | None = Field(default=None, sa_column=Column(JsonCol, nullable=True))
    approval_status: str | None = Field(default=None, max_length=32)
    approver: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
