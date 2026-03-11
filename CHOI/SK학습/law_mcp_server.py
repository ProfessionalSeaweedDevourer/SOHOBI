
import asyncio
import os
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("law-info-server")

LAW_API_KEY = os.getenv("LAW_API_KEY", "")  # 국가법령정보센터 발급 키
LAW_BASE = "https://www.law.go.kr/DRF/lawSearch.do"


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_law",
            description="국가법령정보센터에서 법령을 검색합니다. 식품위생법, 상가임대차보호법 등 F&B 관련 법령 조회.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 법령명 또는 키워드"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_law_article",
            description="특정 법령의 조문 내용을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_name": {"type": "string", "description": "법령명 (예: 식품위생법)"},
                    "article_no": {"type": "string", "description": "조문 번호 (예: 제37조)"},
                },
                "required": ["law_name", "article_no"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient() as client:
        if name == "search_law":
            resp = await client.get(
                LAW_BASE,
                params={
                    "OC": LAW_API_KEY,
                    "target": "law",
                    "type": "JSON",
                    "query": arguments["query"],
                    "display": 5,
                },
            )
            return [TextContent(type="text", text=resp.text)]

    return [TextContent(type="text", text="알 수 없는 툴: %s" % name)]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
