from pydantic import BaseModel


class Totals(BaseModel):
    total: int
    valid_count: int
    invalid_count: int


class InvalidBreakdownItem(BaseModel):
    rule: str
    label: str
    count: int


class BreakdownItem(BaseModel):
    code: str
    count: int
    percentage: float


class SatisfactionScoreItem(BaseModel):
    score: int
    label: str
    count: int


class SatisfactionSummary(BaseModel):
    closed_total: int
    scored_total: int
    average_score: float
    scores: list[SatisfactionScoreItem]


class AnalysisResult(BaseModel):
    source_filename: str
    analyzed_at: str
    totals: Totals
    invalid_breakdown: list[InvalidBreakdownItem]
    categories: list[BreakdownItem]
    statuses: list[BreakdownItem]
    countries: list[BreakdownItem]
    satisfaction: SatisfactionSummary
