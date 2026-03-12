"""
location_plugin.py
오케스트레이터용 SK Plugin 래퍼

[오케스트레이터에서 등록하는 방법]
    from location_agent.plugin.location_plugin import LocationPlugin
    kernel.add_plugin(LocationPlugin(), plugin_name="LocationAnalysis")
"""

import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from typing import Annotated
from semantic_kernel.functions import kernel_function

from agent.location_agent import LocationAgent


class LocationPlugin:
    """
    오케스트레이터 커널에 등록되는 SK Plugin
    LLM이 @kernel_function description을 보고 자동으로 호출 판단
    """

    def __init__(self):
        self._agent = LocationAgent()

    @kernel_function(
        name="analyze_commercial_area",
        description=(
            "서울 특정 지역의 F&B 상권을 분석합니다. "
            "월 추정매출, 시간대별 매출, 성별/연령대 매출, 점포수, 개폐업률을 DB에서 조회하고 "
            "리스크/기회 분석 결과를 반환합니다. "
            "사용자가 특정 지역(예: 홍대, 강남, 잠실)과 업종(예: 카페, 한식, 치킨)을 언급할 때 호출합니다."
        ),
    )
    async def analyze_commercial_area(
        self,
        location: Annotated[str, "분석할 지역명 (예: 홍대, 강남, 잠실)"],
        business_type: Annotated[str, "업종명 (예: 카페, 한식, 치킨)"],
        quarter: Annotated[
            str, "분기코드 YYYYQ (예: 20253). 언급 없으면 20253 사용"
        ] = "20253",
    ) -> str:
        result = await self._agent.analyze(location, business_type, quarter)

        if "error" in result:
            return json.dumps(result, ensure_ascii=False)

        sales_summary = result.get("sales_data", {}).get("summary", {})
        store_summary = result.get("store_data", {}).get("summary", {})

        # 오케스트레이터에게 분석 텍스트 + raw 핵심 수치 반환
        output = {
            "location": result["location"],
            "business_type": result["business_type"],
            "quarter": result["quarter"],
            "monthly_sales_krw": sales_summary.get("monthly_sales_krw", 0),
            "store_count": store_summary.get("store_count", 0),
            "open_rate_pct": store_summary.get("open_rate_pct", 0),
            "close_rate_pct": store_summary.get("close_rate_pct", 0),
            "analysis": result["analysis"],
        }
        return json.dumps(output, ensure_ascii=False)
