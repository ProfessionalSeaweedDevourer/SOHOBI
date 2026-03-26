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
from db.repository import CommercialRepository

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

    return {
        "mode": params.get("mode", "analyze"),
        "locations": params.get("locations", []),
        "business_type": params.get("business_type", ""),
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
        from db.repository import AREA_MAP
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
            }
        finally:
            # 임시 키 정리
            AREA_MAP.pop(temp_key, None)

    if not locations or not business_type:
        return {
            "session_id": session_id,
            "type": "error",
            "analysis": "분석할 지역명과 업종을 명시해 주십시오.\n예: '홍대 카페 상권 분석', '강남 vs 잠실 한식 비교'",
            "location": None,
            "business_type": None,
        }

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

        return {
            "session_id": session_id,
            "type": "analyze",
            "analysis": result.get("analysis", ""),
            "similar_locations": result.get("similar_locations", []),
            "location": location,
            "business_type": business_type,
            "quarter": quarter,
        }


# ── 서버 실행 ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
