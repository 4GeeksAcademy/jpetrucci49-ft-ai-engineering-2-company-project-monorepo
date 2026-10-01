"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { getToken } from "@healthcore/auth";
import {
  applyDeskFrame,
  deskSocketUrl,
  RECONNECT_DELAYS_MS,
  type DeskChatFrame,
  type DeskChatMessage,
} from "@/lib/knowledge/desk-chat";

const EXAMPLES = [
  "Is there a charge for cancelling 12 hours in advance?",
  "What do I need to bring to my first appointment?",
];
const SESSION_KEY = "healthcore.desk.session_id";

export function DeskKnowledgePage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<DeskChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const generatingRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let attempt = 0;
    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const sessionId = readSessionId();

    function connect() {
      if (cancelled) return;
      const token = getToken();
      if (!token) {
        setError("Sign in again to ask the desk.");
        return;
      }
      socket = new WebSocket(deskSocketUrl(sessionId, token));
      socketRef.current = socket;
      socket.onopen = () => {
        attempt = 0;
        setReconnecting(false);
        setError(null);
      };
      socket.onmessage = (event) => {
        let frame: DeskChatFrame;
        try {
          frame = JSON.parse(String(event.data)) as DeskChatFrame;
        } catch {
          return;
        }
        if (frame.type === "error") {
          setGenerating(false);
          setError(frame.detail || "Unable to get an answer from the knowledge base.");
          return;
        }
        if (frame.type === "generation_completed") {
          generatingRef.current = false;
          setGenerating(false);
        } else if (frame.type === "generation_interrupted") {
          setGenerating(generatingRef.current);
        }
        setMessages((current) => applyDeskFrame(current, frame));
      };
      socket.onclose = () => {
        if (cancelled) return;
        setReconnecting(true);
        const delay = RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
        attempt += 1;
        timer = setTimeout(connect, delay);
      };
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      socketRef.current = null;
      socket?.close();
    };
  }, []);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    const socket = socketRef.current;
    if (!text || socket === null || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    const payload = generatingRef.current
      ? { type: "interrupt", new_input: text }
      : { type: "user_message", text };
    generatingRef.current = true;
    socket.send(JSON.stringify(payload));
    setGenerating(true);
    setError(null);
    setQuestion("");
  }

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-2xl font-semibold text-slate-900">Desk knowledge</h2>
          {reconnecting ? <p className="text-sm font-medium text-amber-800">Reconnecting…</p> : null}
        </div>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          For Priya Nair’s patient coordinators. Answers come from HealthCore appointment,
          insurance, referral, and new-patient policies — never from a raw search dump.
        </p>
      </header>

      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" aria-live="polite">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-500">Ask a policy question. The answer appears as it is written.</p>
        ) : (
          <ol className="space-y-3">
            {messages.map((message) => (
              <li key={message.id} className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {message.role === "user" ? "You" : "Compliance assistant"}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-slate-900">{message.text}</p>
                {message.status === "interrupted" ? (
                  <p className="mt-1 text-xs font-medium text-amber-800">Interrupted</p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </section>

      <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="desk-question" className="block text-sm font-medium text-slate-800">
          Question
        </label>
        <textarea
          id="desk-question"
          name="question"
          rows={3}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={EXAMPLES[0]}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
        />
        <p className="text-xs text-slate-500">
          Example: {EXAMPLES[1]}. Sending while a reply is still arriving stops that reply.
        </p>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          {generating ? "Send" : "Ask"}
        </button>
      </form>
    </div>
  );
}

function readSessionId(): string {
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = window.crypto.randomUUID();
  window.sessionStorage.setItem(SESSION_KEY, created);
  return created;
}
