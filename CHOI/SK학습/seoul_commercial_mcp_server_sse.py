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

DONG_CODE_MAP = {
    "홍대":     "11440680",
    "홍대입구":  "11440680",
    "강남":     "11680640",
    "역삼":     "11680640",
    "신촌":     "11410530",
    "이태원":   "11170640",
    "건대":     "11305710",
    "합정":     "11440620",
    "잠실":     "11710720",
    "종로":     "11110530",
}

INDUSTRY_CODE_MAP = {
    "카페":       "CS100001",
    "한식":       "CS100001",
    "일반음식점":  "CS100001",
    "치킨":       "CS100003",
    "피자":       "CS100004",
    "패스트푸드":  "CS100005",
    "분식":       "CS100006",
}


@mcp.tool()
def get_estimated_sales(location: str, business_type: str, quarter: str = "20243") -> str:
    """
    Query Seoul commercial area estimated monthly sales
    by administrative district and business type (OA-22175 VwsmAdstrdSelngW).
    location: Location in Korean (e.g. 홍대, 강남, 잠실)
    business_type: Business type in Korean (e.g. 카페, 일반음식점)
    quarter: Quarter YYYYQ (e.g. 20243 = 2024 Q3)
    """
    dong_code     = DONG_CODE_MAP.get(location, "")
    industry_code = INDUSTRY_CODE_MAP.get(business_type, "CS100001")

    if not SEOUL_API_KEY:
        return json.dumps({"error": "SEOUL_API_KEY not set"}, ensure_ascii=False)
    if not dong_code:
        return json.dumps({"error": "Unsupported location", "supported": list(DONG_CODE_MAP.keys())}, ensure_ascii=False)

    url = (
        "%s/%s/json/VwsmAdstrdSelngW/1/5"
        "?STDR_YYQU_CD=%s&ADSTRD_CD=%s&SVC_INDUTY_CD=%s"
    ) % (BASE_URL, urllib.parse.quote(SEOUL_API_KEY), quarter, dong_code, industry_code)

    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        rows = data.get("VwsmAdstrdSelngW", {}).get("row", [])
        if rows:
            row = rows[0]
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
            result = {"message": "No data", "location": location, "quarter": quarter}
    except Exception as e:
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_store_count(location: str, business_type: str, quarter: str = "20243") -> str:
    """
    Query store count and open/close rates
    by administrative district and business type (OA-22172 VwsmAdstrdStorW).
    location: Location in Korean (e.g. 홍대, 강남, 잠실)
    business_type: Business type in Korean (e.g. 카페, 일반음식점)
    quarter: Quarter YYYYQ (e.g. 20243 = 2024 Q3)
    """
    dong_code     = DONG_CODE_MAP.get(location, "")
    industry_code = INDUSTRY_CODE_MAP.get(business_type, "CS100001")

    if not SEOUL_API_KEY:
        return json.dumps({"error": "SEOUL_API_KEY not set"}, ensure_ascii=False)
    if not dong_code:
        return json.dumps({"error": "Unsupported location", "supported": list(DONG_CODE_MAP.keys())}, ensure_ascii=False)

    url = (
        "%s/%s/json/VwsmAdstrdStorW/1/5"
        "?STDR_YYQU_CD=%s&ADSTRD_CD=%s&SVC_INDUTY_CD=%s"
    ) % (BASE_URL, urllib.parse.quote(SEOUL_API_KEY), quarter, dong_code, industry_code)

    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode())
        rows = data.get("VwsmAdstrdStorW", {}).get("row", [])
        if rows:
            row = rows[0]
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
            result = {"message": "No data", "location": location, "quarter": quarter}
    except Exception as e:
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.requests import Request

    port = int(os.getenv("MCP_PORT", "8001"))
    print("Seoul Commercial MCP Server (mcp 1.26 / SSE) on http://localhost:%d/sse" % port)
    print("SEOUL_API_KEY:", "설정됨 ✅" if SEOUL_API_KEY else "❌ 미설정")

    # mcp 1.26.0: SseServerTransport + Starlette 직접 구성
    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
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
