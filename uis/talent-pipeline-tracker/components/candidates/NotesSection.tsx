"use client";

import { useState } from "react";
import { createNote, deleteNote, fetchNotes } from "@/lib/api/notes";
import { validateNoteContent } from "@/lib/validation";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Field, TextArea } from "@/components/ui/Field";
import type { NoteOut } from "@/types/note";

interface NotesSectionProps {
  recordId: string;
  initialNotes: NoteOut[];
}

export function NotesSection({ recordId, initialNotes }: NotesSectionProps) {
  const [notes, setNotes] = useState(initialNotes);
  const [content, setContent] = useState("");
  const [contentError, setContentError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refreshNotes = async () => {
    const response = await fetchNotes(recordId);
    setNotes(response.data);
  };

  const handleAddNote = async (event: React.FormEvent) => {
    event.preventDefault();
    const error = validateNoteContent(content);
    setContentError(error);
    if (error) return;

    setIsSubmitting(true);
    setMutationError(null);
    setSuccessMessage(null);
    try {
      await createNote(recordId, { content: content.trim() });
      setContent("");
      setSuccessMessage("Note added.");
      await refreshNotes();
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : "Could not add note.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    setDeletingId(noteId);
    setMutationError(null);
    setSuccessMessage(null);
    try {
      await deleteNote(recordId, noteId);
      setNotes((current) => current.filter((note) => note.id !== noteId));
      setSuccessMessage("Note deleted.");
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : "Could not delete note.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Internal notes</h2>
        <p className="text-sm text-slate-600">Capture call and interview notes for the People team.</p>
      </div>

      {mutationError ? <Alert variant="error">{mutationError}</Alert> : null}
      {successMessage ? <Alert variant="success">{successMessage}</Alert> : null}

      <ul className="space-y-3">
        {notes.length === 0 ? (
          <li className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-600">
            No notes yet for this candidate.
          </li>
        ) : (
          notes.map((note) => (
            <li key={note.id} className="rounded-lg border border-slate-200 px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-800">{note.content}</p>
                  <p className="mt-2 text-xs text-slate-500">{new Date(note.created_at).toLocaleString()}</p>
                </div>
                <Button
                  type="button"
                  variant="danger"
                  className="shrink-0 px-3 py-1.5 text-xs"
                  disabled={deletingId === note.id}
                  onClick={() => void handleDelete(note.id)}
                >
                  {deletingId === note.id ? "Deleting..." : "Delete"}
                </Button>
              </div>
            </li>
          ))
        )}
      </ul>

      <form onSubmit={handleAddNote} className="space-y-3 border-t border-slate-100 pt-4">
        <Field label="Add note" htmlFor="note-content" error={contentError ?? undefined}>
          <TextArea
            id="note-content"
            value={content}
            onChange={(event) => {
              setContent(event.target.value);
              setContentError(null);
            }}
            placeholder="Summary from phone screen, interview, or reference check..."
          />
        </Field>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Adding..." : "Add note"}
        </Button>
      </form>
    </section>
  );
}
