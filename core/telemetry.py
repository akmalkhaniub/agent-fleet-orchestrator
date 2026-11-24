import datetime
import json
import os
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional


def generate_trace_id() -> str:
    """Return a W3C 32-char lowercase hex trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Return a W3C 16-char lowercase hex span ID."""
    return uuid.uuid4().hex[:16]


def format_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    """Format a W3C Trace Context traceparent header (version 00)."""
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"


def parse_traceparent(header: Optional[str]) -> Optional[Dict[str, str]]:
    """Parse a W3C traceparent header into trace_id, parent_span_id, and flags."""
    if not header:
        return None
    parts = header.strip().split("-")
    if len(parts) != 4 or len(parts[1]) != 32 or len(parts[2]) != 16:
        return None
    return {
        "version": parts[0],
        "trace_id": parts[1],
        "parent_span_id": parts[2],
        "flags": parts[3],
    }


class TelemetryTracer:
    """Lightweight OpenTelemetry GenAI semantic-convention span recorder."""

    def __init__(self, coordination_dir: Optional[str] = None, service_name: str = "agent-fleet-orchestrator"):
        self.coordination_dir = coordination_dir
        self.service_name = service_name
        self.spans: list[Dict[str, Any]] = []

    @contextmanager
    def start_span(
        self,
        name: str,
        parent_traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Record an OTel-compatible span with W3C traceparent propagation."""
        parsed = parse_traceparent(parent_traceparent)
        trace_id = parsed["trace_id"] if parsed else generate_trace_id()
        parent_span_id = parsed["parent_span_id"] if parsed else None
        span_id = generate_span_id()
        traceparent = format_traceparent(trace_id, span_id)

        start_ns = time.perf_counter_ns()
        start_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        span: Dict[str, Any] = {
            "name": name,
            "service": self.service_name,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "traceparent": traceparent,
            "start_time": start_iso,
            "status": "OK",
            "attributes": dict(attributes or {}),
        }
        try:
            yield span
        except Exception as exc:
            span["status"] = "ERROR"
            span["attributes"]["error.type"] = type(exc).__name__
            span["attributes"]["error.message"] = str(exc)
            raise
        finally:
            end_ns = time.perf_counter_ns()
            span["end_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            span["duration_ms"] = round((end_ns - start_ns) / 1_000_000, 3)
            self.spans.append(span)
            self._persist_span(span)

    def _persist_span(self, span: Dict[str, Any]) -> None:
        if not self.coordination_dir:
            return
        os.makedirs(self.coordination_dir, exist_ok=True)
        trace_file = os.path.join(self.coordination_dir, "traces.jsonl")
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(span) + "\n")
