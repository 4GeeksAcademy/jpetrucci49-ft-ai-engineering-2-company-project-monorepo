import { RECORD_STAGES, RECORD_STATUSES, type RecordStage, type RecordStatus } from "@/types/record";

const STATUS_LABELS: Record<RecordStatus, string> = {
  received: "Received",
  in_progress: "In progress",
  selected: "Selected",
  discarded: "Discarded",
};

const STAGE_LABELS: Record<RecordStage, string> = {
  pending: "Pending review",
  review: "Under review",
  personal_interview: "Personal interview",
  technical_interview: "Technical interview",
  offer_presented: "Offer presented",
};

export function getStatusLabel(status: string): string {
  if (isRecordStatus(status)) return STATUS_LABELS[status];
  return status;
}

export function getStageLabel(stage: string): string {
  if (isRecordStage(stage)) return STAGE_LABELS[stage];
  return stage;
}

export function isRecordStatus(value: string): value is RecordStatus {
  return (RECORD_STATUSES as readonly string[]).includes(value);
}

export function isRecordStage(value: string): value is RecordStage {
  return (RECORD_STAGES as readonly string[]).includes(value);
}

export const statusOptions = RECORD_STATUSES.map((value) => ({
  value,
  label: STATUS_LABELS[value],
}));

export const stageOptions = RECORD_STAGES.map((value) => ({
  value,
  label: STAGE_LABELS[value],
}));
