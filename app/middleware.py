"""Request validation, size limiting, and error handling middleware."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_request_counts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 60  # requests per minute per IP


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = [t for t in _request_counts[ip] if now - t < 60]
        window.append(now)
        _request_counts[ip] = window
        if len(window) > _RATE_LIMIT:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Max 60 requests/minute."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
