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

from agent.location_agent import LocationAgent


async def test_single(location: str, business_type: str, quarter: str = "20244"):
    print(f"\n{'='*55}")
    print(f"테스트: {location} / {business_type} / {quarter}")
    print(f"{'='*55}")

    agent = LocationAgent()
    result = await agent.analyze(location, business_type, quarter)

    if "error" in result:
        if result["error"] == "업종 미지원":
            print(
                f"❌ '{result.get('business_type')}' 은(는) 지원하지 않는 업종입니다."
            )
        else:
            print(
                f"❌ '{result.get('location')}' 은(는) 지원하지 않는 지역입니다. 서울 내 지역만 조회 가능합니다."
            )
        return

    sales = result.get("sales_data", {}).get("summary", {})
    store_data = result.get("store_data")
    store = store_data.get("summary", {}) if store_data else {}

    print(f"\n[RAW - 매출]")
    print(f"  월 추정매출: {sales.get('monthly_sales_krw', 0):,}원")
    print(
        f"  주중: {sales.get('weekday_sales_krw', 0):,}원 / 주말: {sales.get('weekend_sales_krw', 0):,}원"
    )
    print(
        f"  11~14시: {sales.get('time_11_14_krw', 0):,}원 / 17~21시: {sales.get('time_17_21_krw', 0):,}원"
    )

    print(f"\n[RAW - 점포]")
    if store:
        print(f"  점포수: {store.get('store_count', 0)}개")
        print(
            f"  개업률: {store.get('open_rate_pct', 0)}% / 폐업률: {store.get('close_rate_pct', 0)}%"
        )
    else:
        print(f"  점포 데이터 없음 (추후 추가 예정)")

    print(f"\n[에이전트 분석]")
    print(result.get("analysis", ""))

    similar = result.get("similar_locations", [])
    if similar:
        print("\n[추천 유사 상권]")
        for s in similar:
            # Oracle 버전은 keyword/avg_sales_per_store_krw 없을 수 있음
            name = s.get("keyword") or s.get("adm_name", "")
            avg = s.get("avg_sales_per_store_krw", 0) // 10000
            score = s.get("score", 0)
            close = s.get("close_rate_pct", "N/A")
            print(f"  📍 {name} - 점포당 평균 {avg}만원, 폐업률 {close}%, 점수 {score}")


async def main():

    async def test_compare(locations, business_type, quarter="20244"):
        print(f"\n{'='*55}")
        print(f"비교: {' vs '.join(locations)} / {business_type} / {quarter}")
        print(f"{'='*55}")
        agent = LocationAgent()
        result = await agent.compare(locations, business_type, quarter)
        if "error" in result:
            print(f"❌ {result['error']}")
            return
        print(result.get("comparison", ""))

    # 정상 케이스
    await test_single("홍대", "카페")
    # await test_single("강남", "한식")
    # await test_single("잠실", "치킨")

    # 비교 케이스
    await test_compare(["홍대", "강남", "잠실"], "카페")

    # 미지원 지역 (에러 처리 확인)
    # await test_single("부산", "카페")
    # await test_single("홍대", "피자")  # 미지원 업종


if __name__ == "__main__":
    asyncio.run(main())
