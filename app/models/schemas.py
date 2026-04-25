from __future__ import annotations

from pydantic import BaseModel, Field


class DiffRequest(BaseModel):
    old_document: str = Field(..., min_length=1)
    new_document: str = Field(..., min_length=1)
    model_name: str = Field(default="all-MiniLM-L6-v2")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class RuleHitOut(BaseModel):
    rule_id: str
    severity: str
    description: str
    old_snippet: str | None = None
    new_snippet: str | None = None


class RiskScoreOut(BaseModel):
    semantic_score: float
    rule_score: int
    structural_score: int
    combined: float
    level: str
    drivers: list[str]


class ClauseDiffOut(BaseModel):
    change_type: str
    match_type: str
    old_id: str | None = None
    new_id: str | None = None
    old_heading: str | None = None
    new_heading: str | None = None
    old_text: str | None = None
    new_text: str | None = None
    similarity: float | None = None
    risk: RiskScoreOut
    rule_hits: list[RuleHitOut]
    summary: str


class DiffResponse(BaseModel):
    total_clauses_old: int
    total_clauses_new: int
    added: int
    removed: int
    modified: int
    unchanged: int
    overall_risk: str
    summary: str
    diffs: list[ClauseDiffOut]


class HealthResponse(BaseModel):
    status: str
    version: str
