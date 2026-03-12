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
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from db.repository import CommercialRepository


def _make_kernel() -> Kernel:
    k = Kernel()
    k.add_service(AzureChatCompletion(
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    ))
    return k


class LocationAgent:
    def __init__(self):
        self.repo = CommercialRepository()

    async def analyze(self, location: str, business_type: str,
                      quarter: str = "20253") -> dict:
        sales_data = self.repo.get_sales(location, business_type, quarter)
        store_data = self.repo.get_store_count(location, business_type, quarter)

        if not sales_data and not store_data:
            return {
                "error":               "데이터 없음",
                "location":            location,
                "business_type":       business_type,
                "quarter":             quarter,
                "supported_locations": self.repo.get_supported_locations(),
            }

        analysis = await self._run_agent(
            location, business_type, quarter, sales_data, store_data
        )

        return {
            "location":      location,
            "business_type": business_type,
            "quarter":       quarter,
            "sales_data":    sales_data,   # {summary, breakdown}
            "store_data":    store_data,   # {summary, breakdown}
            "analysis":      analysis,
        }

    async def _run_agent(self, location, business_type, quarter,
                          sales_data, store_data) -> str:
        kernel   = _make_kernel()
        settings = AzureChatPromptExecutionSettings()
        year     = quarter[:4]
        q        = quarter[4]

        agent = ChatCompletionAgent(
            name="LocationAgent",
            instructions=(
                "You are a commercial area analysis expert for F&B startups in Seoul. "
                "You receive pre-fetched DB data containing both a summary (합산) and "
                "a breakdown (상권별 분리) for the requested area. "
                "Structure your response as follows:\n"
                "1. 📅 데이터 기준: {year}년 {q}분기\n"
                "2. 📊 전체 합산 요약 (월매출, 점포수, 주중/주말 비율, 피크타임, 주요 고객층)\n"
                "3. 🏪 상권별 분리 분석 (각 상권 특징 비교)\n"
                "4. ✅ 기회 요인 / ⚠️ 리스크 요인\n"
                "Keep it under 500 words. Always respond in Korean."
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        sales_summary   = sales_data.get("summary", {}) if sales_data else {}
        sales_breakdown = sales_data.get("breakdown", []) if sales_data else []
        store_summary   = store_data.get("summary", {}) if store_data else {}
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