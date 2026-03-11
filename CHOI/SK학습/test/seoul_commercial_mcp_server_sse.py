import os
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("seoul-commercial-server")

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY", "")
BASE_URL = "http://openapi.seoul.go.kr:8088"

# 행정동 코드 (서울시 VwsmAdstrdSelngW 실제 데이터 기준으로 검증된 코드)
DONG_CODE_MAP = {
    # 마포구
    "홍대":     "11440660",  # 서교동 (홍대 상권 중심)
    "서교동":   "11440660",
    "홍대입구":  "11440660",
    "연남동":   "11440710",  # 홍대 인근
    "합정":     "11440680",  # 합정동
    "합정동":   "11440680",
    "망원":     "11440690",  # 망원1동
    "망원동":   "11440690",
    "신촌":     "11410530",  # 서대문구 신촌동 (추후 검증 필요)
    # 강남구
    "강남":     "11680640",  # 역삼1동 (추후 검증 필요)
    "역삼":     "11680640",
    # 용산구
    "이태원":   "11170640",  # (추후 검증 필요)
    # 광진구
    "건대":     "11305710",  # (추후 검증 필요)
    # 송파구
    "잠실":     "11710720",  # 잠실7동 (샘플 데이터로 확인됨)
    # 종로구
    "종로":     "11110530",  # (추후 검증 필요)
}

# 업종 코드 (서울시 VwsmAdstrdSelngW 서교동 실제 데이터로 검증된 코드)
INDUSTRY_CODE_MAP = {
    # 음식점
    "한식":       "CS100001",
    "한식음식점":  "CS100001",
    "중식":       "CS100002",
    "일식":       "CS100003",
    "양식":       "CS100004",
    "제과점":     "CS100005",
    "베이커리":    "CS100005",
    "패스트푸드":  "CS100006",
    "치킨":       "CS100007",
    "분식":       "CS100008",
    "호프":       "CS100009",
    "술집":       "CS100009",
    # 카페
    "카페":       "CS100010",  # ✅ 커피-음료 (기존 CS100001 한식 오류 수정)
    "커피":       "CS100010",
    "음료":       "CS100010",
    # 서비스
    "미용실":     "CS200028",
    "네일":       "CS200029",
    "노래방":     "CS200037",
    # 소매
    "편의점":     "CS300002",
    "약국":       "CS300018",
    "화장품":     "CS300022",
}



PAGE_SIZE = 1000  # 서울시 API 최대 페이지 크기


def _fetch_by_quarter(service_name: str, quarter: str, dong_code: str, industry_code: str) -> dict:
    """
    서울시 API 페이지네이션으로 원하는 행정동+업종 데이터 탐색
    - 1000건씩 페이지 요청, 매칭되면 즉시 반환 (불필요한 요청 최소화)
    - 해당 분기 데이터 없으면 최대 4분기 이전까지 자동 fallback
    """
    current_quarter = quarter

    for attempt in range(4):
        # 1단계: 전체 건수 확인
        url_count = "%s/%s/json/%s/1/1/%s" % (
            BASE_URL, urllib.parse.quote(SEOUL_API_KEY), service_name, current_quarter
        )
        safe = url_count.replace(urllib.parse.quote(SEOUL_API_KEY), "***KEY***")
        print("[MCP] 전체건수 확인: %s" % safe)

        with urllib.request.urlopen(url_count, timeout=10) as r:
            data = json.loads(r.read().decode())
        total = data.get(service_name, {}).get("list_total_count", 0)
        print("[MCP] 분기 %s 전체 건수: %d" % (current_quarter, total))

        if total == 0:
            print("[MCP] 데이터 없음 → 이전 분기 fallback")
            current_quarter = _prev_quarter(current_quarter)
            continue

        # 2단계: 1000건씩 페이지네이션으로 탐색
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        print("[MCP] 총 %d건 / %d페이지 탐색 시작" % (total, total_pages))

        for page in range(total_pages):
            start    = page * PAGE_SIZE + 1
            end      = min(start + PAGE_SIZE - 1, total)
            url_page = "%s/%s/json/%s/%d/%d/%s" % (
                BASE_URL, urllib.parse.quote(SEOUL_API_KEY),
                service_name, start, end, current_quarter
            )
            safe_page = url_page.replace(urllib.parse.quote(SEOUL_API_KEY), "***KEY***")
            print("[MCP] 페이지 %d/%d: %s" % (page + 1, total_pages, safe_page))

            with urllib.request.urlopen(url_page, timeout=15) as r:
                page_data = json.loads(r.read().decode())
            rows = page_data.get(service_name, {}).get("row", [])

            matched = [
                r for r in rows
                if r.get("ADSTRD_CD") == dong_code
                and r.get("SVC_INDUTY_CD") == industry_code
            ]
            if matched:
                print("[MCP] ✅ 매칭! 페이지 %d에서 발견 (분기: %s)" % (page + 1, current_quarter))
                if current_quarter != quarter:
                    print("[MCP] ⚠️ 요청 분기(%s) 없어 %s 데이터 사용" % (quarter, current_quarter))
                return matched[0]

        print("[MCP] 분기 %s 전체 탐색 완료 - 매칭 없음 → 이전 분기 fallback" % current_quarter)
        current_quarter = _prev_quarter(current_quarter)

    return {}

@mcp.tool()
def get_estimated_sales(location: str, business_type: str, quarter: str = "20253") -> str:
    """
    Query Seoul commercial area estimated monthly sales
    by administrative district and business type (OA-22175 VwsmAdstrdSelngW).
    location: Location in Korean (e.g. 홍대, 강남, 잠실)
    business_type: Business type in Korean (e.g. 카페, 일반음식점)
    quarter: Quarter code YYYYQ. Default is 20253 (latest: 2025 Q3).
      Convert natural language to quarter code before calling:
      - "최신" / no mention          → 20253
      - "1분기"                      → current year + "1" (e.g. 20251)
      - "2024년 2분기" / "24년 2분기" → 20242
      - "작년 3분기"                  → (current_year-1) + "3"
      - "올해 1분기"                  → current_year + "1"
      Always pass a 5-digit string like "20253", never pass natural language.
    """
    dong_code     = DONG_CODE_MAP.get(location, "")
    industry_code = INDUSTRY_CODE_MAP.get(business_type, "CS100001")

    if not SEOUL_API_KEY:
        return json.dumps({"error": "SEOUL_API_KEY not set"}, ensure_ascii=False)
    if not dong_code:
        return json.dumps({"error": "Unsupported location", "supported": list(DONG_CODE_MAP.keys())}, ensure_ascii=False)

    try:
        row = _fetch_by_quarter("VwsmAdstrdSelngW", quarter, dong_code, industry_code)
        if row:
            result = {
                "location":           location,
                "dong_name":          row.get("ADSTRD_CD_NM", ""),
                "business_type":      row.get("SVC_INDUTY_CD_NM", business_type),
                "quarter":            row.get("STDR_YYQU_CD", quarter),
                "monthly_sales_krw":  int(row.get("THSMON_SELNG_AMT", 0)),
                "monthly_tx_count":   int(row.get("THSMON_SELNG_CO", 0)),
                "weekday_sales_krw":  int(row.get("MDWK_SELNG_AMT", 0)),
                "weekend_sales_krw":  int(row.get("WKEND_SELNG_AMT", 0)),
                "time_11_14_krw":     int(row.get("TMZON_11_14_SELNG_AMT", 0)),
                "time_17_21_krw":     int(row.get("TMZON_17_21_SELNG_AMT", 0)),
                "male_sales_krw":     int(row.get("ML_SELNG_AMT", 0)),
                "female_sales_krw":   int(row.get("FML_SELNG_AMT", 0)),
                "age_20s_krw":        int(row.get("AGRDE_20_SELNG_AMT", 0)),
                "age_30s_krw":        int(row.get("AGRDE_30_SELNG_AMT", 0)),
                "age_40s_krw":        int(row.get("AGRDE_40_SELNG_AMT", 0)),
                "source":             "서울시 상권분석서비스 VwsmAdstrdSelngW (OA-22175)",
            }
        else:
            result = {
                "message": "No data",
                "location": location,
                "quarter": quarter,
                "note": "행정동 코드(%s) 또는 업종 코드(%s)가 해당 분기 데이터에 없습니다." % (dong_code, industry_code)
            }
    except Exception as e:
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_store_count(location: str, business_type: str, quarter: str = "20253") -> str:
    """
    Query store count and open/close rates
    by administrative district and business type (OA-22172 VwsmAdstrdStorW).
    location: Location in Korean (e.g. 홍대, 강남, 잠실)
    business_type: Business type in Korean (e.g. 카페, 일반음식점)
    quarter: Quarter code YYYYQ. Default is 20253 (latest: 2025 Q3).
      Convert natural language to quarter code before calling:
      - "최신" / no mention          → 20253
      - "1분기"                      → current year + "1" (e.g. 20251)
      - "2024년 2분기" / "24년 2분기" → 20242
      - "작년 3분기"                  → (current_year-1) + "3"
      - "올해 1분기"                  → current_year + "1"
      Always pass a 5-digit string like "20253", never pass natural language.
    """
    dong_code     = DONG_CODE_MAP.get(location, "")
    industry_code = INDUSTRY_CODE_MAP.get(business_type, "CS100001")

    if not SEOUL_API_KEY:
        return json.dumps({"error": "SEOUL_API_KEY not set"}, ensure_ascii=False)
    if not dong_code:
        return json.dumps({"error": "Unsupported location", "supported": list(DONG_CODE_MAP.keys())}, ensure_ascii=False)

    try:
        row = _fetch_by_quarter("VwsmAdstrdStorW", quarter, dong_code, industry_code)
        if row:
            result = {
                "location":        location,
                "dong_name":       row.get("ADSTRD_CD_NM", ""),
                "business_type":   row.get("SVC_INDUTY_CD_NM", business_type),
                "quarter":         row.get("STDR_YYQU_CD", quarter),
                "store_count":     int(row.get("STOR_CO", 0)),
                "open_rate_pct":   float(row.get("OPBIZ_RATE", 0)),
                "close_rate_pct":  float(row.get("CLSBIZ_RATE", 0)),
                "source":          "서울시 상권분석서비스 VwsmAdstrdStorW (OA-22172)",
            }
        else:
            result = {
                "message": "No data",
                "location": location,
                "quarter": quarter,
                "note": "행정동 코드(%s) 또는 업종 코드(%s)가 해당 분기 데이터에 없습니다." % (dong_code, industry_code)
            }
    except Exception as e:
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount

    port = int(os.getenv("MCP_PORT", "8001"))
    print("Seoul Commercial MCP Server (mcp 1.26 / SSE) on http://localhost:%d/sse" % port)
    print("SEOUL_API_KEY:", "설정됨 ✅" if SEOUL_API_KEY else "❌ 미설정")

    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0], streams[1],
                mcp._mcp_server.create_initialization_options()
            )

    starlette_app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ])

    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
