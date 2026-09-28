"""Incident tools. Calls the existing manager — same TinyDB as the API."""

from __future__ import annotations

from pydantic import ValidationError

from app.incidents.manager import create_incident, get_incident, update_incident_status
from app.incidents.models import IncidentCreate, IncidentStatus
from mcps.healthcore.errors import tool_error
from mcps.healthcore.runtime import log_invocation

INCIDENT_GET_DESCRIPTION = (
    "Read one HealthCore Incidents Manager ticket by numeric id. "
    "For coordinators and operators checking status. Does not create or change tickets. "
    "Statuses: open, in_progress, resolved, discarded."
)
INCIDENT_CREATE_DESCRIPTION = (
    "Create a HealthCore Incidents Manager ticket. Default status is open. "
    "Requires incidents:write. Field names match the HTTP API (origin, not source). "
    "category: clinical_equipment | it_system | billing_error | compliance_breach | "
    "patient_experience | staff_issue | facility_issue | referral_issue | other. "
    "origin: customer | branch | internal. "
    "branch: central | austin_north | dallas_uptown | houston_med_center | "
    "san_antonio_west | miami_brickell | miami_doral | orlando_east | tampa_bay | "
    "atlanta_midtown | savannah | london_city | london_west | manchester_central."
)
INCIDENT_UPDATE_DESCRIPTION = (
    "Change only the status of a HealthCore Incidents Manager ticket. "
    "Requires incidents:write. Uses the same lifecycle as PATCH /api/incidents/{id}/status: "
    "open → in_progress | discarded; in_progress → resolved | discarded; "
    "resolved and discarded have no next status. Never a generic field patch."
)


def incidents_get(incident_id: int) -> dict:
    try:
        incident = get_incident(incident_id)
    except Exception:
        log_invocation("incidents_get", "unavailable")
        return tool_error("unavailable", "Incidents store is unavailable.")
    if incident is None:
        log_invocation("incidents_get", "incident_not_found")
        return tool_error("incident_not_found", f"Ticket {incident_id} was not found.")
    log_invocation("incidents_get", "ok")
    return {"ok": True, "incident": incident.model_dump(mode="json")}


def incidents_create(
    title: str,
    description: str,
    category: str,
    origin: str,
    branch: str,
    status: str = IncidentStatus.OPEN.value,
) -> dict:
    try:
        payload = IncidentCreate(
            title=title,
            description=description,
            category=category,
            origin=origin,
            branch=branch,
            status=status,
        )
        incident = create_incident(payload)
    except ValidationError as exc:
        log_invocation("incidents_create", "validation_error")
        return tool_error("validation_error", exc.errors()[0]["msg"])
    except Exception:
        log_invocation("incidents_create", "unavailable")
        return tool_error("unavailable", "Incidents store is unavailable.")
    log_invocation("incidents_create", "ok")
    return {"ok": True, "incident": incident.model_dump(mode="json")}


def incidents_update_status(incident_id: int, status: str) -> dict:
    try:
        new_status = IncidentStatus(status)
    except ValueError:
        log_invocation("incidents_update_status", "validation_error")
        return tool_error(
            "validation_error",
            "status must be open, in_progress, resolved, or discarded.",
        )
    try:
        incident = update_incident_status(incident_id, new_status)
    except LookupError:
        log_invocation("incidents_update_status", "incident_not_found")
        return tool_error("incident_not_found", f"Ticket {incident_id} was not found.")
    except ValueError as exc:
        log_invocation("incidents_update_status", "invalid_status_transition")
        return tool_error("invalid_status_transition", str(exc))
    except Exception:
        log_invocation("incidents_update_status", "unavailable")
        return tool_error("unavailable", "Incidents store is unavailable.")
    log_invocation("incidents_update_status", "ok")
    return {"ok": True, "incident": incident.model_dump(mode="json")}
