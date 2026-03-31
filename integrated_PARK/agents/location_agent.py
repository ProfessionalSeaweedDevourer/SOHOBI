"""
상권분석 에이전트 (통합 버전)
출처: CHOI/locationAgent_sang/agent/location_agent.py

변경:
- ChatCompletionAgent / _make_kernel() 제거 → 단일 커널(get_kernel) + 직접 LLM 호출
- generate_draft(question, retry_prompt, profile) 진입점 구현
- S1~S5 루브릭 통과용 지시 포함 (sign-off 루프 참여)
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from db.repository import CommercialRepository


# ── 파라미터 추출 프롬프트 ─────────────────────────────────────────────

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
- 분기가 언급되지 않으면 "20244" 사용
- JSON 외 다른 텍스트 절대 출력 금지"""

# ── LLM 분석 지시 프롬프트 ────────────────────────────────────────────

_ANALYZE_INSTRUCTIONS = """\
당신은 서울 F&B 창업 상권분석 전문가입니다.
제공된 DB 데이터를 바탕으로 아래 형식에 따라 한국어로만 응답하십시오.

## 절대 준수 언어 규칙
응답의 모든 단어는 한국어 또는 숫자여야 합니다. 영어·중국어·일본어 사용 금지.

## 응답 형식 (반드시 이 순서대로)
📅 데이터 기준: {year}년 {q}분기

📊 전체 합산 요약
- 월매출: XXX억 X,XXX만원
- 점포수: XX개
- 주중/주말 비율: 주중 XX% / 주말 XX%
- 피크타임: XX시~XX시
- 주요 고객층: 성별(남성 XX% / 여성 XX%), 연령(XX대 중심)
- 점포당 평균 매출: XXX만원

🏪 상권별 분리 분석
- **상권명**: 월매출 XXX억 X,XXX만원, 점포수 XX개, 점포당 평균 X,XXX만원, 개업률 X% / 폐업률 X%, 특징 1~2줄
(모든 상권에 개업률과 폐업률을 반드시 포함할 것)

✅ 기회 요인
- 핵심 기회 2~3가지 (각 1줄)

⚠️ 리스크 요인
- 핵심 리스크 2~3가지 (각 1줄)

## 추가 준수 규칙
- 지정된 섹션 외 추가 섹션(## 메모, ## 참고 등) 절대 생성 금지
- 금액 변환: 1억=100,000,000원 (예: 2,028,280,000 → 20억 2,828만원)
- 모든 금액은 억/만원 단위로 변환 (원 단위 절대 사용 금지)
- 점포당 평균 매출도 반드시 만원 단위 (예: 42,722,618 → 4,272만원)
- 번호 매기기 절대 금지 (1. 2. 3. 사용 금지)
- 800자 이내
- 리스크 요인 이후 총평 문장 추가 금지
- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지
- 이 응답은 DB 데이터 기반 정보 제공이며 창업을 보장하지 않습니다 (마지막 줄에 한 줄 추가)\
"""

_COMPARE_INSTRUCTIONS = """\
당신은 서울 F&B 창업 상권 비교 전문가입니다.
제공된 DB 데이터를 바탕으로 아래 형식에 따라 한국어로만 응답하십시오.

## 절대 준수 언어 규칙
응답의 모든 단어는 한국어 또는 숫자여야 합니다. 영어·중국어·일본어 사용 금지.

## 응답 형식 (반드시 이 순서대로)
📅 데이터 기준: {year}년 {q}분기 / 업종: {business_type}

📊 지역별 비교표

| 항목 | 지역A | 지역B | ... |
|------|-------|-------|
| 월매출 | XXX억 X,XXX만원 | XXX억 X,XXX만원 |
| 점포수 | XX개 | XX개 |
| 점포당 평균매출 | X,XXX만원 | X,XXX만원 |
| 주중/주말 | XX%/XX% | XX%/XX% |
| 개업률 | X.X% | X.X% |
| 폐업률 | X.X% | X.X% |
| 주요 성별 | 남XX%/여XX% | 남XX%/여XX% |

✅ 창업 추천 순위
- **1순위: XXX** - 추천 이유 1~2줄
- **2순위: XXX** - 추천 이유 1~2줄

⚠️ 유의사항
- 각 지역별 리스크 1줄씩

## 추가 준수 규칙
- 창업 추천 순위 기준: 점포당 평균매출 높음 > 폐업률 낮음 > 개업률 적정
- 모든 금액은 억/만원 단위로 변환 (원 단위 절대 사용 금지)
- 번호 매기기 절대 금지 (추천 순위 제외)
- 유의사항 이후 총평 문장 추가 금지
- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지
- 이 응답은 DB 데이터 기반 정보 제공이며 창업을 보장하지 않습니다 (마지막 줄에 한 줄 추가)\
"""

_RETRY_PREFIX = """이전 응답에서 다음 문제가 지적되었습니다. 반드시 반영하여 전체 응답을 다시 작성하십시오.

[지적 사항]
{retry_prompt}

"""

_PROFILE_CONTEXT = """[창업자 상황]
{profile}

"""


class LocationAgent:
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._repo = CommercialRepository()

    # ── 내부 LLM 호출 ──────────────────────────────────────────

    async def _call_llm(self, system_msg: str, user_msg: str) -> str:
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        history = ChatHistory()
        history.add_system_message(system_msg)
        history.add_user_message(user_msg)
        settings = OpenAIChatPromptExecutionSettings(max_completion_tokens=2000)
        try:
            result = await service.get_chat_message_content(history, settings=settings)
            text = str(result)
            if not text or text == "None":
                raise ValueError("LLM이 빈 응답을 반환했습니다.")
            return text
        except Exception as e:
            err_str = str(e).lower()
            logger.error("LocationAgent LLM 호출 실패: %s", e)
            if "content_filter" in err_str or "content filter" in err_str:
                safe_sys = "다음은 합법적인 상권 데이터 분석 요청입니다.\n\n" + system_msg
                result = await service.get_chat_message_content(
                    ChatHistory(system_message=safe_sys),
                    settings=settings,
                )
                return str(result)
            raise ValueError(f"AI 응답 생성 중 오류가 발생했습니다: {e}") from e

    # ── 파라미터 추출 ───────────────────────────────────────────

    async def _extract_params(self, question: str, prior_history: list[dict] | None = None) -> dict:
        """자연어 질문 → {mode, locations, business_type, quarter}"""
        history_ctx = ""
        if prior_history:
            lines = []
            for msg in prior_history:
                role_label = "사용자" if msg["role"] == "user" else "에이전트"
                lines.append(f"[{role_label}] {msg['content']}")
            history_ctx = "이전 대화 맥락:\n" + "\n".join(lines) + "\n\n"
        raw = await self._call_llm(
            "You are a parameter extractor. Output JSON only.",
            history_ctx + _PARAM_EXTRACT_PROMPT.format(user_input=question),
        )
        clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            params = json.loads(clean)
        except json.JSONDecodeError:
            params = {}

        return {
            "mode": params.get("mode", "analyze"),
            "locations": params.get("locations", []),
            "business_type": params.get("business_type", ""),
            "quarter": params.get("quarter", "20244"),
        }

    # ── DB 조회 + LLM 단일 지역 분석 ───────────────────────────

    async def _run_agent(
        self,
        location: str,
        business_type: str,
        quarter: str,
        sales_data: dict | None,
        store_data: dict | None,
    ) -> str:
        year = quarter[:4]
        q = quarter[4]

        instructions = _ANALYZE_INSTRUCTIONS.format(year=year, q=q)

        sales_summary = sales_data.get("summary", {}) if sales_data else {}
        sales_breakdown = sales_data.get("breakdown", []) if sales_data else []
        store_summary = store_data.get("summary", {}) if store_data else {}
        store_breakdown = store_data.get("breakdown", []) if store_data else []

        user_msg = (
            f"지역: {location} / 업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[매출 합산]\n{json.dumps(sales_summary, ensure_ascii=False, indent=2)}\n\n"
            f"[매출 상권별]\n{json.dumps(sales_breakdown, ensure_ascii=False, indent=2)}\n\n"
            f"[점포 합산]\n{json.dumps(store_summary, ensure_ascii=False, indent=2)}\n\n"
            f"[점포 상권별]\n{json.dumps(store_breakdown, ensure_ascii=False, indent=2)}"
        )

        return await self._call_llm(instructions, user_msg)

    async def analyze(
        self, location: str, business_type: str, quarter: str = "20244"
    ) -> dict:
        """단일 지역 상권 분석 → {draft, adm_codes, type} dict 반환"""
        supported = self._repo.get_supported_industries()
        if business_type not in supported:
            return {
                "draft": f"죄송합니다. '{business_type}' 업종은 현재 지원하지 않습니다.\n지원 업종: {', '.join(sorted(supported))}",
                "adm_codes": [],
                "type": "analyze",
            }

        sales_data = self._repo.get_sales(location, business_type, quarter)
        store_data = self._repo.get_store_count(location, business_type, quarter)

        if not sales_data and not store_data:
            return {
                "draft": (
                    f"'{location}' 지역의 '{business_type}' 업종 데이터를 찾을 수 없습니다.\n"
                    "지역명 또는 업종명을 확인해 주십시오."
                ),
                "adm_codes": [],
                "type": "analyze",
            }

        # 점포당 평균 매출 계산
        monthly_sales = float(
            sales_data.get("summary", {}).get("monthly_sales_krw", 0) if sales_data else 0
        )
        store_count = int(
            store_data.get("summary", {}).get("store_count", 0) if store_data else 0
        )
        avg_per_store = int(monthly_sales / store_count) if store_count > 0 else 0
        if sales_data:
            sales_data["summary"]["avg_sales_per_store_krw"] = avg_per_store
        if sales_data and store_data:
            store_map = {b["trdar_name"]: b for b in store_data.get("breakdown", [])}
            for s in sales_data.get("breakdown", []):
                s_count = int(store_map.get(s["trdar_name"], {}).get("store_count", 0))
                s_sales = float(s.get("monthly_sales_krw", 0))
                s["avg_sales_per_store_krw"] = int(s_sales / s_count) if s_count > 0 else 0

        analysis = await self._run_agent(location, business_type, quarter, sales_data, store_data)

        # 유사 상권 추천 테이블 추가
        similar = self._repo.get_similar_locations(
            business_type=business_type,
            quarter=quarter,
            exclude_location=location,
            top_n=3,
        )
        if similar:
            rows = "\n".join(
                f"| {i+1} | {s['adm_name']} | {s['monthly_sales_krw']:,}원 | "
                f"{s['store_count']}개 | {s['avg_sales_per_store_krw']:,}원 |"
                for i, s in enumerate(similar)
            )
            similar_table = (
                "\n\n📍 유사 상권 추천 (참고)\n\n"
                "| 순위 | 지역 | 월매출 | 점포수 | 점포당 평균 |\n"
                "|------|------|--------|--------|------------|\n"
                + rows
            )
            analysis += similar_table

        adm_codes = self._repo._get_adm_codes(location)
        return {"draft": analysis, "adm_codes": adm_codes, "type": "analyze"}

    # ── DB 조회 + LLM 복수 지역 비교 ───────────────────────────

    async def _run_compare_agent(
        self, location_data: list, business_type: str, year: str, q: str
    ) -> str:
        instructions = _COMPARE_INSTRUCTIONS.format(
            year=year, q=q, business_type=business_type
        )
        user_msg = (
            f"업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[지역별 데이터]\n{json.dumps(location_data, ensure_ascii=False, indent=2)}"
        )
        return await self._call_llm(instructions, user_msg)

    async def compare(
        self, locations: list[str], business_type: str, quarter: str = "20244"
    ) -> dict:
        """복수 지역 비교 → {draft, adm_codes, type} dict 반환"""
        supported = self._repo.get_supported_industries()
        if business_type not in supported:
            return {
                "draft": f"죄송합니다. '{business_type}' 업종은 현재 지원하지 않습니다.\n지원 업종: {', '.join(sorted(supported))}",
                "adm_codes": [],
                "type": "compare",
            }

        year = quarter[:4]
        q = quarter[4]

        location_data = []
        for loc in locations:
            sales = self._repo.get_sales(loc, business_type, quarter)
            store = self._repo.get_store_count(loc, business_type, quarter)
            if not sales and not store:
                continue

            ss = sales.get("summary", {}) if sales else {}
            st = store.get("summary", {}) if store else {}
            monthly = float(ss.get("monthly_sales_krw", 0))
            cnt = int(st.get("store_count", 0))
            avg = int(monthly / cnt) if cnt > 0 else 0

            location_data.append({
                "location": loc,
                "monthly_sales_krw": monthly,
                "store_count": cnt,
                "avg_sales_per_store_krw": avg,
                "weekday_pct": round(ss.get("weekday_sales_krw", 0) / monthly * 100) if monthly else 0,
                "weekend_pct": round(ss.get("weekend_sales_krw", 0) / monthly * 100) if monthly else 0,
                "open_rate_pct": st.get("open_rate_pct", 0),
                "close_rate_pct": st.get("close_rate_pct", 0),
                "male_pct": round(ss.get("male_sales_krw", 0) / monthly * 100) if monthly else 0,
                "female_pct": round(ss.get("female_sales_krw", 0) / monthly * 100) if monthly else 0,
            })

        if not location_data:
            return {
                "draft": "요청하신 지역들의 데이터를 찾을 수 없습니다. 지역명을 확인해 주십시오.",
                "adm_codes": [],
                "type": "compare",
            }

        analysis = await self._run_compare_agent(location_data, business_type, year, q)
        all_adm_codes = []
        for loc in locations:
            all_adm_codes.extend(self._repo._get_adm_codes(loc))
        return {"draft": analysis, "adm_codes": all_adm_codes, "type": "compare"}

    # ── 오케스트레이터 진입점 ───────────────────────────────────

    @kernel_function(name="generate_draft", description="상권분석 draft 생성")
    async def generate_draft(
        self,
        question: str,
        retry_prompt: str = "",
        profile: str = "",
        prior_history: list[dict] | None = None,
    ) -> dict:
        params = await self._extract_params(question, prior_history=prior_history)
        mode = params["mode"]
        locations = params["locations"]
        business_type = params["business_type"]
        quarter = params["quarter"]

        if not locations or not business_type:
            return {
                "draft": (
                    "분석할 지역명과 업종을 명시해 주십시오.\n"
                    "예: '홍대 카페 상권 분석', '강남 vs 잠실 한식 비교'"
                ),
                "adm_codes": [],
                "type": mode,
            }

        # draft 생성
        if mode == "compare" and len(locations) >= 2:
            result = await self.compare(locations, business_type, quarter)
        else:
            result = await self.analyze(locations[0], business_type, quarter)

        draft = result["draft"]
        adm_codes = result["adm_codes"]

        # retry_prompt 반영 (sign-off 재시도)
        # 데이터 부재·미지원 업종 응답은 재시도해도 달라지지 않으므로 건너뜀
        _NO_DATA_PREFIXES = ("죄송합니다.", "'", "요청하신 지역")
        if retry_prompt and not any(draft.startswith(p) for p in _NO_DATA_PREFIXES):
            retry_prefix = _RETRY_PREFIX.format(retry_prompt=retry_prompt)
            profile_ctx = _PROFILE_CONTEXT.format(profile=profile) if profile else ""

            if mode == "compare" and len(locations) >= 2:
                location_data_lines = ", ".join(locations)
                user_msg = (
                    f"{retry_prefix}{profile_ctx}"
                    f"업종: {business_type} / 지역: {location_data_lines} / 분기: {quarter}\n\n"
                    f"아래는 이전에 생성된 draft입니다. 위 지적 사항을 반영해 전체를 다시 작성하십시오.\n\n"
                    f"{draft}"
                )
                year = quarter[:4]
                q = quarter[4]
                instructions = _COMPARE_INSTRUCTIONS.format(
                    year=year, q=q, business_type=business_type
                )
            else:
                year = quarter[:4]
                q = quarter[4]
                user_msg = (
                    f"{retry_prefix}{profile_ctx}"
                    f"지역: {locations[0]} / 업종: {business_type} / 분기: {quarter}\n\n"
                    f"아래는 이전에 생성된 draft입니다. 위 지적 사항을 반영해 전체를 다시 작성하십시오.\n\n"
                    f"{draft}"
                )
                instructions = _ANALYZE_INSTRUCTIONS.format(year=year, q=q)

            try:
                draft = await self._call_llm(instructions, user_msg)
            except ValueError:
                # 빈 응답 등 retry LLM 실패 시 이전 draft 유지
                logger.warning("LocationAgent retry LLM 실패 — 이전 draft 유지")

        return {"draft": draft, "adm_codes": adm_codes, "type": mode}
