"""
피드백 라우터
- POST /api/feedback  — 사용자 인라인 피드백을 Cosmos DB에 저장한다.

Cosmos DB 구조:
  Database  : COSMOS_DATABASE (기본값 "sohobi")
  Container : "feedback"
  Partition : /agent_type
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

_logger = logging.getLogger("sohobi.feedback")

router = APIRouter()

# ── Cosmos DB 연결 싱글턴 ──────────────────────────────────────────
_feedback_container = None
_feedback_client = None


async def _get_feedback_container():
    global _feedback_container
    if _feedback_container is not None:
        return _feedback_container

    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None  # 로컬 개발: 폴백 모드

    from azure.cosmos.aio import CosmosClient
    from azure.cosmos import PartitionKey
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")

    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)

    # 컨테이너가 없으면 생성
    _feedback_container = await db.create_container_if_not_exists(
        id="feedback",
        partition_key=PartitionKey(path="/agent_type"),
    )

    global _feedback_client
    _feedback_client = client
    return _feedback_container


# ── 인메모리 폴백 ──────────────────────────────────────────────────
_feedback_fallback: list = []


# ── 스키마 ────────────────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    session_id:           str
    agent_type:           str   # admin | finance | legal | location | chat
    message_id:           str
    feedback_type:        str   # positive | negative
    tags:                 Optional[List[str]] = []
    conversation_context: Optional[str] = None
    timestamp:            str


# ── 엔드포인트 ────────────────────────────────────────────────────
@router.get("/api/feedback")
async def get_feedback(limit: int = 500):
    """저장된 피드백 목록을 반환한다 (로그 뷰어용)."""
    container = await _get_feedback_container()
    if container is not None:
        results = []
        query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
        async for item in container.query_items(
            query=query,
            enable_cross_partition_query=True,
        ):
            results.append(item)
    else:
        results = _feedback_fallback[-limit:] if limit > 0 else list(_feedback_fallback)
    return {"count": len(results), "items": results}


@router.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """사용자 인라인 피드백을 Cosmos DB(또는 인메모리)에 저장한다."""
    document = {
        "id":                   str(uuid4()),
        "session_id":           feedback.session_id,
        "agent_type":           feedback.agent_type,
        "message_id":           feedback.message_id,
        "feedback_type":        feedback.feedback_type,
        "tags":                 feedback.tags or [],
        "conversation_context": feedback.conversation_context,
        "timestamp":            feedback.timestamp,
        "created_at":           datetime.now(timezone.utc).isoformat(),
    }

    container = await _get_feedback_container()
    if container is not None:
        await container.create_item(body=document)
    else:
        _feedback_fallback.append(document)
        _logger.debug("피드백 인메모리 저장 (Cosmos DB 미설정): %s", document["id"])

    return {"status": "ok", "id": document["id"]}
