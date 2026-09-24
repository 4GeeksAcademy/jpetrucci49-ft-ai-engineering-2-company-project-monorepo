import { authFetch, parseApiError } from "@healthcore/auth";
import { toUserFacingMessage } from "@healthcore/api/errors";

const NETWORK_ERROR = "Unable to reach the server. Check your connection and try again.";
const INVALID_RESPONSE = "Received an invalid response from the server.";

export class KnowledgeApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "KnowledgeApiError";
    this.status = status;
  }
}

export async function askDeskKnowledge(question: string): Promise<string> {
  let response: Response;
  try {
    response = await authFetch("/api/knowledge/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch (error) {
    throw new KnowledgeApiError(toUserFacingMessage(error, NETWORK_ERROR), 0);
  }

  if (!response.ok) {
    const raw = await parseApiError(response);
    throw new KnowledgeApiError(raw || "Unable to get an answer.", response.status);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new KnowledgeApiError(INVALID_RESPONSE, response.status);
  }

  const answer = (payload as { answer?: unknown }).answer;
  if (typeof answer !== "string" || !answer.trim()) {
    throw new KnowledgeApiError(INVALID_RESPONSE, response.status);
  }
  return answer;
}
