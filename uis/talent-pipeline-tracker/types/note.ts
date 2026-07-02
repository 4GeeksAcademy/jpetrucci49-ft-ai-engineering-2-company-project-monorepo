export interface NoteOut {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
}

export interface NoteCreate {
  content: string;
}

export interface NotesListResponse {
  data: NoteOut[];
  meta: {
    total: number;
  };
}
