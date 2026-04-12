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

from auth_router import get_optional_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from session_store import session_exists

_logger = logging.getLogger("sohobi.roadmap")
router = APIRouter()

# ── 기능 목록 ─────────────────────────────────────────────────────
# status: "in_progress" = Phase 1 개발 중 (투표 비활성)
#          "voting"      = 투표 가능
ROADMAP_FEATURES = [
    # Phase 1 개발 중 (백로그 #1–5)
    {
        "id": "tax_guide",
        "label": "세무 신고 가이드",
        "icon_name": "Receipt",
        "color": "brand-teal",
        "description": "부가세·종합소득세 신고 시점과 필요 서류를 업종별로 안내합니다.",
        "status": "in_progress",
    },
    {
        "id": "gov_support",
        "label": "정부지원금 자동 매칭",
        "icon_name": "Gift",
        "color": "brand-teal",
        "description": "사업자 정보로 받을 수 있는 정부·지자체 지원금을 자동 매칭해 줍니다.",
        "status": "in_progress",
    },
    {
        "id": "hr_guide",
        "label": "HR/노무 가이드",
        "icon_name": "Users",
        "color": "brand-teal",
        "description": "직원 채용·계약·해고 시 지켜야 할 노동법 절차와 서식을 안내합니다.",
        "status": "in_progress",
    },
    {
        "id": "menu_pricing",
        "label": "메뉴 원가 계산",
        "icon_name": "UtensilsCrossed",
        "color": "brand-teal",
        "description": "재료비·인건비·임대료를 반영해 적정 판매가와 마진율을 계산합니다.",
        "status": "in_progress",
    },
    {
        "id": "safety_checklist",
        "label": "위생/안전 점검 체크리스트",
        "icon_name": "ShieldCheck",
        "color": "brand-teal",
        "description": "업종별 위생·안전 점검 항목을 체크리스트로 정리해 단속 대비를 돕습니다.",
        "status": "in_progress",
    },
    # Phase 1 투표 (백로그 #6–10)
    {
        "id": "seasonal_forecast",
        "label": "계절성 매출 예측",
        "icon_name": "TrendingUp",
        "color": "brand-blue",
        "description": "과거 매출과 지역 데이터로 다음 달·분기의 매출 변동을 예측합니다.",
        "status": "voting",
    },
    {
        "id": "contract_analysis",
        "label": "계약서 독소조항 분석",
        "icon_name": "FileText",
        "color": "brand-blue",
        "description": "임대·프랜차이즈 계약서 문구에서 불리한 조항을 찾아 대안을 제시합니다.",
        "status": "voting",
    },
    {
        "id": "delivery_fee",
        "label": "배달앱 수수료 최적화",
        "icon_name": "Bike",
        "color": "brand-orange",
        "description": "배민·쿠팡이츠 등 플랫폼별 수수료 구조를 비교해 실수령액을 극대화합니다.",
        "status": "voting",
    },
    {
        "id": "commercial_trend",
        "label": "상권 트렌드 모니터링",
        "icon_name": "Search",
        "color": "brand-mint",
        "description": "우리 상권의 유동인구·경쟁점포 변화를 주간 단위로 리포트합니다.",
        "status": "voting",
    },
    {
        "id": "biz_closure",
        "label": "폐업/양도 절차 안내",
        "icon_name": "DoorOpen",
        "color": "brand-blue",
        "description": "폐업 신고·세금 정산·권리금 회수까지 단계별로 필요한 일을 안내합니다.",
        "status": "voting",
    },
    # Phase 2 투표 (백로그 #11–24)
    {
        "id": "franchise_compare",
        "label": "프랜차이즈 비교 분석",
        "icon_name": "Store",
        "color": "brand-mint",
        "description": "가맹비·로열티·평균 매출을 프랜차이즈 브랜드별로 비교해 선택을 돕습니다.",
        "status": "voting",
    },
    {
        "id": "local_marketing",
        "label": "SNS/로컬 마케팅 전략",
        "icon_name": "Megaphone",
        "color": "brand-orange",
        "description": "업종·타깃 고객에 맞는 인스타·블로그·당근 마케팅 실행안을 제안합니다.",
        "status": "voting",
    },
    {
        "id": "biz_insurance",
        "label": "사업자 보험 설계",
        "icon_name": "Shield",
        "color": "brand-blue",
        "description": "화재·배상책임·고용보험 등 꼭 필요한 보험 조합을 업종별로 추천합니다.",
        "status": "voting",
    },
    {
        "id": "claim_management",
        "label": "고객 클레임 대응 가이드",
        "icon_name": "MessageCircle",
        "color": "brand-bright-cyan",
        "description": "환불·위생·직원 응대 클레임별 대응 스크립트와 법적 기준선을 제공합니다.",
        "status": "voting",
    },
    {
        "id": "multi_store",
        "label": "멀티 매장 입지 비교",
        "icon_name": "Map",
        "color": "brand-mint",
        "description": "2호점 후보지의 상권·임대료·예상 매출을 본점과 비교 분석합니다.",
        "status": "voting",
    },
    {
        "id": "biz_type_change",
        "label": "업종 전환 타당성 분석",
        "icon_name": "Repeat",
        "color": "brand-orange",
        "description": "현 입지·시설을 유지한 채 전환 가능한 업종과 예상 수익을 시뮬레이션합니다.",
        "status": "voting",
    },
    {
        "id": "premium_valuation",
        "label": "권리금 적정가 산정",
        "icon_name": "Coins",
        "color": "brand-blue",
        "description": "매출·시설·상권 가치를 반영해 주고받아야 할 권리금 범위를 계산합니다.",
        "status": "voting",
    },
    {
        "id": "biz_plan",
        "label": "사업계획서 작성 보조",
        "icon_name": "PenLine",
        "color": "brand-orange",
        "description": "정부지원금·대출 심사에 통과할 수 있는 사업계획서 초안을 생성합니다.",
        "status": "voting",
    },
    {
        "id": "revenue_dashboard",
        "label": "매출/비용 분석 대시보드",
        "icon_name": "BarChart3",
        "color": "brand-blue",
        "description": "카드·현금 매출과 고정비를 한 화면에서 추적해 손익 흐름을 시각화합니다.",
        "status": "voting",
    },
    {
        "id": "inventory",
        "label": "재고 관리 도우미",
        "icon_name": "Package",
        "color": "brand-orange",
        "description": "입출고·유통기한을 추적해 결품과 폐기 손실을 줄이도록 도와줍니다.",
        "status": "voting",
    },
    {
        "id": "crm",
        "label": "단골 고객 관리 (CRM)",
        "icon_name": "Gem",
        "color": "brand-bright-cyan",
        "description": "방문 주기·객단가를 기준으로 단골을 식별하고 재방문 쿠폰을 자동 발송합니다.",
        "status": "voting",
    },
    # Phase 3 투표
    {
        "id": "contract_pdf",
        "label": "계약서 PDF 업로드 분석",
        "icon_name": "FolderOpen",
        "color": "brand-blue",
        "description": "PDF 계약서를 업로드하면 조항을 추출해 위험도와 협상 포인트를 표시합니다.",
        "status": "voting",
    },
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
                    item_voter = (
                        item.get("voter_id") or f"session:{item.get('session_id', '')}"
                    )
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
            "label": f["label"],
            "icon_name": f["icon_name"],
            "color": f["color"],
            "description": f["description"],
            "status": f.get("status", "voting"),
            "vote_count": counts[f["id"]],
            "user_voted": user_voted[f["id"]],
        }
        for f in ROADMAP_FEATURES
    ]
    # in_progress 먼저, 그 안에서는 목록 순서 유지 / voting은 vote_count 내림차순
    result.sort(key=lambda x: (x["status"] == "voting", -x["vote_count"]))
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
                await container.create_item(
                    {
                        "id": doc_id,
                        "feature_id": fid,
                        "voter_id": voter_id,
                        "session_id": sid,
                        "voted_at": datetime.utcnow().isoformat(),
                    }
                )
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
        _logger.error(
            "roadmap vote 토글 실패 feature=%s voter=%s: %s", fid, voter_id, e
        )
        return {"feature_id": fid, "voted": False, "vote_count": 0}

    return {"feature_id": fid, "voted": voted, "vote_count": vote_count}
