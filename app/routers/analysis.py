"""Legal document analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, UploadFile, File, status

from app.config import settings
from app.diff.engine import ChangeType, diff_documents
from app.models.schemas import (
    ClauseDiffOut, DiffRequest, DiffResponse, RiskScoreOut, RuleHitOut,
)

router = APIRouter(prefix="/v1", tags=["analysis"])


def _build_response(result) -> DiffResponse:
    diffs_out = []
    for d in result.diffs:
        rule_hits_out = [
            RuleHitOut(
                rule_id=h.rule_id,
                severity=h.severity.value,
                description=h.description,
                old_snippet=h.old_snippet,
                new_snippet=h.new_snippet,
            )
            for h in d.rule_hits
        ]
        risk_out = RiskScoreOut(
            semantic_score=d.risk.semantic_score,
            rule_score=d.risk.rule_score,
            structural_score=d.risk.structural_score,
            combined=d.risk.combined,
            level=d.risk.level,
            drivers=d.risk.drivers,
        )
        diffs_out.append(ClauseDiffOut(
            change_type=d.change_type.value,
            match_type=d.match_type,
            old_id=d.old_clause.id if d.old_clause else None,
            new_id=d.new_clause.id if d.new_clause else None,
            old_heading=d.old_clause.heading if d.old_clause else None,
            new_heading=d.new_clause.heading if d.new_clause else None,
            old_text=d.old_clause.text if d.old_clause else None,
            new_text=d.new_clause.text if d.new_clause else None,
            similarity=d.similarity,
            risk=risk_out,
            rule_hits=rule_hits_out,
            summary=d.summary,
        ))

    return DiffResponse(
        total_clauses_old=result.total_clauses_old,
        total_clauses_new=result.total_clauses_new,
        added=len(result.added),
        removed=len(result.removed),
        modified=len(result.modified),
        unchanged=sum(1 for d in result.diffs if d.change_type == ChangeType.UNCHANGED),
        overall_risk=result.overall_risk,
        summary=result.summary,
        diffs=diffs_out,
    )


@router.post("/diff", response_model=DiffResponse, summary="Semantic diff two legal documents (JSON)")
async def diff_json(req: DiffRequest) -> DiffResponse:
    if len(req.old_document.encode()) > settings.max_document_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "old_document exceeds size limit")
    if len(req.new_document.encode()) > settings.max_document_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "new_document exceeds size limit")
    result = diff_documents(
        req.old_document, req.new_document,
        model_name=req.model_name,
        similarity_threshold=req.similarity_threshold,
    )
    return _build_response(result)


@router.post("/diff/upload", response_model=DiffResponse, summary="Semantic diff via file upload")
async def diff_upload(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...),
    similarity_threshold: float = Form(default=0.85),
) -> DiffResponse:
    old_bytes = await old_file.read()
    new_bytes = await new_file.read()
    if len(old_bytes) > settings.max_document_bytes or len(new_bytes) > settings.max_document_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 5 MB limit")
    result = diff_documents(
        old_bytes.decode("utf-8", errors="replace"),
        new_bytes.decode("utf-8", errors="replace"),
        model_name=settings.model_name,
        similarity_threshold=similarity_threshold,
    )
    return _build_response(result)


@router.get("/risk-terms", summary="List tracked high-risk legal terms and rules")
async def risk_terms() -> dict:
    return {
        "rules": [
            {"id": "obligation.shall_to_may", "severity": "critical", "description": "shall → may: obligation weakened"},
            {"id": "liability.shield_removed", "severity": "critical", "description": "Liability limitation removed"},
            {"id": "dispute.arbitration_added", "severity": "critical", "description": "Arbitration clause added"},
            {"id": "rights.waiver_added", "severity": "critical", "description": "Waiver of rights added"},
            {"id": "penalty.added", "severity": "high", "description": "Penalty/damages clause added"},
            {"id": "penalty.amount_change", "severity": "high", "description": "Financial amounts changed"},
            {"id": "deadline.changed", "severity": "medium-high", "description": "Time deadline changed"},
            {"id": "dispute.jurisdiction_changed", "severity": "high", "description": "Governing law/jurisdiction changed"},
            {"id": "scope.irrevocable_added", "severity": "critical", "description": "Irrevocable scope added"},
            {"id": "rights.indemnity_added", "severity": "high", "description": "Indemnification obligation added"},
        ]
    }
