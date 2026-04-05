"""
로드맵 투표 라우터
- GET /api/roadmap/votes?session_id=...  — 기능별 투표 현황 반환
- POST /api/roadmap/vote                 — 투표 토글 (추가/취소)

Cosmos DB 컨테이너: roadmap_votes, 파티션 키: /feature_id
미설정 시 인메모리 폴백 사용.
"""

import logging
import os
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_router import get_optional_user
from session_store import session_exists

_logger = logging.getLogger("sohobi.roadmap")
router = APIRouter()

# ── 기능 목록 (지시문 3-D) ─────────────────────────────────────────
ROADMAP_FEATURES = [
    {"id": "inventory",         "label": "재고 관리 도우미",             "icon": "📦"},
    {"id": "revenue_dashboard", "label": "매출/비용 분석 대시보드",       "icon": "📊"},
    {"id": "tax_guide",         "label": "세무/회계 안내",               "icon": "🧾"},
    {"id": "hr_guide",          "label": "직원 채용/노무 관리 가이드",    "icon": "👥"},
    {"id": "delivery_pos",      "label": "배달앱/POS 연동 매출 통합",     "icon": "📱"},
    {"id": "safety_checklist",  "label": "위생/안전 점검 체크리스트",     "icon": "✅"},
    {"id": "crm",               "label": "단골 고객 관리 (CRM)",         "icon": "💎"},
    {"id": "menu_pricing",      "label": "메뉴 원가 계산 및 가격 최적화", "icon": "🍽️"},
]
_FEATURE_IDS = {f["id"] for f in ROADMAP_FEATURES}

# ── 인메모리 폴백: {feature_id: set(session_ids)} ─────────────────
_votes_fallback: dict[str, set] = defaultdict(set)


# ── Cosmos DB 클라이언트 헬퍼 ──────────────────────────────────────
async def _get_votes_container():
    """roadmap_votes 컨테이너 클라이언트를 반환한다. COSMOS_ENDPOINT 미설정 시 None."""
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    if not endpoint:
        return None

    from azure.cosmos import PartitionKey
    from azure.cosmos.aio import CosmosClient
    from azure.identity.aio import DefaultAzureCredential

    db_name = os.getenv("COSMOS_DATABASE", "sohobi")
    credential = DefaultAzureCredential()
    client = CosmosClient(url=endpoint, credential=credential)
    db = client.get_database_client(db_name)
    return await db.create_container_if_not_exists(
        id="roadmap_votes",
        partition_key=PartitionKey(path="/feature_id"),
    )


# ── 엔드포인트 ────────────────────────────────────────────────────
@router.get("/api/roadmap/votes")
async def get_roadmap_votes(
    session_id: str = "",
    user: dict | None = Depends(get_optional_user),
):
    """모든 기능의 투표 현황과 현재 사용자의 투표 상태를 반환한다."""
    counts: dict[str, int] = {f["id"]: 0 for f in ROADMAP_FEATURES}
    user_voted: dict[str, bool] = {f["id"]: False for f in ROADMAP_FEATURES}

    # 현재 유저의 voter_id 계산
    if user:
        my_voter_id = f"user:{user['sub']}"
    else:
        my_voter_id = f"session:{session_id}" if session_id else ""

    try:
        container = await _get_votes_container()
        if container is not None:
            async for item in container.query_items(
                query="SELECT c.feature_id, c.voter_id, c.session_id FROM c",
            ):
                fid = item.get("feature_id")
                if fid in counts:
                    counts[fid] += 1
                    # voter_id 필드 우선, 없으면 레거시 session_id로 폴백
                    item_voter = item.get("voter_id") or f"session:{item.get('session_id', '')}"
                    if my_voter_id and item_voter == my_voter_id:
                        user_voted[fid] = True
        else:
            for fid, voters in _votes_fallback.items():
                if fid in counts:
                    counts[fid] = len(voters)
                    user_voted[fid] = my_voter_id in voters
    except Exception as e:
        _logger.error("roadmap votes 조회 실패: %s", e)

    result = [
        {
            "feature_id": f["id"],
            "label":      f["label"],
            "icon":       f["icon"],
            "vote_count": counts[f["id"]],
            "user_voted": user_voted[f["id"]],
        }
        for f in ROADMAP_FEATURES
    ]
    result.sort(key=lambda x: x["vote_count"], reverse=True)
    return {"features": result}


class VoteRequest(BaseModel):
    feature_id: str
    session_id: str


@router.post("/api/roadmap/vote")
async def toggle_vote(
    req: VoteRequest,
    user: dict | None = Depends(get_optional_user),
):
    """기능에 투표하거나 투표를 취소한다. (토글)"""
    fid = req.feature_id
    sid = req.session_id

    if fid not in _FEATURE_IDS:
        raise HTTPException(status_code=400, detail="유효하지 않은 feature_id")

    # voter_id 결정: 로그인 유저는 user_id 기반, 비로그인은 session_id (유효성 검증 포함)
    if user:
        voter_id = f"user:{user['sub']}"
    else:
        if not await session_exists(sid):
            raise HTTPException(status_code=400, detail="유효하지 않은 session_id")
        voter_id = f"session:{sid}"

    doc_id = f"vote_{fid}_{voter_id}"
    voted = False
    vote_count = 0

    try:
        container = await _get_votes_container()
        if container is not None:
            try:
                await container.read_item(item=doc_id, partition_key=fid)
                # 존재 → 삭제 (투표 취소)
                await container.delete_item(item=doc_id, partition_key=fid)
                voted = False
            except Exception:
                # 없음 → 생성 (투표 추가)
                await container.create_item({
                    "id":         doc_id,
                    "feature_id": fid,
                    "voter_id":   voter_id,
                    "session_id": sid,
                    "voted_at":   datetime.utcnow().isoformat(),
                })
                voted = True

            # 현재 파티션 내 투표 수 집계
            count = 0
            async for _ in container.query_items(
                query="SELECT c.id FROM c WHERE c.feature_id = @fid",
                parameters=[{"name": "@fid", "value": fid}],
                partition_key=fid,
            ):
                count += 1
            vote_count = count
        else:
            # 인메모리 폴백
            if voter_id in _votes_fallback[fid]:
                _votes_fallback[fid].discard(voter_id)
                voted = False
            else:
                _votes_fallback[fid].add(voter_id)
                voted = True
            vote_count = len(_votes_fallback[fid])

    except HTTPException:
        raise
    except Exception as e:
        _logger.error("roadmap vote 토글 실패 feature=%s voter=%s: %s", fid, voter_id, e)
        return {"feature_id": fid, "voted": False, "vote_count": 0}

    return {"feature_id": fid, "voted": voted, "vote_count": vote_count}
