"use client";

import { FormEvent, useState } from "react";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { askDeskKnowledge, KnowledgeApiError } from "@/lib/api/knowledge";

const EXAMPLES = [
  "Is there a charge for cancelling 12 hours in advance?",
  "What do I need to bring to my first appointment?",
];

export function DeskKnowledgePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);

  async function ask(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      setError("Enter a question for the desk knowledge base.");
      setAnswer(null);
      return;
    }
    setIsAsking(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await askDeskKnowledge(trimmed));
    } catch (caught) {
      const message =
        caught instanceof KnowledgeApiError
          ? caught.message
          : "Unable to get an answer from the knowledge base.";
      setError(message);
    } finally {
      setIsAsking(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question);
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">Desk knowledge</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          For Priya Nair’s patient coordinators. Answers come from HealthCore appointment,
          insurance, referral, and new-patient policies — never from a raw search dump.
        </p>
      </header>

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
        <p className="text-xs text-slate-500">Example: {EXAMPLES[1]}</p>
        <button
          type="submit"
          disabled={isAsking}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isAsking ? "Asking…" : "Ask"}
        </button>
      </form>

      {isAsking ? <LoadingState label="Asking the knowledge base…" layout="inline" /> : null}
      {error ? (
        <ErrorState
          message={error}
          onRetry={() => {
            void ask(question);
          }}
          homeHref="/"
        />
      ) : null}
      {!isAsking && answer ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" aria-live="polite">
          <h3 className="text-sm font-semibold text-slate-800">Answer</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{answer}</p>
        </section>
      ) : null}
    </div>
  );
}
