export type RfpTicketNotice = {
  ticket_id: string;
  status: string;
};

export const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];

export function ticketStatusLabel(status: string): string {
  if (status === "analyzing") return "Needs processing";
  return status;
}

/** Prepend unseen tickets. The same ticket_id is never returned twice. */
export function mergeTicketNotices(
  current: RfpTicketNotice[],
  incoming: RfpTicketNotice[]
): RfpTicketNotice[] {
  const known = new Set(current.map((row) => row.ticket_id));
  const incomingById = new Map(incoming.map((row) => [row.ticket_id, row]));
  const fresh = incoming.filter((row) => !known.has(row.ticket_id));
  const kept = current.map((row) => incomingById.get(row.ticket_id) ?? row);
  return [...fresh, ...kept];
}

export function parseTicketEvent(frame: string): RfpTicketNotice | null {
  let eventName = "";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith(":") || line.startsWith("id:")) continue;
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  if (eventName !== "agent_status_changed" || dataLines.length === 0) return null;
  try {
    const payload = JSON.parse(dataLines.join("\n")) as Partial<RfpTicketNotice>;
    if (!payload.ticket_id || !payload.status) return null;
    return { ticket_id: payload.ticket_id, status: payload.status };
  } catch {
    return null;
  }
}
