"""
사용 리포트 라우터
- GET /api/report/me              — 로그인 사용자 전체 세션 합산 리포트
- GET /api/report/{session_id}    — 단일 세션 리포트 (비로그인 폴백)

집계 소스:
  queries.jsonl          : 에이전트별 쿼리 횟수 (domain 필드 사용)
  feedback 컨테이너      : positive/negative 비율 (partition /agent_type)
  checklist 컨테이너     : 진행률 + 미완료 항목 (partition /session_id)
"""

import asyncio
import logging
import os
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from auth import verify_api_key
from auth_router import get_current_user
from checklist_store import CHECKLIST_ITEM_IDS
from log_formatter import load_entries_json
from session_store import get_sessions_by_user, session_exists

_logger = logging.getLogger("sohobi.report")

router = APIRouter()

# ── Cosmos DB 클라이언트 헬퍼 (feedback / checklist 용) ────────────
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


def _get_fallback_feedback():
    try:
        from feedback_router import _feedback_fallback
        return list(_feedback_fallback)
    except Exception:
        return []


# ── 집계 함수 ──────────────────────────────────────────────────────
def _aggregate_events(session_ids: list[str]) -> dict:
    """백엔드 쿼리 로그(queries.jsonl)에서 에이전트별 쿼리 횟수를 집계한다."""
    entries = load_entries_json(log_type="queries", limit=0)
    sid_set = set(session_ids)

    counts: dict[str, int] = {}
    total = 0
    first_ts: str | None = None
    last_ts: str | None = None

    for e in entries:
        if e.get("session_id") not in sid_set:
            continue
        agent = e.get("domain") or "unknown"
        counts[agent] = counts.get(agent, 0) + 1
        total += 1
        ts = e.get("ts")
        if ts:
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts

    most_used = max(counts, key=counts.get) if counts else None
    return {
        "total": total,
        "by_agent": counts,
        "first_active": first_ts,
        "last_active": last_ts,
        "most_used_agent": {"type": most_used, "count": counts[most_used]} if most_used else None,
    }


async def _aggregate_feedback(session_id: str) -> dict:
    """session_id 기준 피드백 집계를 반환한다."""
    container = await _get_container("feedback", "/agent_type")

    positive = 0
    negative = 0

    tag_counter: Counter = Counter()

    if container is not None:
        query = "SELECT c.feedback_type, c.tags FROM c WHERE c.session_id = @sid"
        params = [{"name": "@sid", "value": session_id}]
        async for item in container.query_items(
            query=query,
            parameters=params,
        ):
            if item.get("feedback_type") == "positive":
                positive += 1
            else:
                negative += 1
                for tag in item.get("tags") or []:
                    tag_counter[tag] += 1
    else:
        for fb in _get_fallback_feedback():
            if fb.get("session_id") == session_id:
                if fb.get("feedback_type") == "positive":
                    positive += 1
                else:
                    negative += 1
                    for tag in fb.get("tags") or []:
                        tag_counter[tag] += 1

    total = positive + negative
    positive_rate = round(positive / total, 3) if total > 0 else None
    top_negative_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(5)]

    return {
        "positive": positive,
        "negative": negative,
        "total": total,
        "positive_rate": positive_rate,
        "top_negative_tags": top_negative_tags,
    }


async def _aggregate_checklist(session_id: str) -> dict:
    """session_id 기준 체크리스트 집계를 반환한다."""
    from checklist_store import get_checklist

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


# ── 멀티세션 합산 헬퍼 ─────────────────────────────────────────────
def _merge_feedback(results: list[dict]) -> dict:
    """여러 세션의 피드백 집계를 합산한다."""
    positive = sum(r["positive"] for r in results)
    negative = sum(r["negative"] for r in results)
    total = positive + negative
    tag_counter: Counter = Counter()
    for r in results:
        for t in r.get("top_negative_tags", []):
            tag_counter[t["tag"]] += t["count"]
    return {
        "positive": positive,
        "negative": negative,
        "total": total,
        "positive_rate": round(positive / total, 3) if total > 0 else None,
        "top_negative_tags": [{"tag": t, "count": c} for t, c in tag_counter.most_common(5)],
    }


def _merge_checklist(results: list[dict]) -> dict:
    """여러 세션의 체크리스트를 합산한다 (하나라도 완료면 완료)."""
    completed_set: set[str] = set()
    for r in results:
        completed_set.update(r.get("completed_items", []))
    total = len(CHECKLIST_ITEM_IDS)
    completed = len(completed_set)
    incomplete = [i for i in CHECKLIST_ITEM_IDS if i not in completed_set]
    return {
        "completed": completed,
        "total": total,
        "progress_pct": round(completed / total * 100, 1) if total > 0 else 0,
        "completed_items": list(completed_set),
        "incomplete_items": incomplete,
    }


# ── 엔드포인트 ────────────────────────────────────────────────────

# /api/report/me 를 {session_id} 보다 먼저 선언해야 FastAPI가 "me"를 path param으로 잡지 않음
@router.get("/api/report/me")
async def get_my_report(user: dict = Depends(get_current_user)):
    """로그인 사용자의 전체 세션 합산 리포트."""
    user_id = user["sub"]
    sessions = await get_sessions_by_user(user_id)
    session_ids = [s["session_id"] for s in sessions]

    if not session_ids:
        return {
            "user_id": user_id,
            "total_queries": 0,
            "agent_usage": {},
            "most_used_agent": None,
            "first_active": None,
            "last_active": None,
            "feedback": {"positive": 0, "negative": 0, "total": 0, "positive_rate": None, "top_negative_tags": []},
            "checklist": {"completed": 0, "total": 0, "progress_pct": 0, "completed_items": [], "incomplete_items": []},
        }

    events_data = _aggregate_events(session_ids)

    try:
        feedback_results, checklist_results = await asyncio.gather(
            asyncio.gather(*[_aggregate_feedback(sid) for sid in session_ids]),
            asyncio.gather(*[_aggregate_checklist(sid) for sid in session_ids]),
        )
    except Exception as e:
        _logger.error("report/me 집계 실패 user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="집계 중 오류가 발생했습니다.")

    return {
        "user_id":         user_id,
        "total_queries":   events_data["total"],
        "agent_usage":     events_data["by_agent"],
        "most_used_agent": events_data["most_used_agent"],
        "first_active":    events_data["first_active"],
        "last_active":     events_data["last_active"],
        "feedback":        _merge_feedback(feedback_results),
        "checklist":       _merge_checklist(checklist_results),
    }


@router.get("/api/report/{session_id}", dependencies=[Depends(verify_api_key)])
async def get_report(session_id: str):
    """단일 세션 리포트 (비로그인 폴백)."""
    if not await session_exists(session_id):
        raise HTTPException(status_code=403, detail="접근 권한 없음")

    try:
        events_data = _aggregate_events([session_id])
        feedback_data, checklist_data = await asyncio.gather(
            _aggregate_feedback(session_id),
            _aggregate_checklist(session_id),
        )
    except Exception as e:
        _logger.error("report 집계 실패 session_id=%s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="집계 중 오류가 발생했습니다.")

    return {
        "session_id":      session_id,
        "total_queries":   events_data["total"],
        "agent_usage":     events_data["by_agent"],
        "most_used_agent": events_data["most_used_agent"],
        "first_active":    events_data["first_active"],
        "last_active":     events_data["last_active"],
        "feedback":        feedback_data,
        "checklist":       checklist_data,
    }
