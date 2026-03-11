"""
서울시 상권 분석 플러그인
출처: CHOI/SK학습/seoul_commercial_mcp_server_sse.py
변경: MCP 서버 → 직접 SK 플러그인 (통합 환경에서 별도 서버 불필요)
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Annotated

from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function

load_dotenv()

DONG_CODE_MAP: dict[str, str] = {
    "홍대": "11440680", "홍대입구": "11440680",
    "강남": "11680640", "역삼": "11680640",
    "신촌": "11410530",
    "이태원": "11170640",
    "건대": "11305710",
    "합정": "11440620",
    "잠실": "11710720",
    "종로": "11110530",
}

INDUSTRY_CODE_MAP: dict[str, str] = {
    "카페": "CS100001", "한식": "CS100001", "일반음식점": "CS100001",
    "치킨": "CS100003",
    "피자": "CS100004",
    "패스트푸드": "CS100005",
    "분식": "CS100006",
}


class SeoulCommercialPlugin:
    """서울시 오픈 API 기반 상권 데이터 조회 플러그인"""

    def __init__(self):
        self._api_key = os.getenv("SEOUL_API_KEY", "")
        self._base_url = "http://openapi.seoul.go.kr:8088"
        self._available = bool(self._api_key)

    def _fetch(self, endpoint: str) -> dict:
        url = f"{self._base_url}/{urllib.parse.quote(self._api_key)}/{endpoint}"
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read().decode())

    @kernel_function(
        name="get_estimated_sales",
        description=(
            "서울시 행정동과 업종을 입력받아 분기별 추정 월 매출, "
            "거래 건수, 요일/시간대/성별/연령대별 매출 비중을 반환합니다. "
            "location: 한국어 지역명 (예: 홍대, 강남, 잠실), "
            "business_type: 업종 한국어 (예: 카페, 한식), "
            "quarter: YYYYQ 형식 (예: 20243 = 2024년 3분기)"
        ),
    )
    def get_estimated_sales(
        self,
        location: Annotated[str, "지역명 (예: 홍대, 강남)"],
        business_type: Annotated[str, "업종 (예: 카페, 한식)"],
        quarter: str = "20243",
    ) -> str:
        if not self._available:
            return json.dumps({"error": "SEOUL_API_KEY가 설정되지 않았습니다."}, ensure_ascii=False)

        dong = DONG_CODE_MAP.get(location)
        industry = INDUSTRY_CODE_MAP.get(business_type, "CS100001")
        if not dong:
            return json.dumps(
                {"error": f"지원하지 않는 지역: {location}", "supported": list(DONG_CODE_MAP)},
                ensure_ascii=False,
            )

        try:
            data = self._fetch(
                f"json/VwsmAdstrdSelngW/1/5"
                f"?STDR_YYQU_CD={quarter}&ADSTRD_CD={dong}&SVC_INDUTY_CD={industry}"
            )
            rows = data.get("VwsmAdstrdSelngW", {}).get("row", [])
            if not rows:
                return json.dumps({"message": "데이터 없음", "location": location}, ensure_ascii=False)

            row = rows[0]
            return json.dumps({
                "location": location,
                "dong_name": row.get("ADSTRD_CD_NM", ""),
                "business_type": row.get("SVC_INDUTY_CD_NM", business_type),
                "quarter": row.get("STDR_YYQU_CD", quarter),
                "monthly_sales_krw": int(row.get("THSMON_SELNG_AMT", 0)),
                "monthly_tx_count": int(row.get("THSMON_SELNG_CO", 0)),
                "weekday_sales_krw": int(row.get("MDWK_SELNG_AMT", 0)),
                "weekend_sales_krw": int(row.get("WKEND_SELNG_AMT", 0)),
                "age_20s_krw": int(row.get("AGRDE_20_SELNG_AMT", 0)),
                "age_30s_krw": int(row.get("AGRDE_30_SELNG_AMT", 0)),
                "source": "서울시 상권분석서비스 VwsmAdstrdSelngW (OA-22175)",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @kernel_function(
        name="get_store_count",
        description=(
            "서울시 행정동과 업종을 입력받아 점포 수, 개업률, 폐업률을 반환합니다. "
            "location: 한국어 지역명 (예: 홍대, 강남), "
            "business_type: 업종 한국어 (예: 카페, 한식)"
        ),
    )
    def get_store_count(
        self,
        location: Annotated[str, "지역명 (예: 홍대, 강남)"],
        business_type: Annotated[str, "업종 (예: 카페, 한식)"],
        quarter: str = "20243",
    ) -> str:
        if not self._available:
            return json.dumps({"error": "SEOUL_API_KEY가 설정되지 않았습니다."}, ensure_ascii=False)

        dong = DONG_CODE_MAP.get(location)
        industry = INDUSTRY_CODE_MAP.get(business_type, "CS100001")
        if not dong:
            return json.dumps(
                {"error": f"지원하지 않는 지역: {location}", "supported": list(DONG_CODE_MAP)},
                ensure_ascii=False,
            )

        try:
            data = self._fetch(
                f"json/VwsmAdstrdStorW/1/5"
                f"?STDR_YYQU_CD={quarter}&ADSTRD_CD={dong}&SVC_INDUTY_CD={industry}"
            )
            rows = data.get("VwsmAdstrdStorW", {}).get("row", [])
            if not rows:
                return json.dumps({"message": "데이터 없음", "location": location}, ensure_ascii=False)

            row = rows[0]
            return json.dumps({
                "location": location,
                "dong_name": row.get("ADSTRD_CD_NM", ""),
                "business_type": row.get("SVC_INDUTY_CD_NM", business_type),
                "quarter": row.get("STDR_YYQU_CD", quarter),
                "store_count": int(row.get("STOR_CO", 0)),
                "open_rate_pct": float(row.get("OPBIZ_RATE", 0)),
                "close_rate_pct": float(row.get("CLSBIZ_RATE", 0)),
                "source": "서울시 상권분석서비스 VwsmAdstrdStorW (OA-22172)",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
