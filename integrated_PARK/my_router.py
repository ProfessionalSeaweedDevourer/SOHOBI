"""
회원 전용 Q&A 로그 조회 라우터.

엔드포인트:
  GET /api/my/sessions                        — 내 세션 목록 (최신순)
  GET /api/my/sessions/{session_id}/history   — 특정 세션 Q&A 대화 내역

JWT Bearer 토큰 필수 (Authorization: Bearer <token>).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth_router import get_current_user
import session_store

router = APIRouter(prefix="/api/my", tags=["my"])


@router.get("/sessions")
async def list_my_sessions(user: dict = Depends(get_current_user)):
    """현재 유저에 귀속된 세션 목록을 최신순으로 반환."""
    sessions = await session_store.get_sessions_by_user(user["sub"])

    result = []
    for s in sessions:
        ctx = s.get("context", {})
        ts  = s.get("_ts", 0)
        created_at = (
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if ts else None
        )
        result.append({
            "session_id":    s["session_id"],
            "created_at":    created_at,
            "query_count":   s.get("history_count", 0) // 2,  # user+assistant 쌍
            "context": {
                "business_type": ctx.get("business_type", ""),
                "location_name": ctx.get("location_name", ""),
            },
        })
    return result


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    include_messages: bool = False,
    user: dict = Depends(get_current_user),
):
    """특정 세션의 Q&A 대화 내역 반환. 본인 세션만 허용.

    include_messages=true 시 프론트 렌더링용 messages 메타데이터도 함께 반환.
    """
    # 소유권 확인: 해당 세션이 이 유저의 것인지 검증
    user_sessions = await session_store.get_sessions_by_user(user["sub"])
    owned_ids = {s["session_id"] for s in user_sessions}
    if session_id not in owned_ids:
        raise HTTPException(status_code=403, detail="본인의 세션만 조회할 수 있습니다.")

    history = await session_store.get_session_history(session_id)
    # user/assistant 메시지만 반환 (system 제외)
    filtered = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant")
    ]

    if not include_messages:
        return filtered  # 하위 호환: 기존 flat array

    messages = await session_store.get_session_messages(session_id)
    return {"history": filtered, "messages": messages}
