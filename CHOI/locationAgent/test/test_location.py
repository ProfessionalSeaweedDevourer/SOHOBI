"""
test_location.py
LocationAgent 단독 테스트
오케스트레이터 없이 에이전트 직접 실행
"""

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from db.mock_db import init_db
from agent.location_agent import LocationAgent


async def test_single(location: str, business_type: str, quarter: str = "20244"):
    print(f"\n{'='*55}")
    print(f"테스트: {location} / {business_type} / {quarter}")
    print(f"{'='*55}")

    agent = LocationAgent()
    result = await agent.analyze(location, business_type, quarter)

    if "error" in result:
        print(f"❌ {result['error']}")
        print(f"   지원 지역: {result.get('supported_locations', [])}")
        return

    sales = result.get("sales_data", {}).get("summary", {})
    store = result.get("store_data", {}).get("summary", {})

    print(f"\n[RAW - 매출]")
    print(f"  월 추정매출: {sales.get('monthly_sales_krw', 0):,}원")
    print(
        f"  주중: {sales.get('weekday_sales_krw', 0):,}원 / 주말: {sales.get('weekend_sales_krw', 0):,}원"
    )
    print(
        f"  11~14시: {sales.get('time_11_14_krw', 0):,}원 / 17~21시: {sales.get('time_17_21_krw', 0):,}원"
    )

    print(f"\n[RAW - 점포]")
    print(f"  점포수: {store.get('store_count', 0)}개")
    print(
        f"  개업률: {store.get('open_rate_pct', 0)}% / 폐업률: {store.get('close_rate_pct', 0)}%"
    )

    print(f"\n[에이전트 분석]")
    print(result.get("analysis", ""))


async def main():

    # 정상 케이스
    await test_single("홍대", "카페")
    await test_single("강남", "한식")
    await test_single("잠실", "치킨")

    # 미지원 지역 (에러 처리 확인)
    await test_single("부산", "카페")


if __name__ == "__main__":
    asyncio.run(main())
