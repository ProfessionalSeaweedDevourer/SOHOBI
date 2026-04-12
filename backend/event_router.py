"""
이벤트 라우터
- POST /api/events  — 사용 이벤트를 Cosmos DB에 저장한다.

Cosmos DB 구조:
  Database  : COSMOS_DATABASE (기본값 "sohobi")
  Container : "usage_events"
  Partition : /session_id
"""

import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

_logger = logging.getLogger("sohobi.events")

router = APIRouter()

# ── Cosmos DB 연결 싱글턴 ──────────────────────────────────────────
_events_container = None
_events_client = None


async def _get_events_container():
    global _events_container
    if _events_container is not None:
        return _events_container

    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None  # 로컬 개발: 폴백 모드

    from azure.cosmos import PartitionKey
    from azure.cosmos.aio import CosmosClient
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")

    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)

    # 컨테이너가 없으면 생성
    _events_container = await db.create_container_if_not_exists(
        id="usage_events",
        partition_key=PartitionKey(path="/session_id"),
    )

    global _events_client
    _events_client = client
    return _events_container


# ── 인메모리 폴백 ──────────────────────────────────────────────────
_events_fallback: list = []


# ── 스키마 ────────────────────────────────────────────────────────
class EventRequest(BaseModel):
    event_name: str
    session_id: str | None = None
    agent_type: str | None = None
    message_id: str | None = None
    page: str | None = None
    timestamp: str | None = None


# ── 엔드포인트 ────────────────────────────────────────────────────
@router.post("/api/events")
async def track_event(event: EventRequest):
    """사용 이벤트를 Cosmos DB(또는 인메모리)에 저장한다."""
    document = {
        "id": str(uuid4()),
        "event_name": event.event_name,
        "session_id": event.session_id or "anonymous",
        "agent_type": event.agent_type,
        "message_id": event.message_id,
        "page": event.page,
        "timestamp": event.timestamp,
        "created_at": datetime.now(UTC).isoformat(),
    }

    container = await _get_events_container()
    if container is not None:
        await container.create_item(body=document)
    else:
        _events_fallback.append(document)
        _logger.debug("이벤트 인메모리 저장 (Cosmos DB 미설정): %s", document["id"])

    return {"status": "ok", "id": document["id"]}
