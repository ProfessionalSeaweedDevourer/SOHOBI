"""
체크리스트 스토어: 창업 준비 진행률을 Cosmos DB에 저장한다.

Cosmos DB 구조:
  Database  : COSMOS_DATABASE (기본값 "sohobi")
  Container : "checklist"
  Partition : /session_id
  TTL       : COSMOS_SESSION_TTL (기본값 86400)

orchestrator.py에서 직접 import하여 사용한다.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

# ── 싱글턴 ────────────────────────────────────────────────────
_checklist_container = None
_checklist_client    = None

# ── 인메모리 폴백 (COSMOS_ENDPOINT 미설정 시) ─────────────────
_checklist_memory: dict[str, dict] = {}

# ── 체크리스트 항목 ID 목록 ───────────────────────────────────
CHECKLIST_ITEM_IDS: list[str] = [
    "biz_type",
    "location",
    "capital",
    "biz_reg",
    "permit",
    "labor",
    "finance_sim",
    "lease",
]

# ── 자동 체크 키워드 (orchestrator draft 매칭용) ──────────────
CHECKLIST_KEYWORDS: dict[str, list[str]] = {
    "biz_type":    ["업종", "업태", "일반음식점", "휴게음식점", "제과제빵", "소매업"],
    "location":    ["상권", "입지", "유동인구", "상가", "동네", "매장 위치"],
    "capital":     ["초기 자금", "창업 비용", "자본금", "투자금", "대출", "손익분기"],
    "biz_reg":     ["사업자등록", "사업자 등록", "세무서", "개인사업자", "법인"],
    "permit":      ["영업신고", "영업 신고", "위생교육", "허가", "인허가", "식품위생"],
    "labor":       ["직원", "아르바이트", "알바", "4대보험", "근로계약", "인건비"],
    "finance_sim": ["수익성", "손익", "매출", "순이익", "재료비", "시뮬레이션", "BEP"],
    "lease":       ["임대차", "임대 계약", "권리금", "보증금", "월세", "임차인"],
}


def _default_items() -> dict:
    """8개 항목의 기본 상태를 반환한다."""
    return {
        item_id: {"checked": False, "source": None, "checked_at": None}
        for item_id in CHECKLIST_ITEM_IDS
    }


async def _get_checklist_container():
    """싱글턴 Cosmos DB 컨테이너를 반환한다. 미설정 시 None."""
    global _checklist_container, _checklist_client

    if _checklist_container is not None:
        return _checklist_container

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

    _checklist_container = await db.create_container_if_not_exists(
        id="checklist",
        partition_key=PartitionKey(path="/session_id"),
    )
    _checklist_client = client
    return _checklist_container


async def get_checklist(session_id: str) -> dict:
    """
    session_id에 해당하는 체크리스트를 반환한다.
    없으면 기본값(모두 미체크)을 반환한다 (DB에 저장하지 않음).

    반환값: {"session_id": str, "items": dict}
    """
    container = await _get_checklist_container()

    if container is None:
        data = _checklist_memory.get(session_id)
        items = dict(data["items"]) if data else _default_items()
        return {"session_id": session_id, "items": items}

    try:
        item = await container.read_item(item=session_id, partition_key=session_id)
        # 기본값과 병합 (새 항목 ID 추가 대응)
        items = {**_default_items(), **item.get("items", {})}
        return {"session_id": session_id, "items": items}
    except Exception:
        return {"session_id": session_id, "items": _default_items()}


async def upsert_checklist(session_id: str, items: dict) -> None:
    """
    체크리스트 문서를 upsert한다.

    items: {item_id: {"checked": bool, "source": str|None, "checked_at": str|None}}
    """
    ttl = int(os.getenv("COSMOS_SESSION_TTL", "86400"))
    document = {
        "id":         session_id,
        "session_id": session_id,
        "items":      items,
        "ttl":        ttl,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    container = await _get_checklist_container()

    if container is None:
        _checklist_memory[session_id] = document
        return

    await container.upsert_item(document)


async def auto_check_items(session_id: str, draft: str) -> list[str]:
    """
    draft 텍스트에서 CHECKLIST_KEYWORDS 기반으로 매칭되는 항목을 자동 체크한다.
    이미 체크된 항목은 건드리지 않는다.

    반환값: 새로 체크된 item_id 목록 (없으면 빈 리스트)
    """
    if not draft:
        return []

    doc = await get_checklist(session_id)
    items = doc["items"]
    newly_checked: list[str] = []

    for item_id, keywords in CHECKLIST_KEYWORDS.items():
        if items.get(item_id, {}).get("checked"):
            continue  # 이미 체크된 항목은 스킵
        if any(kw in draft for kw in keywords):
            items[item_id] = {
                "checked":    True,
                "source":     "auto",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            newly_checked.append(item_id)

    if newly_checked:
        await upsert_checklist(session_id, items)

    return newly_checked


async def close() -> None:
    """앱 종료 시 Cosmos DB 클라이언트를 닫는다."""
    global _checklist_client
    if _checklist_client is not None:
        await _checklist_client.close()
        _checklist_client = None
