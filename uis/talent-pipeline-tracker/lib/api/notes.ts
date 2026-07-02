import { apiRequest } from "@/lib/api/client";
import type { NoteCreate, NoteOut, NotesListResponse } from "@/types/note";

export function fetchNotes(recordId: string): Promise<NotesListResponse> {
  return apiRequest<NotesListResponse>(`/records/${recordId}/notes`, { method: "GET" });
}

export function createNote(recordId: string, payload: NoteCreate): Promise<NoteOut> {
  return apiRequest<NoteOut>(`/records/${recordId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteNote(recordId: string, noteId: string): Promise<void> {
  return apiRequest<void>(`/records/${recordId}/notes/${noteId}`, { method: "DELETE" });
}
