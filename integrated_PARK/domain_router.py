"""
도메인 라우터: 사용자 질문 → admin | finance | legal 분류
출처: PARK/Code_EJP/domain_router.py (변경 없음)
"""

import json

from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings

from kernel_setup import get_kernel

KEYWORDS: dict[str, list[str]] = {
    "admin":    ["신고", "허가", "인허가", "서류", "관청", "위생", "영업신고", "등록", "행정"],
    "finance":  ["재무", "대출", "금리", "수익", "비용", "투자", "시뮬레이션", "자본"],
    "legal":    ["법", "계약", "소송", "보증금", "임대차", "조항", "권리", "의무", "판례"],
    "location": ["상권", "지역", "상권분석", "홍대", "강남", "잠실", "이태원", "합정", "vs", "비교"],
}

_SYSTEM_PROMPT = """You are a query classifier for a Korean small business assistant.
Classify the user query into exactly one of: admin, finance, legal, location.
- admin: 행정 절차, 영업 신고, 허가, 서류, 관청 관련
- finance: 재무, 대출, 수익, 비용, 투자 시뮬레이션 관련
- legal: 법률, 계약, 권리 의무, 소송, 임대차 관련
- location: 상권 분석, 지역 비교, 매출 지역 데이터, 창업 입지 분석 관련
Respond ONLY in JSON: {"domain": "...", "confidence": 0.0~1.0, "reasoning": "..."}"""

_FALLBACK = {"domain": "admin", "confidence": 0.3, "reasoning": "LLM 파싱 실패 — 기본값 적용"}


def _keyword_classify(question: str) -> dict | None:
    counts = {d: sum(kw in question for kw in kws) for d, kws in KEYWORDS.items()}
    best = max(counts, key=counts.get)
    if counts[best] < 2:
        return None
    if sum(1 for c in counts.values() if c == counts[best]) > 1:
        return None
    matched = [kw for kw in KEYWORDS[best] if kw in question]
    return {"domain": best, "confidence": 0.85, "reasoning": f"키워드 매칭: {', '.join(matched)}"}


async def _llm_classify(question: str) -> dict:
    kernel = get_kernel()
    chat_service = kernel.get_service("sign_off")
    settings = AzureChatPromptExecutionSettings(response_format={"type": "json_object"})
    history = ChatHistory()
    history.add_system_message(_SYSTEM_PROMPT)
    history.add_user_message(question)
    try:
        result = await chat_service.get_chat_message_content(chat_history=history, settings=settings)
        parsed = json.loads(str(result))
        return parsed if parsed.get("domain") in ("admin", "finance", "legal", "location") else _FALLBACK
    except Exception:
        return _FALLBACK


async def classify(question: str) -> dict:
    result = _keyword_classify(question)
    return result if result else await _llm_classify(question)
