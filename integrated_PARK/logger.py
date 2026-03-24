"""
구조화 로거 — Sign-off 거부 이력 및 전체 요청 기록

BLOB_LOGS_ACCOUNT 환경변수가 설정된 경우 Azure Blob Storage에 기록한다.
없으면 로컬 파일(logs/*.jsonl)로 폴백하므로 로컬 개발에서 추가 설정 불필요.

Blob Storage 구조:
  Storage Account : BLOB_LOGS_ACCOUNT
  Container       : BLOB_LOGS_CONTAINER (기본값 "sohobi-logs")
  Blob            : queries.jsonl | rejections.jsonl | errors.jsonl
  인증            : DefaultAzureCredential (관리형 아이덴티티)
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

# ── Blob Storage 싱글턴 ────────────────────────────────────────
_blob_service = None   # BlobServiceClient (동기)


def _get_blob_service():
    global _blob_service
    if _blob_service is not None:
        return _blob_service

    account = os.environ.get("BLOB_LOGS_ACCOUNT", "")
    if not account:
        return None

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    credential = DefaultAzureCredential()
    _blob_service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=credential,
    )
    return _blob_service


def _blob_append(blob_name: str, record: dict) -> None:
    """Blob Storage append blob에 JSONL 한 줄 추가."""
    service = _get_blob_service()
    container = os.environ.get("BLOB_LOGS_CONTAINER", "sohobi-logs")
    client = service.get_blob_client(container=container, blob=blob_name)

    from azure.core.exceptions import ResourceNotFoundError

    line = json.dumps(record, ensure_ascii=False) + "\n"

    try:
        client.append_block(line.encode("utf-8"))
    except ResourceNotFoundError:
        # 블롭이 없으면 생성 후 재시도
        client.create_append_blob()
        client.append_block(line.encode("utf-8"))


def _local_append(path: Path, record: dict) -> None:
    _LOGS_DIR.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append(local_path: Path, record: dict) -> None:
    service = _get_blob_service()
    if service is not None:
        _blob_append(local_path.name, record)
    else:
        _local_append(local_path, record)


# ── 공개 API ────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


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
