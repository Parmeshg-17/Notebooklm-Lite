"""
Production Security Headers Middleware.
Applies defense-in-depth HTTP response headers adhering to OWASP API Security guidelines:
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY (clickjacking protection)
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
- Strips Server & X-Powered-By leakage
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if not settings.SECURITY_HEADERS_ENABLED:
            return response

        # HSTS (HTTP Strict Transport Security) - 1 year, include subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Clickjacking & Framing prevention
        response.headers["X-Frame-Options"] = "DENY"

        # MIME Sniffing protection
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Cross-Site Scripting filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Browser capability isolation
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # Content-Security-Policy for API responses
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "font-src 'self' data:; "
                "connect-src 'self' https: ws:; "
                "frame-ancestors 'none'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )

        # Remove information leakage headers
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response

