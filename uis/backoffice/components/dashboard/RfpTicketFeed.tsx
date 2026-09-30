"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { authFetch } from "@healthcore/auth";
import {
  mergeTicketNotices,
  parseTicketEvent,
  RECONNECT_DELAYS_MS,
  ticketStatusLabel,
  type RfpTicketNotice,
} from "@/lib/rfp/ticket-notices";

export function RfpTicketFeed() {
  const [tickets, setTickets] = useState<RfpTicketNotice[]>([]);
  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let attempt = 0;
    let active: AbortController | null = null;

    async function watch() {
      while (!cancelled) {
        active = new AbortController();
        try {
          const list = await loadTicketNotices(active.signal);
          if (cancelled) return;
          setTickets((current) => mergeTicketNotices(current, list));
          await readTicketStream(
            active.signal,
            (notice) => {
              setTickets((current) => mergeTicketNotices(current, [notice]));
            },
            () => {
              attempt = 0;
              setReconnecting(false);
            }
          );
        } catch {
          if (cancelled) return;
        }
        if (cancelled) return;
        const delay = RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
        attempt += 1;
        setReconnecting(true);
        try {
          await sleep(delay, active.signal);
        } catch {
          if (cancelled) return;
        }
      }
    }

    void watch();
    return () => {
      cancelled = true;
      active?.abort();
    };
  }, []);

  return (
    <section
      className="rounded-xl border border-amber-300 bg-amber-50 p-6 shadow-sm"
      aria-labelledby="rfp-tickets-heading"
    >
      <div className="flex items-baseline justify-between gap-3">
        <h3 id="rfp-tickets-heading" className="text-lg font-semibold text-slate-900">
          RFP tickets
        </h3>
        {reconnecting ? <p className="text-sm font-medium text-amber-800">Reconnecting…</p> : null}
      </div>
      <p className="mt-1 text-sm text-slate-600">New institutional requests, as they are registered.</p>
      {tickets.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">No RFP tickets yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-amber-200">
          {tickets.map((ticket) => (
            <li key={ticket.ticket_id}>
              <Link
                href="/rfp"
                className="flex items-center justify-between gap-4 py-3 text-sm text-slate-900 hover:underline"
              >
                <span className="font-mono">{ticket.ticket_id}</span>
                <span>{ticketStatusLabel(ticket.status)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

async function loadTicketNotices(signal: AbortSignal): Promise<RfpTicketNotice[]> {
  const response = await authFetch("/api/rfp/tickets", { signal, cache: "no-store" });
  if (!response.ok) {
    throw new Error("RFP ticket list failed");
  }
  const body = (await response.json()) as { tickets?: RfpTicketNotice[] };
  return Array.isArray(body.tickets) ? body.tickets : [];
}

async function readTicketStream(
  signal: AbortSignal,
  onTicket: (notice: RfpTicketNotice) => void,
  onOpen: () => void
): Promise<void> {
  const response = await authFetch("/api/rfp/events", { signal, cache: "no-store" });
  if (!response.ok || response.body === null) {
    throw new Error("RFP event stream failed");
  }
  onOpen();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (!signal.aborted) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const notice = parseTicketEvent(frame);
      if (notice) onTicket(notice);
    }
  }
  throw new Error("RFP event stream closed");
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("aborted", "AbortError"));
      },
      { once: true }
    );
  });
}
