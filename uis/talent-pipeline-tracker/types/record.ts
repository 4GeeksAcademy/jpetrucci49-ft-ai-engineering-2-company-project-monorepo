export const RECORD_STATUSES = ["received", "in_progress", "selected", "discarded"] as const;
export const RECORD_STAGES = [
  "pending",
  "review",
  "personal_interview",
  "technical_interview",
  "offer_presented",
] as const;

export type RecordStatus = (typeof RECORD_STATUSES)[number];
export type RecordStage = (typeof RECORD_STAGES)[number];

export interface RecordOut {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: string;
  stage: string;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
}

export interface RecordCreate {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  experience_years: number;
  linkedin_url?: string | null;
  cv_url?: string | null;
}

export interface RecordPatch {
  status?: string | null;
  stage?: string | null;
}

export interface RecordsListParams {
  status?: string;
  stage?: string;
  search?: string;
  page?: number;
  limit?: number;
}

export interface RecordsListResponse {
  total: number;
  page: number;
  limit: number;
  data: RecordOut[];
}
