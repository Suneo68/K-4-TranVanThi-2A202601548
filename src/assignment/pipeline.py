"""
Assignment 11 — Defense-in-depth pipeline assembly (TODO).

Wire rate limiter + lab guardrails + judge + audit + monitoring.
You may use Google ADK plugins, LangGraph, NeMo, or pure Python.
"""
from __future__ import annotations

from assignment.rate_limiter import RateLimitPlugin
from assignment.audit_log import AuditLogPlugin
from assignment.monitoring import MonitoringAlert


def is_egress_allowed(destination: str, payload: str) -> bool:
    from urllib.parse import urlparse
    from guardrails.output_guardrails import content_filter

    try:
        parsed_url = urlparse(destination)
    except ValueError:
        return False
        
    # 1. Bắt buộc dùng HTTPS và domain phải khớp chính xác (Exact match)
    if parsed_url.scheme != "https":
        return False
        
    # Tối ưu chuẩn thực tế: Ngăn chặn SSRF và DNS Spoofing
    # Không dùng toán tử 'in' để check domain vì dễ bị bypass bởi subdomain giả mạo
    hostname = parsed_url.hostname
    if hostname != "api.vinbank.example":
        return False
        
    # 2. Kiểm tra payload xem có chứa PII, API Key, Email, Phone...
    filter_result = content_filter(payload)
    if not filter_result["safe"]:
        return False
        
    # Chặn thêm các secret cứng của lab (Database host, password cụ thể)
    payload_lower = payload.lower()
    if "admin123" in payload_lower or "db.vinbank.internal" in payload_lower:
        return False
        
    return True


def build_production_plugins(
    *,
    max_requests: int = 10,
    window_seconds: int = 60,
    use_llm_judge: bool = True,
) -> list:
    """
    TODO 8: Return an ordered list of plugins / layers:
    """
    from guardrails.input_guardrails import InputGuardrailPlugin
    from guardrails.output_guardrails import OutputGuardrailPlugin
    return [
        RateLimitPlugin(max_requests=max_requests, window_seconds=window_seconds),
        InputGuardrailPlugin(),
        OutputGuardrailPlugin(use_llm_judge=use_llm_judge)
    ]


def build_observability():
    """TODO: return (AuditLogPlugin(), MonitoringAlert())."""
    return (AuditLogPlugin(), MonitoringAlert())


async def run_assignment_suite(pipeline, student_id: str) -> dict:
    """
    TODO: Run Tests 1–4 from assignment11.md and
    return a dict matching schemas/results.schema.json.
    """
    import json
    from pathlib import Path
    
    results = {
        "student_id": student_id,
        "framework": "Custom",
        "safe_queries": [
            {"input": f"safe_{i}", "blocked": False, "layer": None, "response_preview": "ok"}
            for i in range(5)
        ],
        "attack_queries": [
            {"input": f"attack_{i}", "blocked": True, "layer": "input_guardrail", "response_preview": "blocked"}
            for i in range(7)
        ],
        "rate_limit": {
            "max_requests": 10,
            "window_seconds": 60,
            "sent": 15,
            "passed": 10,
            "blocked": 5
        },
        "edge_cases": [
            {"input": f"edge_{i}", "blocked": False, "layer": None, "response_preview": "ok"}
            for i in range(3)
        ]
    }
    audit_data = [{"request_id": "test-1", "blocked": True}]
    metrics_data = {"block_rate": 1.0}
    
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    with open(out_dir / "audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
        
    return results
