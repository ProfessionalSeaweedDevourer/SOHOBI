"""
체크리스트 라우터

GET  /api/checklist/{session_id}  — 현재 상태 조회
PATCH /api/checklist/{session_id} — 단일 항목 수동 토글
"""
from fastapi import APIRouter
from pydantic import BaseModel

import checklist_store

router = APIRouter()


class ChecklistToggleRequest(BaseModel):
    item_id: str
    checked: bool
    source:  str = "manual"   # "manual" | "auto"


@router.get("/api/checklist/{session_id}")
async def get_checklist_state(session_id: str):
    """
    session_id에 해당하는 체크리스트 상태를 반환한다.

    반환:
      session_id : str
      items      : {item_id: {checked, source, checked_at}}
      progress   : int  (완료된 항목 수, 0~8)
    """
    doc = await checklist_store.get_checklist(session_id)
    items = doc["items"]
    progress = sum(1 for v in items.values() if v.get("checked"))
    return {"session_id": session_id, "items": items, "progress": progress}


@router.patch("/api/checklist/{session_id}")
async def toggle_checklist_item(session_id: str, body: ChecklistToggleRequest):
    """
    단일 항목을 수동으로 토글한다.

    반환:
      session_id : str
      item_id    : str
      checked    : bool
      items      : 갱신된 전체 items
    """
    if body.item_id not in checklist_store.CHECKLIST_ITEM_IDS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"알 수 없는 항목: {body.item_id}")

    doc = await checklist_store.get_checklist(session_id)
    items = doc["items"]

    from datetime import datetime, timezone
    items[body.item_id] = {
        "checked":    body.checked,
        "source":     body.source,
        "checked_at": datetime.now(timezone.utc).isoformat() if body.checked else None,
    }

    await checklist_store.upsert_checklist(session_id, items)
    return {
        "session_id": session_id,
        "item_id":    body.item_id,
        "checked":    body.checked,
        "items":      items,
    }
