import { authFetch, parseApiError } from "@healthcore/auth";
import { toUserFacingMessage } from "@healthcore/api/errors";

const NETWORK_ERROR = "Unable to reach the server. Check your connection and try again.";
const INVALID_RESPONSE = "Received an invalid response from the server.";

export class RfpApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "RfpApiError";
    this.status = status;
  }
}

export type RfpTicketStatus =
  | "analyzing"
  | "discarded"
  | "intake_complete"
  | "drafting"
  | "under_evaluation"
  | "needs_human_review"
  | "waiting_for_approval"
  | "done";

export interface RfpEvaluationResult {
  department_id?: string;
  readability?: { pass?: boolean; score?: Record<string, number>; details?: string };
  relevance?: { pass?: boolean; missing_aspects?: string[] };
  compliance?: { pass?: boolean; rule_ids?: string[]; violations?: string[]; contains_phi?: boolean };
  overall_pass?: boolean;
  feedback_for_generator?: string;
  needs_human_review?: boolean;
  iteration?: number;
  last_decision?: { decision?: string; comment?: string; capped?: boolean };
  arbitration?: Array<{
    trigger_id?: string;
    arbiter?: string;
    action?: string;
    instruction?: string;
    affected_departments?: string[];
  }>;
}

export interface RfpMetadata {
  client_name: string | null;
  client_country: string;
  program_type: string;
  covered_population: number | null;
  deadline: string | null;
  budget_range: string | null;
  currency: string | null;
  departments_needed: string[];
  readability: Record<string, number>;
}

export interface RfpTicket {
  ticket_id: string;
  rfp_id: string | null;
  status: RfpTicketStatus;
  discard_reason: string | null;
  error_code: string | null;
  phi_detected: boolean;
  created_at: string;
  updated_at: string;
  metadata: RfpMetadata | null;
  handoff_json: {
    ticket_id: string;
    phi_detected: boolean;
    metadata: Record<string, unknown>;
    departments: Array<{
      department_id: string;
      owner: string;
      key_aspects: string[];
      open_questions: string[];
    }>;
    synthesizer_summary: string;
  } | null;
  part2_handoff_json: {
    ticket_id: string;
    ticket_status: string;
    departments: Array<{
      department_id: string;
      owner: string;
      draft_content: string;
      evaluation_results: RfpEvaluationResult;
      needs_human_review: boolean;
    }>;
  } | null;
  final_document_json: {
    ticket_id: string;
    currency: string;
    generated_at: string;
    sections: Array<{
      department_id: string;
      owner: string;
      approver: string;
      approved_at: string;
      draft_content: string;
    }>;
  } | null;
}

export interface RfpSection {
  department_id: string;
  owner: string;
  key_aspects: string[];
  open_questions: string[];
  draft_content: string | null;
  evaluation_results: RfpEvaluationResult | null;
  approval_status: string | null;
  approver: string | null;
  approved_at: string | null;
  blocking_triggers: string[];
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new RfpApiError(INVALID_RESPONSE, response.status);
  }
}

export async function uploadRfpPdf(file: File): Promise<{ ticket_id: string; status: RfpTicketStatus }> {
  const body = new FormData();
  body.append("file", file);
  let response: Response;
  try {
    response = await authFetch("/api/rfp/tickets", { method: "POST", body });
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to upload the RFP.", response.status);
  }
  const payload = (await readJson(response)) as { ticket_id?: unknown; status?: unknown };
  if (typeof payload.ticket_id !== "string" || !payload.ticket_id) {
    throw new RfpApiError(INVALID_RESPONSE, response.status);
  }
  return { ticket_id: payload.ticket_id, status: "analyzing" };
}

export async function getRfpTicket(ticketId: string): Promise<RfpTicket> {
  let response: Response;
  try {
    response = await authFetch(`/api/rfp/tickets/${ticketId}`);
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to load the ticket.", response.status);
  }
  return (await readJson(response)) as RfpTicket;
}

export async function getRfpSections(ticketId: string): Promise<RfpSection[]> {
  let response: Response;
  try {
    response = await authFetch(`/api/rfp/tickets/${ticketId}/sections`);
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to load department sections.", response.status);
  }
  const payload = (await readJson(response)) as { sections?: RfpSection[] };
  return payload.sections ?? [];
}

export async function startRfpDraft(ticketId: string): Promise<{ ticket_id: string; status: RfpTicketStatus }> {
  let response: Response;
  try {
    response = await authFetch(`/api/rfp/tickets/${ticketId}/draft`, { method: "POST" });
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to start draft generation.", response.status);
  }
  const payload = (await readJson(response)) as { ticket_id?: unknown; status?: unknown };
  if (typeof payload.ticket_id !== "string" || !payload.ticket_id) {
    throw new RfpApiError(INVALID_RESPONSE, response.status);
  }
  const status = typeof payload.status === "string" ? (payload.status as RfpTicketStatus) : "drafting";
  return { ticket_id: payload.ticket_id, status };
}

export async function startRfpApprovals(ticketId: string): Promise<{ ticket_id: string; status: RfpTicketStatus }> {
  let response: Response;
  try {
    response = await authFetch(`/api/rfp/tickets/${ticketId}/approvals`, { method: "POST" });
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to start department approval.", response.status);
  }
  const payload = (await readJson(response)) as { ticket_id?: unknown; status?: unknown };
  if (typeof payload.ticket_id !== "string" || !payload.ticket_id) {
    throw new RfpApiError(INVALID_RESPONSE, response.status);
  }
  const status =
    typeof payload.status === "string" ? (payload.status as RfpTicketStatus) : "waiting_for_approval";
  return { ticket_id: payload.ticket_id, status };
}

export async function submitRfpDecision(
  ticketId: string,
  departmentId: string,
  decision: "approve" | "request_changes" | "reject",
  comment?: string,
  draftContent?: string,
): Promise<RfpTicket> {
  let response: Response;
  try {
    response = await authFetch(`/api/rfp/tickets/${ticketId}/approvals/${departmentId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        comment: comment ?? null,
        draft_content: draftContent ?? null,
      }),
    });
  } catch (error) {
    throw new RfpApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }
  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new RfpApiError(raw || "Unable to record that decision.", response.status);
  }
  return (await readJson(response)) as RfpTicket;
}
