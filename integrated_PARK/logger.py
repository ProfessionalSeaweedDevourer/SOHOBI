"""
구조화 로거 — Sign-off 거부 이력 및 전체 요청 기록
로그 위치: logs/queries.jsonl   (전체 요청)
           logs/rejections.jsonl (거부 이력이 있는 요청만)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

_LOGS_DIR = Path(os.environ.get("LOGS_DIR", Path(__file__).parent / "logs"))
_QUERIES_LOG    = _LOGS_DIR / "queries.jsonl"
_REJECTIONS_LOG = _LOGS_DIR / "rejections.jsonl"
_ERRORS_LOG     = _LOGS_DIR / "errors.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _append(path: Path, record: dict) -> None:
    _LOGS_DIR.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_query(
    *,
    request_id: str,
    session_id: str = "",
    question: str,
    domain: str,
    status: str,
    grade: str = "",
    retry_count: int,
    rejection_history: list[dict],
    draft: str,
    latency_ms: float,
) -> None:
    """모든 /api/v1/query 요청을 queries.jsonl 에 기록한다."""

    record = {
        "ts":               _now_iso(),
        "session_id":       session_id,
        "request_id":       request_id,
        "question":         question,
        "domain":           domain,
        "status":           status,
        "grade":            grade,
        "retry_count":      retry_count,
        "latency_ms":       round(latency_ms),
        "rejection_history": _format_rejection_history(rejection_history),
        "final_draft":      draft,
    }
    _append(_QUERIES_LOG, record)

    # 거부 이력이 하나라도 있으면 rejections.jsonl 에도 기록
    if rejection_history:
        _append(_REJECTIONS_LOG, record)


def log_error(
    *,
    request_id: str = "",
    session_id: str = "",
    question: str,
    domain: str = "unknown",
    error: str,
    latency_ms: float = 0,
) -> None:
    """응답 생성 실패(예외) 발생 시 errors.jsonl 에 기록한다."""
    record = {
        "ts":         _now_iso(),
        "session_id": session_id,
        "request_id": request_id,
        "question":   question,
        "domain":     domain,
        "error":      error,
        "latency_ms": round(latency_ms),
    }
    _append(_ERRORS_LOG, record)


def _format_rejection_history(history: list[dict]) -> list[dict]:
    """orchestrator rejection_history → 읽기 쉬운 형태로 변환."""
    formatted = []
    for entry in history:
        attempt   = entry.get("attempt")
        verdict   = entry.get("verdict", {})
        formatted.append({
            "attempt":      attempt,
            "approved":     verdict.get("approved"),
            "grade":        verdict.get("grade", ""),
            "passed":       verdict.get("passed", []),
            "warnings": [
                {
                    "code":   w.get("code"),
                    "reason": w.get("reason"),
                }
                for w in verdict.get("warnings", [])
            ],
            "issues": [
                {
                    "code":   issue.get("code"),
                    "reason": issue.get("reason"),
                }
                for issue in verdict.get("issues", [])
            ],
            "retry_prompt": verdict.get("retry_prompt", ""),
        })
    return formatted
