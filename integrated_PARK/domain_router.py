"""
도메인 라우터: 사용자 질문 → admin | finance | legal 분류
출처: PARK/Code_EJP/domain_router.py (변경 없음)
"""

import asyncio
import json

from kernel_setup import get_kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

KEYWORDS: dict[str, list[str]] = {
    "admin": [
        "신고",
        "허가",
        "인허가",
        "서류",
        "관청",
        "위생",
        "영업신고",
        "등록",
        "행정",
        "지원사업",
        "보조금",
        "지원금",
        "창업패키지",
        "정책자금",
        "창업지원",
        "소상공인 지원",
        "정부지원",
        "고용지원",
        "채용장려금",
        "신용보증",
        "사업자등록",
        "위생교육",
        "보건증",
        "식품위생",
        "세무서",
        "소진공",
        "소상공인시장진흥공단",
        "융자",
        "정책대출",
        "지원받",
        "지원 가능",
        "지원 신청",
        "지원 대상",
        "지원 혜택",
        "창업자금",
        "자금 지원",
        "혜택 받",
        "창업 혜택",
        "스타트업",
        "지원 추천",
    ],
    "finance": [
        "재무",
        "금리",
        "수익",
        "비용",
        "투자",
        "시뮬레이션",
        "자본",
        "손익분기점",
        "순이익",
        "영업이익",
        "인건비",
        "원가",
        "창업비용",
        "초기비용",
        "초기투자",
        "투자비용",
        "수익률",
        "투자회수",
        "월수익",
        "매출액",
        "고정비",
        "변동비",
        "마진",
        "손익",
        "이익률",
    ],
    "legal": [
        "법",
        "계약",
        "소송",
        "보증금 반환",
        "임대차",
        "조항",
        "권리",
        "의무",
        "판례",
        "분쟁",
        "권리금",
        "묵시적 갱신",
        "계약 해지",
        "위약금",
        "손해배상",
        "불법",
        "위반",
        "고소",
        "고발",
        "내용증명",
    ],
    "location": [
        "상권",
        "지역",
        "상권분석",
        "홍대",
        "강남",
        "잠실",
        "이태원",
        "합정",
        "vs",
        "비교",
        "종로",
        "마포",
        "성수",
        "신촌",
        "건대",
        "혜화",
        "인사동",
        "명동",
        "여의도",
        "유동인구",
        "입지",
        "점포당",
        "개업률",
        "폐업률",
    ],
    "chat": [
        "안녕",
        "반가워",
        "뭐 할 수 있",
        "어떻게 써",
        "어떻게 사용",
        "도움말",
        "사용법",
        "소개해",
        "처음 써",
        "뭐가 필요",
        "어떤 기능",
        "기능 안내",
        "어떻게 하면 돼",
        "지원 업종",
        "어떤 업종",
        "지원하는 업종",
        "업종 목록",
        "가능한 업종",
    ],
}

# 사용법/기능 설명 요청 패턴 — 어떤 도메인 키워드와 함께 나오더라도 chat 우선
_CHAT_OVERRIDE_PATTERNS = [
    "어떤 기능",
    "무슨 기능",
    "어떤 역할",
    "어떻게 사용",
    "어떻게 써",
    "어떻게 쓰나요",
    "어떻게 쓰는",
    "사용법",
    "도움말",
    "기능 안내",
    "기능 소개",
    "어떻게 이용",
    "이용 방법",
    "쓰는 방법",
    "지원하는 업종",
    "지원 업종",
    "어떤 업종",
    "업종 목록",
    "가능한 업종",
    # 기능 설명 요청 — "재무 시뮬레이션 기능을 알려줘" 등이 finance로 오분류되는 문제 방지
    "기능 알려",
    "기능을 알려",
    "기능 설명",
    # 사용 방법 문의 — 서비스 입력값·활용법 질문 (도메인 독립적 표현만 유지)
    "어떻게 활용",
    "어떻게 입력",
    "입력 방법",
    "뭘 입력",
    "무엇을 입력",
]

_SYSTEM_PROMPT = """You are a query classifier for a Korean small business assistant.
Classify the user query into exactly one of: admin, finance, legal, location, chat.
- admin: 행정 절차, 영업 신고, 허가, 서류, 관청 관련, 정부지원사업, 보조금, 지원금, 창업패키지, 정책자금 대출, 소상공인 융자, 신용보증, 고용지원, 채용장려금, 사업자등록, 위생교육, 보건증. ※ 정부지원·보조금 질문은 IT·제조·서비스 등 업종 무관하게 항상 admin
- finance: 재무 시뮬레이션, 수익/비용 분석, 투자 수익률, 손익분기점, 자본금 계산, 인건비·원가·임대료를 비용으로 계산하는 수익 분석, 창업 초기비용/투자비용 계산 (정부지원사업·정책자금 대출은 admin)
- legal: 법률 분쟁, 계약서 검토, 권리 의무, 소송, 보증금 반환 분쟁, 임대차 계약 해석, 위약금, 손해배상 — ※ 보증금·월세 금액이 재무 계산의 비용 항목으로 언급된 경우는 finance
- location: 특정 지역/상권의 매출 데이터 조회, 지역 비교, 창업 입지 분석, 개업률·폐업률·유동인구 데이터 요청 — ※ 지역명이 단순 배경으로 언급되고 재무 계산이 주목적이면 finance
- chat: 인사, 잡담, 서비스 기능·사용법 문의, "뭐 할 수 있어?" 류의 안내 요청, 특정 에이전트의 입력값·사용법을 묻는 질문, 서비스 범위 밖의 질문 (예: 맛집 추천, 서울 외 지역 상권 데이터 문의)

핵심 disambiguation 규칙:
1. "보증금 + 월세 + 손익/수익/계산" → finance (재무 비용 항목)
2. "보증금 반환 / 임대차 분쟁 / 계약 해지" → legal
3. "[지역명] + 상권 분석/비교" → location
4. "[지역명] + 창업비용/손익분기점/수익 계산" → finance (지역은 배경)
5. "창업 절차/신고/허가" → admin
6. "지원받을 수 있어?", "지원 신청", "보조금 받을 수 있어?" 등 정부지원 문의 → admin (업종 무관)
7. 맛집 추천, 시스템 질문, 상권분석 DB 미지원 지역(서울 외: 수원·부산·대구·인천·대전·판교·분당 등) 커버리지 문의 → chat
8. "추천해줘" + 창업/사업/스타트업 맥락 → admin (지원사업/프로그램 추천 요청)
9. 대화 맥락([대화 맥락] 블록)이 제공된 경우, 이전 턴의 도메인을 반드시 참고하여 분류하라. 이전 대화가 admin 주제였다면 후속 질문은 admin 우선 고려

Respond ONLY in JSON: {"domain": "...", "confidence": 0.0~1.0, "reasoning": "..."}"""

_FALLBACK = {
    "domain": "admin",
    "confidence": 0.3,
    "reasoning": "LLM 파싱 실패 — 기본값 적용",
}

_PRIVACY_KEYWORDS = ["개인정보"]


def _keyword_classify(question: str) -> dict | None:
    # chat override 먼저 — 사용법·안내 요청은 도메인 키워드와 무관하게 chat
    for pat in _CHAT_OVERRIDE_PATTERNS:
        if pat in question:
            return {
                "domain": "chat",
                "confidence": 0.9,
                "reasoning": f"사용법/기능 안내 요청 감지: '{pat}'",
            }

    counts = {d: sum(kw in question for kw in kws) for d, kws in KEYWORDS.items()}
    best = max(counts, key=counts.get)
    if counts[best] < 2:
        return None
    if sum(1 for c in counts.values() if c == counts[best]) > 1:
        return None
    matched = [kw for kw in KEYWORDS[best] if kw in question]
    return {
        "domain": best,
        "confidence": 0.85,
        "reasoning": f"키워드 매칭: {', '.join(matched)}",
    }


async def _llm_classify(question: str, prior_history: list[dict] | None = None) -> dict:
    kernel = get_kernel()
    chat_service = kernel.get_service("router")
    settings = AzureChatPromptExecutionSettings(response_format={"type": "json_object"})
    history = ChatHistory()
    history.add_system_message(_SYSTEM_PROMPT)

    # 최근 2턴(최대 4개 메시지)을 대화 맥락으로 삽입하여 문맥 기반 분류 (레이턴시 최소화)
    if prior_history:
        recent = prior_history[-4:]
        context_lines = []
        for msg in recent:
            role = "user" if msg["role"] == "user" else "assistant"
            content = msg["content"][:200]  # 토큰 절약
            context_lines.append(f"{role}: {content}")
        context_block = (
            "[대화 맥락 - 최근 대화]\n" + "\n".join(context_lines) + "\n\n[현재 질문]\n"
        )
        history.add_user_message(context_block + question)
    else:
        history.add_user_message(question)

    try:
        result = await asyncio.wait_for(
            chat_service.get_chat_message_content(
                chat_history=history, settings=settings
            ),
            timeout=30.0,
        )
        parsed = json.loads(str(result))
        return (
            parsed
            if parsed.get("domain") in ("admin", "finance", "legal", "location", "chat")
            else _FALLBACK
        )
    except Exception:
        return _FALLBACK


async def classify(
    question: str,
    prior_history: list[dict] | None = None,
    last_domain: str | None = None,
) -> dict:
    if any(kw in question for kw in _PRIVACY_KEYWORDS):
        return {
            "domain": "chat",
            "confidence": 1.0,
            "reasoning": "개인정보처리방침 질문 — 안내 에이전트로 라우팅",
        }
    result = _keyword_classify(question)
    if result:
        return result
    llm_result = await _llm_classify(question, prior_history)
    # last_domain 방어선: LLM이 chat으로 분류했지만 확신이 낮고 이전 도메인이 실무 도메인이면 유지
    # 단, 현재 질문에 다른 실무 도메인 키워드가 1개 이상 있으면 방어선 해제 (진짜 도메인 전환)
    if (
        llm_result.get("domain") == "chat"
        and llm_result.get("confidence", 1.0) < 0.75
        and last_domain in ("admin", "finance", "legal", "location")
    ):
        other_domain_signals = {
            d: sum(kw in question for kw in kws)
            for d, kws in KEYWORDS.items()
            if d not in ("chat", last_domain)
        }
        if not any(c >= 1 for c in other_domain_signals.values()):
            return {
                "domain": last_domain,
                "confidence": 0.55,
                "reasoning": f"LLM chat 분류 확신 낮음({llm_result.get('confidence', '?')}) — 이전 도메인 '{last_domain}' 유지",
            }
    return llm_result
