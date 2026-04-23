from __future__ import annotations

from pydantic import BaseModel, Field


class DiffRequest(BaseModel):
    old_document: str = Field(..., min_length=1, description="Original document text")
    new_document: str = Field(..., min_length=1, description="Revised document text")
    model_name: str = Field(default="all-MiniLM-L6-v2", description="Sentence-transformer model")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class ClauseDiffOut(BaseModel):
    change_type: str
    old_text: str | None = None
    new_text: str | None = None
    similarity: float | None = None
    semantic_risk: str
    key_changes: list[str]
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
