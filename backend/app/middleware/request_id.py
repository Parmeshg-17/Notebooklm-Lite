import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import metrics_collector

logger = logging.getLogger("app.middleware.request_id")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            process_time_ms = (time.perf_counter() - start_time) * 1000
            metrics_collector.record_request(process_time_ms, is_error=(response.status_code >= 400))
        except Exception:
            process_time_ms = (time.perf_counter() - start_time) * 1000
            metrics_collector.record_request(process_time_ms, is_error=True)
            raise

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        # Only log non-health check endpoints to prevent log clutter
        if not request.url.path.endswith("/health"):
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"{response.status_code} ({process_time_ms:.1f}ms)"
            )

        return response

