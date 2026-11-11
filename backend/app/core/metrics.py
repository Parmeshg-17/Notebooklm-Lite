import time
from typing import Any, Dict, List


class MetricsCollector:
    """In-memory telemetry and observability metrics collector."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.latencies_ms: List[float] = []
        self.total_tokens = 0
        self.ingested_documents = 0
        self.start_time = time.time()

    def record_request(self, latency_ms: float, is_error: bool = False):
        self.request_count += 1
        if is_error:
            self.error_count += 1
        self.latencies_ms.append(latency_ms)
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]

    def record_tokens(self, count: int):
        self.total_tokens += count

    def record_ingestion(self):
        self.ingested_documents += 1

    def get_percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * p)
        idx = min(idx, len(sorted_l) - 1)
        return round(sorted_l[idx], 2)

    def get_summary(self) -> Dict[str, Any]:
        uptime_s = round(time.time() - self.start_time, 1)
        p50 = self.get_percentile(0.50)
        p95 = self.get_percentile(0.95)
        avg = round(sum(self.latencies_ms) / len(self.latencies_ms), 2) if self.latencies_ms else 0.0

        return {
            "uptime_seconds": uptime_s,
            "requests_total": self.request_count,
            "requests_error": self.error_count,
            "error_rate": round(self.error_count / max(self.request_count, 1), 4),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "latency_avg_ms": avg,
            "total_tokens_consumed": self.total_tokens,
            "ingested_documents_count": self.ingested_documents,
        }

    def to_prometheus(self) -> str:
        s = self.get_summary()
        lines = [
            "# HELP http_requests_total Total number of HTTP requests",
            "# TYPE http_requests_total counter",
            f"http_requests_total {s['requests_total']}",
            "# HELP http_requests_errors Total number of HTTP error responses",
            "# TYPE http_requests_errors counter",
            f"http_requests_errors {s['requests_error']}",
            "# HELP http_latency_p50_ms P50 latency in ms",
            "# TYPE http_latency_p50_ms gauge",
            f"http_latency_p50_ms {s['latency_p50_ms']}",
            "# HELP http_latency_p95_ms P95 latency in ms",
            "# TYPE http_latency_p95_ms gauge",
            f"http_latency_p95_ms {s['latency_p95_ms']}",
            "# HELP rag_tokens_total Total tokens consumed",
            "# TYPE rag_tokens_total counter",
            f"rag_tokens_total {s['total_tokens_consumed']}",
            "# HELP documents_ingested_total Total documents indexed",
            "# TYPE documents_ingested_total counter",
            f"documents_ingested_total {s['ingested_documents_count']}",
        ]
        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()

