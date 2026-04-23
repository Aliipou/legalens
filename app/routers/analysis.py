"""Legal document analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status

from app.config import settings
from app.diff.engine import diff_documents, ChangeType
from app.models.schemas import DiffRequest, DiffResponse, ClauseDiffOut

router = APIRouter(prefix="/v1", tags=["analysis"])


def _build_response(result) -> DiffResponse:
    diffs_out = []
    for d in result.diffs:
        diffs_out.append(
            ClauseDiffOut(
                change_type=d.change_type.value,
                old_text=d.old_clause.text if d.old_clause else None,
                new_text=d.new_clause.text if d.new_clause else None,
                similarity=d.similarity,
                semantic_risk=d.semantic_risk,
                key_changes=d.key_changes,
                summary=d.summary,
            )
        )

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
        req.old_document,
        req.new_document,
        model_name=req.model_name,
        similarity_threshold=req.similarity_threshold,
    )
    return _build_response(result)


@router.post("/diff/upload", response_model=DiffResponse, summary="Semantic diff via file upload")
async def diff_upload(
    old_file: UploadFile = File(..., description="Original document (.txt or .md)"),
    new_file: UploadFile = File(..., description="Revised document (.txt or .md)"),
    similarity_threshold: float = Form(default=0.85),
) -> DiffResponse:
    old_bytes = await old_file.read()
    new_bytes = await new_file.read()

    if len(old_bytes) > settings.max_document_bytes or len(new_bytes) > settings.max_document_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 5 MB limit")

    old_text = old_bytes.decode("utf-8", errors="replace")
    new_text = new_bytes.decode("utf-8", errors="replace")

    result = diff_documents(
        old_text, new_text,
        model_name=settings.model_name,
        similarity_threshold=similarity_threshold,
    )
    return _build_response(result)


@router.get("/risk-terms", summary="List tracked high-risk legal terms")
async def risk_terms() -> dict:
    return {
        "terms": [
            "indemnification", "liability", "termination", "arbitration",
            "exclusive", "waiver", "forfeiture", "penalty", "liquidated damages",
            "warranty disclaimer", "irrevocable", "perpetual license",
        ],
        "note": "Clauses containing these terms are flagged as higher risk when modified or removed.",
    }
