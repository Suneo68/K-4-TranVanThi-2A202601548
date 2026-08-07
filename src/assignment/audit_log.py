"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, float] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """Store input + start timestamp keyed by request_id/user_id."""
        import time
        from guardrails.output_guardrails import content_filter
        
        if request_id is None:
            request_id = user_id
            
        # Tối ưu chuẩn thực tế: Redact secret/PII trước khi ghi log
        safe_text = content_filter(text)["redacted"]
        
        self._open[request_id] = {
            "start_time": time.time(),
            "timestamp": utc_now_iso(),
            "user_id": user_id,
            "input_text": safe_text
        }

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
        decision: str | None = None,
    ):
        """Store output, layer decision, latency; append to self.logs."""
        import time
        from guardrails.output_guardrails import content_filter
        
        if request_id is None:
            request_id = user_id
            
        entry = self._open.pop(request_id, {})
        start_time = entry.get("start_time", time.time())
        latency = time.time() - start_time
        
        # Redact secret/PII trước khi ghi log
        safe_text = content_filter(text)["redacted"]
        
        log_record = {
            "request_id": request_id,
            "user_id": user_id,
            "timestamp": entry.get("timestamp", utc_now_iso()),
            "input": entry.get("input_text", ""),
            "output": safe_text,
            "blocked": blocked,
            "layer": layer,
            "decision": decision,
            "latency_ms": round(latency * 1000, 2)
        }
        self.logs.append(log_record)

    def export_json(self, filepath: str = "outputs/audit_log.json"):
        """Write logs to disk (JSON array)."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
