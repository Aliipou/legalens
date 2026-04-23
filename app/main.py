"""LegaLens — semantic legal document diff API."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import HealthResponse
from app.routers.analysis import router as analysis_router

app = FastAPI(
    title="LegaLens",
    description="Semantic diff engine for legal documents — find what changed and why it matters.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analysis_router)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"service": "legalens", "docs": "/docs"})
