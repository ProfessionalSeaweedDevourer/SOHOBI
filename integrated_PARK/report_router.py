"""
사용 리포트 라우터
- GET /api/report/{session_id}  — 사용 통계 집계 반환

집계 소스:
  usage_events 컨테이너  : 에이전트별 쿼리 횟수 (partition /session_id)
  feedback 컨테이너      : positive/negative 비율 (partition /agent_type)
  checklist 컨테이너     : 진행률 + 미완료 항목 (partition /session_id)
"""

import logging
import os

from fastapi import APIRouter

_logger = logging.getLogger("sohobi.report")

router = APIRouter()

# ── Cosmos DB 클라이언트 헬퍼 ──────────────────────────────────────
async def _get_container(container_name: str, partition_path: str):
    """컨테이너 클라이언트를 반환한다. COSMOS_ENDPOINT 미설정 시 None."""
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None

    from azure.cosmos.aio import CosmosClient
    from azure.cosmos import PartitionKey
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")
    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)
    container = await db.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path=partition_path),
    )
    return container


# ── 인메모리 폴백 참조 (각 라우터 모듈에서 가져옴) ─────────────────
def _get_fallback_events():
    try:
        from event_router import _events_fallback
        return list(_events_fallback)
    except Exception:
        return []


def _get_fallback_feedback():
    try:
        from feedback_router import _feedback_fallback
        return list(_feedback_fallback)
    except Exception:
        return []


def _get_fallback_checklist(session_id: str):
    try:
        from checklist_store import _checklist_memory
        data = _checklist_memory.get(session_id)
        return data["items"] if data else {}
    except Exception:
        return {}


# ── 집계 함수 ──────────────────────────────────────────────────────
async def _aggregate_events(session_id: str) -> dict:
    """session_id 기준 에이전트별 쿼리 횟수를 반환한다."""
    container = await _get_container("usage_events", "/session_id")

    counts: dict[str, int] = {}
    total = 0

    if container is not None:
        query = "SELECT c.agent_type FROM c WHERE c.session_id = @sid"
        params = [{"name": "@sid", "value": session_id}]
        async for item in container.query_items(
            query=query,
            parameters=params,
            partition_key=session_id,
        ):
            agent = item.get("agent_type") or "unknown"
            counts[agent] = counts.get(agent, 0) + 1
            total += 1
    else:
        for ev in _get_fallback_events():
            if ev.get("session_id") == session_id:
                agent = ev.get("agent_type") or "unknown"
                counts[agent] = counts.get(agent, 0) + 1
                total += 1

    return {"total": total, "by_agent": counts}


async def _aggregate_feedback(session_id: str) -> dict:
    """session_id 기준 피드백 집계를 반환한다."""
    container = await _get_container("feedback", "/agent_type")

    positive = 0
    negative = 0

    if container is not None:
        query = "SELECT c.feedback_type FROM c WHERE c.session_id = @sid"
        params = [{"name": "@sid", "value": session_id}]
        async for item in container.query_items(
            query=query,
            parameters=params,
        ):
            if item.get("feedback_type") == "positive":
                positive += 1
            else:
                negative += 1
    else:
        for fb in _get_fallback_feedback():
            if fb.get("session_id") == session_id:
                if fb.get("feedback_type") == "positive":
                    positive += 1
                else:
                    negative += 1

    total = positive + negative
    positive_rate = round(positive / total, 3) if total > 0 else None

    return {
        "positive": positive,
        "negative": negative,
        "total": total,
        "positive_rate": positive_rate,
    }


async def _aggregate_checklist(session_id: str) -> dict:
    """session_id 기준 체크리스트 집계를 반환한다."""
    from checklist_store import get_checklist, CHECKLIST_ITEM_IDS

    doc = await get_checklist(session_id)
    items = doc.get("items", {})

    completed_ids = [
        item_id for item_id in CHECKLIST_ITEM_IDS
        if items.get(item_id, {}).get("checked")
    ]
    incomplete_ids = [
        item_id for item_id in CHECKLIST_ITEM_IDS
        if not items.get(item_id, {}).get("checked")
    ]
    total = len(CHECKLIST_ITEM_IDS)
    completed = len(completed_ids)

    return {
        "completed": completed,
        "total": total,
        "progress_pct": round(completed / total * 100, 1) if total > 0 else 0,
        "completed_items": completed_ids,
        "incomplete_items": incomplete_ids,
    }


# ── 엔드포인트 ────────────────────────────────────────────────────
@router.get("/api/report/{session_id}")
async def get_report(session_id: str):
    """
    session_id의 사용 통계를 집계해 반환한다.

    응답 필드:
      total_queries   : 총 이벤트 수
      agent_usage     : 에이전트별 이용 횟수 dict
      feedback        : positive/negative/total/positive_rate
      checklist       : completed/total/progress_pct/incomplete_items
    """
    try:
        import asyncio
        events_data, feedback_data, checklist_data = await asyncio.gather(
            _aggregate_events(session_id),
            _aggregate_feedback(session_id),
            _aggregate_checklist(session_id),
        )
    except Exception as e:
        _logger.error("report 집계 실패 session_id=%s: %s", session_id, e)
        return {
            "session_id": session_id,
            "error": "집계 중 오류가 발생했습니다.",
        }

    return {
        "session_id":    session_id,
        "total_queries": events_data["total"],
        "agent_usage":   events_data["by_agent"],
        "feedback":      feedback_data,
        "checklist":     checklist_data,
    }
