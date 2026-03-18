"""
location_agent.py
상권분석 에이전트 본체
- DB에서 raw 데이터 조회 후 LLM으로 분석
- 오케스트레이터에서 SK Plugin(location_plugin.py)을 통해 호출됨
"""

import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.functions import KernelArguments

from db.repository import CommercialRepository


def _make_kernel() -> Kernel:
    k = Kernel()
    k.add_service(
        AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
        )
    )
    return k


class LocationAgent:
    def __init__(self):
        self.repo = CommercialRepository()

    async def analyze(
        self, location: str, business_type: str, quarter: str = "20253"
    ) -> dict:
        sales_data = self.repo.get_sales(location, business_type, quarter)
        store_data = self.repo.get_store_count(location, business_type, quarter)

        supported_industries = self.repo.get_supported_industries()
        if business_type not in supported_industries:
            return {
                "error": "업종 미지원",
                "location": location,
                "business_type": business_type,
                "quarter": quarter,
            }

        if not sales_data and not store_data:
            return {
                "error": "데이터 없음",
                "location": location,
                "business_type": business_type,
                "quarter": quarter,
            }

        # 점포당 평균 매출 계산 (store_data 있을 때만)
        monthly_sales = (
            sales_data.get("summary", {}).get("monthly_sales_krw", 0)
            if sales_data
            else 0
        )
        store_count = (
            store_data.get("summary", {}).get("store_count", 0) if store_data else 0
        )
        avg_per_store = int(monthly_sales / store_count) if store_count > 0 else 0
        if sales_data:
            sales_data["summary"]["avg_sales_per_store_krw"] = avg_per_store
        if sales_data and store_data:
            store_breakdown_map = {
                b["adm_name"]: b for b in store_data.get("breakdown", [])
            }
            for s in sales_data.get("breakdown", []):
                adm_name = s["adm_name"]
                s_count = store_breakdown_map.get(adm_name, {}).get("store_count", 0)
                s_sales = s.get("monthly_sales_krw", 0)
                s["avg_sales_per_store_krw"] = (
                    int(s_sales / s_count) if s_count > 0 else 0
                )

        analysis = await self._run_agent(
            location, business_type, quarter, sales_data, store_data
        )

        # 유사 상권 추천
        similar = self.repo.get_similar_locations(
            business_type=business_type,
            quarter=quarter,
            exclude_location=location,
            top_n=3,
        )

        return {
            "location": location,
            "business_type": business_type,
            "quarter": quarter,
            "sales_data": sales_data,  # {summary, breakdown}
            "store_data": store_data,  # {summary, breakdown}
            "analysis": analysis,
            "similar_locations": similar,  # 추천 상권
        }

    async def _run_agent(
        self, location, business_type, quarter, sales_data, store_data
    ) -> str:
        kernel = _make_kernel()
        settings = AzureChatPromptExecutionSettings()
        year = quarter[:4]
        q = quarter[4]

        has_store = store_data is not None

        store_format = (
            ("")  # 점포 데이터 없으면 항목 자체 제외
            if not has_store
            else ("- 점포수: XX개\n" "- 점포당 평균 매출: XXX만원\n")
        )

        store_breakdown_format = (
            (
                "- **상권명**: 월매출 XXX억 X,XXX만원, 특징 1~2줄\n"
                "(점포수/개폐업률 데이터 없음 - 절대 점포수/개폐업률 수치 생성 금지)\n"
            )
            if not has_store
            else (
                "- **상권명**: 월매출 XXX억 X,XXX만원, 점포수 XX개, 점포당 평균 X,XXX만원, 개업률 X% / 폐업률 X%, 특징 1~2줄\n"
                "(모든 상권에 개업률과 폐업률을 반드시 포함할 것)\n"
            )
        )

        agent = ChatCompletionAgent(
            name="LocationAgent",
            instructions=(
                "You are a Seoul F&B startup commercial area analysis expert. "
                "Analyze the provided summary and breakdown data from DB.\n\n"
                "## CRITICAL LANGUAGE RULE\n"
                "You MUST respond ONLY in Korean. "
                "NEVER use English, Russian, Chinese, Japanese, or any other language. "
                "Every single word in your response must be Korean or numbers. "
                "This is an absolute requirement with no exceptions.\n\n"
                "## Response Format (strictly follow this format)\n\n"
                f"📅 데이터 기준: {year}년 {q}분기\n\n"
                "📊 전체 합산 요약\n"
                "- 월매출: XXX억 X,XXX만원\n"
                + store_format
                + "- 주중/주말 비율: 주중 XX% / 주말 XX%\n"
                "- 피크타임: XX시~XX시\n"
                "- 주요 고객층: 성별(남성 XX% / 여성 XX%), 연령(XX대 중심)\n\n"
                "🏪 상권별 분리 분석\n" + store_breakdown_format + "\n✅ 기회 요인\n"
                "- 핵심 기회 2~3가지 (각 1줄)\n\n"
                "⚠️ 리스크 요인\n"
                "- 핵심 리스크 2~3가지 (각 1줄)\n\n"
                "## Rules\n"
                "- 지정된 섹션 외 추가 섹션(## 메모, ## 참고 등) 절대 생성 금지\n"
                + (
                    "- 점포 데이터 없으므로 점포수/점포당 평균 매출/개업률/폐업률 항목 절대 출력 금지\n"
                    if not has_store
                    else ""
                )
                + "- 금액 변환 규칙: 1억=100,000,000원. "
                "예시) 2,028,280,000 → 20억 2,828만원, "
                "11,366,060,000 → 113억 6,606만원, "
                "315,840,000 → 3억 1,584만원\n"
                "- 모든 금액은 반드시 억/만원 단위로 변환\n"
                "- 점포당 평균 매출도 반드시 만원 단위로 표시\n"
                "- 원 단위 절대 사용 금지\n"
                "- 번호 매기기 절대 금지 (1. 2. 3. 사용 금지)\n"
                "- 800자 이내로 작성\n"
                "- 리스크 요인 이후 총평 문장 추가 금지\n"
                "- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지\n"
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        sales_summary = sales_data.get("summary", {}) if sales_data else {}
        sales_breakdown = sales_data.get("breakdown", []) if sales_data else []

        store_section = (
            (
                f"[점포 합산]\n{json.dumps(store_data.get('summary', {}), ensure_ascii=False, indent=2)}\n\n"
                f"[점포 상권별]\n{json.dumps(store_data.get('breakdown', []), ensure_ascii=False, indent=2)}"
            )
            if store_data
            else "※ 점포 데이터 없음 (매출 데이터만으로 분석할 것)"
        )

        prompt = (
            f"지역: {location} / 업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[매출 합산]\n{json.dumps(sales_summary, ensure_ascii=False, indent=2)}\n\n"
            f"[매출 상권별]\n{json.dumps(sales_breakdown, ensure_ascii=False, indent=2)}\n\n"
            + store_section
        )

        thread = ChatHistoryAgentThread()
        result = None
        async for msg in agent.invoke(messages=prompt, thread=thread):
            result = str(msg.content)

        return result or ""

    async def compare(
        self, locations: list, business_type: str, quarter: str = "20244"
    ) -> dict:
        """복수 지역 비교 분석"""
        supported_industries = self.repo.get_supported_industries()
        if business_type not in supported_industries:
            return {"error": "업종 미지원", "business_type": business_type}

        year = quarter[:4]
        q = quarter[4]

        # 지역별 데이터 수집
        location_data = []
        for loc in locations:
            sales = self.repo.get_sales(loc, business_type, quarter)
            store = self.repo.get_store_count(loc, business_type, quarter)
            if not sales and not store:
                continue

            ss = sales.get("summary", {}) if sales else {}
            st = store.get("summary", {}) if store else {}

            monthly = ss.get("monthly_sales_krw", 0)
            cnt = st.get("store_count", 0) if store else None
            avg = int(monthly / cnt) if cnt else None

            item = {
                "location": loc,
                "monthly_sales_krw": monthly,
                "weekday_pct": (
                    round(ss.get("weekday_sales_krw", 0) / monthly * 100)
                    if monthly
                    else 0
                ),
                "weekend_pct": (
                    round(ss.get("weekend_sales_krw", 0) / monthly * 100)
                    if monthly
                    else 0
                ),
                "male_pct": (
                    round(ss.get("male_sales_krw", 0) / monthly * 100) if monthly else 0
                ),
                "female_pct": (
                    round(ss.get("female_sales_krw", 0) / monthly * 100)
                    if monthly
                    else 0
                ),
            }
            # 점포 데이터 있을 때만 추가
            if store:
                item["store_count"] = cnt
                item["avg_sales_per_store_krw"] = avg
                item["open_rate_pct"] = st.get("open_rate_pct", 0)
                item["close_rate_pct"] = st.get("close_rate_pct", 0)

            location_data.append(item)

        if not location_data:
            return {"error": "데이터 없음"}

        comparison = await self._run_compare_agent(
            location_data, business_type, year, q
        )

        return {
            "locations": locations,
            "business_type": business_type,
            "quarter": quarter,
            "data": location_data,
            "comparison": comparison,
        }

    async def _run_compare_agent(
        self, location_data: list, business_type: str, year: str, q: str
    ) -> str:
        kernel = _make_kernel()
        settings = AzureChatPromptExecutionSettings()

        # 점포 데이터 포함 여부 확인
        has_store = "store_count" in location_data[0] if location_data else False

        store_rows = (
            (
                "| 점포수 | XX개 | XX개 |\n"
                "| 점포당 평균매출 | X,XXX만원 | X,XXX만원 |\n"
                "| 개업률 | X.X% | X.X% |\n"
                "| 폐업률 | X.X% | X.X% |\n"
            )
            if has_store
            else ""
        )

        store_rank_rule = (
            (
                "- 창업 추천 순위 기준: 점포당 평균매출 높음 > 폐업률 낮음 > 개업률 적정 순으로 평가\n"
            )
            if has_store
            else (
                "- 창업 추천 순위 기준: 점포 데이터 없으므로 월매출 높음 > 주중비율 높음 > 여성비율 순으로 평가\n"
                "- 점포수/점포당 평균매출/개업률/폐업률 항목 절대 출력 금지\n"
            )
        )

        agent = ChatCompletionAgent(
            name="LocationCompareAgent",
            instructions=(
                "You are a Seoul F&B startup commercial area comparison expert.\n\n"
                "## CRITICAL LANGUAGE RULE\n"
                "You MUST respond ONLY in Korean. "
                "NEVER use English, Russian, Chinese, Japanese, or any other language. "
                "Every single word in your response must be Korean or numbers. "
                "This is an absolute requirement with no exceptions.\n\n"
                "## Response Format (strictly follow this format)\n\n"
                f"📅 데이터 기준: {year}년 {q}분기 / 업종: {business_type}\n\n"
                "📊 지역별 비교표\n\n"
                "| 항목 | 지역A | 지역B | ... |\n"
                "|------|-------|-------|\n"
                "| 월매출 | XXX억 X,XXX만원 | XXX억 X,XXX만원 |\n"
                + store_rows
                + "| 주중/주말 | XX%/XX% | XX%/XX% |\n"
                "| 주요 성별 | 남XX%/여XX% | 남XX%/여XX% |\n\n"
                "✅ 창업 추천 순위\n"
                "- **1순위: XXX** - 추천 이유 1~2줄\n"
                "- **2순위: XXX** - 추천 이유 1~2줄\n\n"
                "⚠️ 유의사항\n"
                "- 각 지역별 리스크 1줄씩\n\n"
                "## Rules\n"
                + store_rank_rule
                + "- 유의사항은 비교한 모든 지역에 대해 각각 1줄씩 반드시 작성\n"
                "- 모든 금액은 반드시 억/만원 단위로 변환 (예: 24,608,228,093 → 246억 828만원)\n"
                "- 점포당 평균매출도 반드시 만원 단위 (예: 42,722,618 → 4,272만원)\n"
                "- 원 단위 절대 사용 금지\n"
                "- 번호 매기기 절대 금지 (추천 순위 제외)\n"
                "- 유의사항 이후 총평 문장 추가 금지\n"
                "- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지\n"
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        prompt = (
            f"업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[지역별 데이터]\n{json.dumps(location_data, ensure_ascii=False, indent=2)}"
        )

        thread = ChatHistoryAgentThread()
        result = None
        async for msg in agent.invoke(messages=prompt, thread=thread):
            result = str(msg.content)

        return result or ""
