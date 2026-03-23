"""
location_plugin.py
오케스트레이터용 SK Plugin 래퍼

출처: CHOI/locationAgent_sang/plugin/location_plugin.py
변경: import 경로를 integrated_PARK 구조에 맞게 수정
     (agents.location_agent, 단일 커널 주입 방식)

[오케스트레이터에서 등록하는 방법]
    from plugins.location_plugin import LocationPlugin
    kernel.add_plugin(LocationPlugin(kernel), plugin_name="LocationAnalysis")
"""

import json

from typing import Annotated
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

from agents.location_agent import LocationAgent


class LocationPlugin:
    """
    오케스트레이터 커널에 등록되는 SK Plugin.
    LLM이 @kernel_function description을 보고 자동으로 호출 판단.
    """

    def __init__(self, kernel: Kernel):
        self._agent = LocationAgent(kernel)

    @kernel_function(
        name="analyze_commercial_area",
        description=(
            "서울 특정 지역의 F&B 상권을 분석합니다. "
            "월 추정매출, 시간대별 매출, 성별/연령대 매출, 점포수, 개폐업률을 DB에서 조회하고 "
            "리스크/기회 분석 및 유사 상권 추천 결과를 반환합니다. "
            "사용자가 특정 지역(예: 홍대, 강남, 잠실)과 업종(예: 카페, 한식, 치킨)을 언급할 때 호출합니다."
        ),
    )
    async def analyze_commercial_area(
        self,
        location: Annotated[str, "분석할 지역명 (예: 홍대, 강남, 잠실)"],
        business_type: Annotated[str, "업종명 (예: 카페, 한식, 치킨)"],
        quarter: Annotated[
            str, "분기코드 YYYYQ (예: 20244). 언급 없으면 20244 사용"
        ] = "20244",
    ) -> str:
        return await self._agent.analyze(location, business_type, quarter)

    @kernel_function(
        name="compare_commercial_areas",
        description=(
            "서울 여러 지역의 F&B 상권을 비교 분석합니다. "
            "지역별 매출, 점포수, 점포당 평균매출, 개폐업률을 비교표로 제공하고 "
            "창업 추천 순위를 반환합니다. "
            "사용자가 두 개 이상의 지역을 비교하거나 추천을 요청할 때 호출합니다. "
            "(예: 홍대 vs 강남, 어디가 더 좋아?)"
        ),
    )
    async def compare_commercial_areas(
        self,
        locations: Annotated[str, "비교할 지역명 목록, 쉼표로 구분 (예: 홍대,강남,잠실)"],
        business_type: Annotated[str, "업종명 (예: 카페, 한식, 치킨)"],
        quarter: Annotated[
            str, "분기코드 YYYYQ (예: 20244). 언급 없으면 20244 사용"
        ] = "20244",
    ) -> str:
        location_list = [loc.strip() for loc in locations.split(",")]
        return await self._agent.compare(location_list, business_type, quarter)
