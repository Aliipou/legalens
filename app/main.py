"""LegaLens — semantic legal document diff API."""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.models.schemas import HealthResponse
from app.routers.analysis import router as analysis_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("legalens")

app = FastAPI(
    title="LegaLens",
    description=(
        "Legal reasoning and change intelligence engine. "
        "Detects obligation shifts, liability changes, deadline modifications, "
        "arbitration clauses, and 15+ other high-risk legal patterns."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analysis_router)

_start_time = time.time()


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="2.0.0")


@app.get("/ready", tags=["meta"])
async def readiness() -> dict:
    return {"status": "ready", "uptime_seconds": round(time.time() - _start_time, 1)}


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"service": "legalens", "version": "2.0.0", "docs": "/docs"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
