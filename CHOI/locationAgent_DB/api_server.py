"""
상권분석 에이전트 독립 API 서버
- locationAgent_DB의 LocationAgent를 REST API로 제공
- 지도 프론트엔드(TERRY)와 직접 연동용
"""

import json
import re
import uuid
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from agent.location_agent import LocationAgent, _get_kernel
from db.repository import CommercialRepository, AREA_MAP, INDUSTRY_CODE_MAP

# ── 앱 초기화 ──────────────────────────────────────────────
app = FastAPI(title="상권분석 에이전트 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent = LocationAgent()
_repo = CommercialRepository()


# ── 파라미터 추출 프롬프트 ─────────────────────────────────
_PARAM_EXTRACT_PROMPT = """사용자가 다음과 같은 상권 분석 질문을 했습니다:
"{user_input}"

아래 형식의 JSON만 출력하십시오.
{{
  "mode": "analyze" 또는 "compare",
  "locations": ["지역명1", "지역명2", ...],
  "business_type": "업종명",
  "quarter": "YYYYQ"
}}

규칙:
- 지역이 하나이면 mode="analyze", 두 개 이상이면 mode="compare"
- 지역명은 한국어 원문 그대로 (예: "홍대", "강남", "잠실")
- 업종명은 한국어 원문 그대로 (예: "카페", "한식", "치킨")
- 분기가 언급되지 않으면 "20253" 사용
- JSON 외 다른 텍스트 절대 출력 금지"""


def _normalize_location(raw: str) -> str | None:
    """
    사용자 입력 지역명 → AREA_MAP 키로 정규화
    "서초동" → "서초", "서초1동" → "서초", "강남역" → "강남", "홍대입구" → "홍대"
    """
    # 1단계: 정확히 일치
    if raw in AREA_MAP:
        return raw

    # 2단계: DB ADM_NM 역조회 (정확도 우선)
    #   "서초1동" → ADM_NM LIKE '%서초1동%' → 서초1동 코드만 반환
    #   AREA_MAP에 없는 개별 행정동도 정확히 조회 가능
    try:
        results = _repo.find_adm_codes_by_name(raw)
        if results:
            temp_key = f"__nm_{raw}"
            AREA_MAP[temp_key] = [r["adm_cd"] for r in results]
            return temp_key
    except Exception:
        pass

    # 3단계: 접미사 제거 후 매칭
    #   숫자+동, 동, 구, 역, 입구, 주변, 근처, 일대, 쪽
    stripped = re.sub(r"\d*동$|구$|역$|입구$|지역$|쪽$|근처$|일대$|주변$|앞$", "", raw)
    if stripped and stripped in AREA_MAP:
        return stripped

    # 4단계: 부분 문자열 매칭 (AREA_MAP 키 → 입력에 포함)
    #   "서초구반포" → "반포" 매칭
    candidates = []
    for key in AREA_MAP:
        if len(key) >= 2 and key in raw:
            candidates.append(key)
    if candidates:
        # 가장 긴 매칭 우선 (더 구체적인 지역)
        candidates.sort(key=len, reverse=True)
        return candidates[0]

    # 5단계: stripped로 부분 매칭
    if stripped and len(stripped) >= 2:
        for key in AREA_MAP:
            if stripped in key or key in stripped:
                return key

    return None


def _normalize_business_type(raw: str) -> str | None:
    """
    사용자 입력 업종명 → INDUSTRY_CODE_MAP 키로 정규화
    "치킨집" → "치킨", "빵집" → "빵집"(직접 매핑), "브런치 카페" → "브런치 카페"(직접 매핑)
    """
    if not raw:
        return None

    # 1단계: 정확히 일치
    if raw in INDUSTRY_CODE_MAP:
        return raw

    # 2단계: 접미사 제거 후 매칭 (집, 점, 가게, 전문점, 샵)
    stripped = re.sub(r"(집|점|가게|전문점|전문|샵)$", "", raw)
    if stripped and stripped in INDUSTRY_CODE_MAP:
        return stripped

    # 3단계: 부분 문자열 매칭 (입력이 키에 포함 or 키가 입력에 포함)
    for key in INDUSTRY_CODE_MAP:
        if len(key) >= 2 and (key in raw or raw in key):
            return key

    return None


async def _extract_params(question: str) -> dict:
    """자연어 질문 → {mode, locations, business_type, quarter}"""
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from semantic_kernel.contents import ChatHistory
    from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings

    kernel = _get_kernel()
    services = list(kernel.services.values())
    service = services[0] if services else None

    history = ChatHistory()
    history.add_system_message("You are a parameter extractor. Output JSON only.")
    history.add_user_message(_PARAM_EXTRACT_PROMPT.format(user_input=question))

    settings = AzureChatPromptExecutionSettings(max_completion_tokens=500)
    result = await service.get_chat_message_content(history, settings=settings)
    raw = str(result)

    clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        params = json.loads(clean)
    except json.JSONDecodeError:
        params = {}

    # 추출된 지역명을 AREA_MAP 키로 정규화
    raw_locations = params.get("locations", [])
    normalized = []
    for loc in raw_locations:
        normed = _normalize_location(loc)
        if normed:
            normalized.append(normed)
        else:
            normalized.append(loc)  # 정규화 실패 시 원본 유지 (에이전트가 에러 처리)

    # 추출된 업종명을 INDUSTRY_CODE_MAP 키로 정규화
    raw_biz = params.get("business_type", "")
    normed_biz = _normalize_business_type(raw_biz)

    return {
        "mode": params.get("mode", "analyze"),
        "locations": normalized,
        "business_type": normed_biz or raw_biz,
        "quarter": params.get("quarter", "20253"),
    }


# ── 요청/응답 모델 ────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    adm_cd: str | None = None  # 지도에서 선택한 행정동 코드 (직접 DB 조회용)


# ── 엔드포인트 ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/locations")
async def get_locations():
    return {"locations": _repo.get_supported_locations()}


@app.get("/industries")
async def get_industries():
    return {"industries": _repo.get_supported_industries()}


@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # 파라미터 추출
    params = await _extract_params(req.question)
    mode = params["mode"]
    locations = params["locations"]
    business_type = params["business_type"]
    quarter = params["quarter"]

    # adm_cd가 있으면 AREA_MAP을 우회하여 직접 행정동 코드로 조회
    # 지도에서 행정동을 클릭 → AI 버튼으로 넘어온 경우
    if req.adm_cd and business_type:
        # 임시 키로 AREA_MAP에 등록하여 기존 에이전트 로직 재활용
        temp_key = f"__adm_{req.adm_cd}"
        AREA_MAP[temp_key] = [req.adm_cd]
        try:
            result = await _agent.analyze(temp_key, business_type, quarter)

            if "error" in result:
                return {
                    "session_id": session_id,
                    "type": "error",
                    "analysis": result.get("error", "오류가 발생했습니다."),
                    "location": locations[0] if locations else req.adm_cd,
                    "business_type": business_type,
                }

            return {
                "session_id": session_id,
                "type": "analyze",
                "analysis": result.get("analysis", ""),
                "similar_locations": result.get("similar_locations", []),
                "location": locations[0] if locations else req.adm_cd,
                "business_type": business_type,
                "quarter": quarter,
                "adm_codes": [req.adm_cd],
            }
        finally:
            # 임시 키 정리
            AREA_MAP.pop(temp_key, None)

    if not locations and not business_type:
        return {
            "session_id": session_id,
            "type": "error",
            "analysis": (
                "분석할 지역과 업종을 함께 알려주세요!\n\n"
                "💡 이렇게 질문해 보세요:\n"
                "• 홍대 카페 상권 분석해줘\n"
                "• 강남 치킨 창업 어때?\n"
                "• 잠실 vs 건대 한식 비교\n\n"
                "📍 지원 지역: 서울시 전체 행정동\n"
                "🍽️ 지원 업종: 한식, 카페, 치킨, 양식, 일식, 중식, 분식, "
                "베이커리, 호프/술집, 패스트푸드, 미용실, 편의점 등"
            ),
            "location": None,
            "business_type": None,
        }
    if not locations:
        return {
            "session_id": session_id,
            "type": "error",
            "analysis": (
                f"'{business_type}' 업종은 확인했는데, 어느 지역인지 알려주세요!\n\n"
                "💡 예시: '홍대 {0} 분석', '강남 {0} 창업 어때?'".format(business_type)
            ),
            "location": None,
            "business_type": business_type,
        }
    if not business_type:
        loc_str = locations[0] if len(locations) == 1 else ", ".join(locations)
        return {
            "session_id": session_id,
            "type": "error",
            "analysis": (
                f"'{loc_str}' 지역은 확인했는데, 어떤 업종을 분석할까요?\n\n"
                "💡 예시: '{0} 카페 분석', '{0} 치킨 창업 어때?'\n\n"
                "🍽️ 지원 업종: 한식, 카페, 치킨, 양식, 일식, 중식, 분식, "
                "베이커리, 호프/술집, 패스트푸드, 미용실, 편의점 등".format(loc_str)
            ),
            "location": loc_str,
            "business_type": None,
        }

    # DB fallback으로 생성된 임시 키 추적 (사용 후 정리)
    temp_keys = [loc for loc in locations if loc.startswith("__nm_")]

    try:
        # 분석 수행
        if mode == "compare" and len(locations) >= 2:
            result = await _agent.compare(locations, business_type, quarter)

            if "error" in result:
                return {
                    "session_id": session_id,
                    "type": "error",
                    "analysis": result.get("error", "오류가 발생했습니다."),
                    "location": ", ".join(locations),
                    "business_type": business_type,
                }

            return {
                "session_id": session_id,
                "type": "compare",
                "analysis": result.get("comparison", ""),
                "locations": locations,
                "business_type": business_type,
                "quarter": quarter,
                "data": result.get("data", []),
            }
        else:
            location = locations[0]
            result = await _agent.analyze(location, business_type, quarter)

            if "error" in result:
                return {
                    "session_id": session_id,
                    "type": "error",
                    "analysis": result.get("error", "오류가 발생했습니다."),
                    "location": location,
                    "business_type": business_type,
                }

            # 분석에 사용된 행정동 코드 목록 반환 (지도 하이라이트용)
            adm_codes = AREA_MAP.get(location, [])

            return {
                "session_id": session_id,
                "type": "analyze",
                "analysis": result.get("analysis", ""),
                "similar_locations": result.get("similar_locations", []),
                "location": location,
                "business_type": business_type,
                "quarter": quarter,
                "adm_codes": adm_codes,
            }
    finally:
        # DB fallback 임시 키 정리
        for tk in temp_keys:
            AREA_MAP.pop(tk, None)


# ── 서버 실행 ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
