export interface Totals {
  total: number;
  valid_count: number;
  invalid_count: number;
}

export interface InvalidBreakdownItem {
  rule: string;
  label: string;
  count: number;
}

export interface BreakdownItem {
  code: string;
  count: number;
  percentage: number;
}

export interface SatisfactionScoreItem {
  score: number;
  label: string;
  count: number;
}

export interface SatisfactionSummary {
  closed_total: number;
  scored_total: number;
  average_score: number;
  scores: SatisfactionScoreItem[];
}

export interface AnalysisResult {
  source_filename: string;
  analyzed_at: string;
  totals: Totals;
  invalid_breakdown: InvalidBreakdownItem[];
  categories: BreakdownItem[];
  statuses: BreakdownItem[];
  countries: BreakdownItem[];
  satisfaction: SatisfactionSummary;
}

export class IncidentsApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "IncidentsApiError";
  }
}
