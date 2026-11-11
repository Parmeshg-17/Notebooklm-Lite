"""
Sliding-Window Rate Limiting Middleware.
Provides defense against brute-force attacks, resource exhaustion, and API quota abuse.
Tracks requests per client IP / authorization identity using memory-efficient sliding windows.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # client_key -> list of request epoch timestamps
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _get_client_key(self, request: Request) -> str:
        """Derive client identity key from authorization token, X-Forwarded-For, or client host."""
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            # Rate limit per token if present
            return f"auth:{hash(auth)}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
            return f"ip:{client_ip}"

        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "anonymous"

    def _get_limit_and_window(self, path: str, method: str) -> Tuple[int, int]:
        """
        Returns (max_requests, window_seconds) based on endpoint sensitivity.
        """
        # Strict auth brute-force protection
        if "/auth/login" in path or "/auth/register" in path:
            return 20, 60

        # AI inference & chat protection
        if "/chat" in path and method == "POST":
            return 45, 60

        # Upload resource protection
        if "/documents" in path and method == "POST":
            return 25, 60

        # General API default
        return 200, 60

    def _clean_expired(self, current_time: float) -> None:
        """Periodically purge expired timestamp entries to prevent memory growth."""
        if current_time - self.last_cleanup < 60:
            return
        cutoff = current_time - 120
        keys_to_delete = []
        for key, timestamps in self.request_history.items():
            self.request_history[key] = [t for t in timestamps if t > cutoff]
            if not self.request_history[key]:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.request_history[key]
        self.last_cleanup = current_time

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Whitelist non-rate-limited monitoring/documentation endpoints
        if path.startswith(("/docs", "/redoc", "/openapi.json")) or path.endswith(("/health", "/metrics")):
            return await call_next(request)

        client_key = self._get_client_key(request)
        rate_key = f"{client_key}:{path}"
        max_requests, window_seconds = self._get_limit_and_window(path, request.method)

        now = time.time()
        self._clean_expired(now)

        window_start = now - window_seconds
        timestamps = [t for t in self.request_history[rate_key] if t > window_start]

        if len(timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - timestamps[0])) + 1
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": max(1, retry_after),
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )
            return response

        # Record this request
        timestamps.append(now)
        self.request_history[rate_key] = timestamps

        response = await call_next(request)
        remaining = max(0, max_requests - len(timestamps))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

