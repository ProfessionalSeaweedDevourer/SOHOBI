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
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
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

        # 점포당 평균 매출 계산
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
                b["trdar_name"]: b for b in store_data.get("breakdown", [])
            }
            for s in sales_data.get("breakdown", []):
                trdar_name = s["trdar_name"]
                s_count = store_breakdown_map.get(trdar_name, {}).get("store_count", 0)
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

        agent = ChatCompletionAgent(
            name="LocationAgent",
            instructions=(
                "You are a Seoul F&B startup commercial area analysis expert. "
                "Analyze the provided summary and breakdown data from DB.\n\n"
                "## Response Format (strictly follow this format)\n\n"
                "📅 데이터 기준: {year}년 {q}분기\n\n"
                "📊 전체 합산 요약\n"
                "- 월매출: XXX억 X,XXX만원\n"
                "- 점포수: XX개\n"
                "- 주중/주말 비율: 주중 XX% / 주말 XX%\n"
                "- 피크타임: XX시~XX시\n"
                "- 주요 고객층: 성별(남성 XX% / 여성 XX%), 연령(XX대 중심)\n"
                "- 점포당 평균 매출: XXX만원\n\n"
                "🏪 상권별 분리 분석\n"
                "- **상권명**: 월매출 XXX억원, 점포수 XX개, 점포당 평균 XXX만원, 개업률 X% / 폐업률 X%, 특징 1~2줄\n"
                "(모든 상권에 개업률과 폐업률을 반드시 포함할 것)\n\n"
                "✅ 기회 요인\n"
                "- 핵심 기회 2~3가지 (각 1줄)\n\n"
                "⚠️ 리스크 요인\n"
                "- 핵심 리스크 2~3가지 (각 1줄)\n\n"
                "## Rules\n"
                "- Convert sales to 억/만원 unit (e.g. 24,608,228,093 → 246억 828만원)\n"
                "- Never use numbering (1. 2. 3.), strictly follow the format above\n"
                "- Keep under 500 words\n"
                "- Do not add any closing summary sentence after the risk factors.\n"
                "- Round sales to the nearest 만원, do not show 원 units (e.g. 6억 5,247만원, NOT 6억 5,247만 2,006원)\n"
                "- Only use data explicitly provided. Never infer, assume, or fabricate any figures not present in the data\n"
                "- Always respond in Korean"
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        sales_summary = sales_data.get("summary", {}) if sales_data else {}
        sales_breakdown = sales_data.get("breakdown", []) if sales_data else []
        store_summary = store_data.get("summary", {}) if store_data else {}
        store_breakdown = store_data.get("breakdown", []) if store_data else []

        prompt = (
            f"지역: {location} / 업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[매출 합산]\n{json.dumps(sales_summary, ensure_ascii=False, indent=2)}\n\n"
            f"[매출 상권별]\n{json.dumps(sales_breakdown, ensure_ascii=False, indent=2)}\n\n"
            f"[점포 합산]\n{json.dumps(store_summary, ensure_ascii=False, indent=2)}\n\n"
            f"[점포 상권별]\n{json.dumps(store_breakdown, ensure_ascii=False, indent=2)}"
        )

        thread = ChatHistoryAgentThread()
        result = ""
        async for msg in agent.invoke(messages=prompt, thread=thread):
            result += str(msg.content)

        return result
