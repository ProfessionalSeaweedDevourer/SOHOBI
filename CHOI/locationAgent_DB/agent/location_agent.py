"""
location_agent.py
상권분석 에이전트 본체
- DB에서 raw 데이터 조회 후 LLM으로 분석
- 오케스트레이터에서 SK Plugin(location_plugin.py)을 통해 호출됨

[성능 개선]
- Kernel 싱글턴 재사용 (매 호출마다 재생성 방지)
- DB 쿼리 병렬 실행 (asyncio.gather + ThreadPoolExecutor)
- LLM 호출과 유사상권 DB 쿼리 동시 실행
- compare() 지역별 DB 쿼리 병렬 실행
- LLM 프롬프트 토큰 절약 (필요한 필드만 전송)
- 수치 사전 계산 (금액 변환, 비율, 피크타임, 주요 고객층)
"""

import asyncio
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.functions import KernelArguments

from db.repository import CommercialRepository
from chart.location_chart import generate_analyze_charts, generate_compare_charts

# ── Kernel 싱글턴 ──────────────────────────────────────────
_shared_kernel = None


def _get_kernel() -> Kernel:
    """Kernel + AzureChatCompletion 객체를 한 번만 생성하여 재사용"""
    global _shared_kernel
    if _shared_kernel is None:
        _shared_kernel = Kernel()
        _shared_kernel.add_service(
            AzureChatCompletion(
                deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
            )
        )
    return _shared_kernel


# ── 동기 DB 호출을 비동기로 감싸기 위한 스레드풀 ──────────────
_executor = ThreadPoolExecutor(max_workers=4)


# ── 사전 계산 유틸리티 ─────────────────────────────────────
def _format_krw(amount: int) -> str:
    """원 → 억/만원 변환 (예: 2028280000 → '20억 2,828만원')"""
    if not amount:
        return "0만원"
    eok = amount // 100_000_000
    man = (amount % 100_000_000) // 10_000
    if eok > 0:
        return f"{eok}억 {man:,}만원"
    return f"{man:,}만원"


def _calc_pct(part: int, total: int) -> int:
    """비율 계산 (0 나누기 방지)"""
    return round(part / total * 100) if total > 0 else 0


def _find_peak_time(data: dict) -> str:
    """시간대별 매출에서 피크타임 판별"""
    time_slots = {
        "00~06시": data.get("time_00_06_krw", 0),
        "06~11시": data.get("time_06_11_krw", 0),
        "11~14시": data.get("time_11_14_krw", 0),
        "14~17시": data.get("time_14_17_krw", 0),
        "17~21시": data.get("time_17_21_krw", 0),
        "21~24시": data.get("time_21_24_krw", 0),
    }
    return max(time_slots, key=time_slots.get)


def _find_top_age(data: dict) -> tuple:
    """연령대별 매출에서 주요 고객층 판별 → (연령대, 비율%)"""
    total = data.get("monthly_sales_krw", 0) or 1
    ages = {
        "10대": data.get("age_10s_krw", 0),
        "20대": data.get("age_20s_krw", 0),
        "30대": data.get("age_30s_krw", 0),
        "40대": data.get("age_40s_krw", 0),
        "50대": data.get("age_50s_krw", 0),
        "60대": data.get("age_60s_krw", 0),
    }
    top = max(ages, key=ages.get)
    return top, _calc_pct(ages[top], total)


def _precompute_summary(sales_summary: dict, store_summary: dict | None) -> dict:
    """LLM에 보낼 사전 계산된 합산 요약"""
    total = sales_summary.get("monthly_sales_krw", 0) or 1
    top_age, top_age_pct = _find_top_age(sales_summary)

    result = {
        "location": sales_summary.get("location", ""),
        "business_type": sales_summary.get("business_type", ""),
        "monthly_sales": _format_krw(total),
        "weekday_pct": _calc_pct(sales_summary.get("weekday_sales_krw", 0), total),
        "weekend_pct": _calc_pct(sales_summary.get("weekend_sales_krw", 0), total),
        "peak_time": _find_peak_time(sales_summary),
        "male_pct": _calc_pct(sales_summary.get("male_sales_krw", 0), total),
        "female_pct": _calc_pct(sales_summary.get("female_sales_krw", 0), total),
        "top_age": top_age,
        "top_age_pct": top_age_pct,
    }

    if store_summary:
        result["store_count"] = store_summary.get("store_count", 0)
        result["avg_sales_per_store"] = _format_krw(
            sales_summary.get("avg_sales_per_store_krw", 0)
        )
        result["open_rate_pct"] = store_summary.get("open_rate_pct", 0)
        result["close_rate_pct"] = store_summary.get("close_rate_pct", 0)

    return result


def _precompute_breakdown(
    sales_breakdown: list, store_breakdown: list | None
) -> list:
    """LLM에 보낼 사전 계산된 상권별 데이터"""
    store_map = {}
    if store_breakdown:
        store_map = {b["adm_name"]: b for b in store_breakdown}

    items = []
    for s in sales_breakdown:
        total = s.get("monthly_sales_krw", 0) or 1
        top_age, top_age_pct = _find_top_age(s)
        adm_name = s["adm_name"]

        item = {
            "adm_name": adm_name,
            "monthly_sales": _format_krw(total),
            "weekday_pct": _calc_pct(s.get("weekday_sales_krw", 0), total),
            "weekend_pct": _calc_pct(s.get("weekend_sales_krw", 0), total),
            "peak_time": _find_peak_time(s),
            "male_pct": _calc_pct(s.get("male_sales_krw", 0), total),
            "female_pct": _calc_pct(s.get("female_sales_krw", 0), total),
            "top_age": top_age,
            "top_age_pct": top_age_pct,
        }

        st = store_map.get(adm_name)
        if st:
            item["store_count"] = st.get("store_count", 0)
            item["avg_sales_per_store"] = _format_krw(
                s.get("avg_sales_per_store_krw", 0)
            )
            item["open_rate_pct"] = st.get("open_rate_pct", 0)
            item["close_rate_pct"] = st.get("close_rate_pct", 0)

        items.append(item)
    return items


class LocationAgent:
    def __init__(self):
        self.repo = CommercialRepository()

    # ── 단일 지역 분석 ──────────────────────────────────────
    async def analyze(
        self, location: str, business_type: str, quarter: str = "20253"
    ) -> dict:
        supported_industries = self.repo.get_supported_industries()
        if business_type not in supported_industries:
            return {
                "error": "업종 미지원",
                "location": location,
                "business_type": business_type,
                "quarter": quarter,
            }

        loop = asyncio.get_event_loop()

        # ── DB 쿼리 2개 병렬 실행 ──────────────────────────
        sales_data, store_data = await asyncio.gather(
            loop.run_in_executor(
                _executor, self.repo.get_sales, location, business_type, quarter
            ),
            loop.run_in_executor(
                _executor, self.repo.get_store_count, location, business_type, quarter
            ),
        )

        if not sales_data and not store_data:
            year = quarter[:4]
            q = quarter[4:]
            return {
                "error": (
                    f"'{location}' 지역의 '{business_type}' 업종 데이터를 찾을 수 없습니다.\n\n"
                    f"📅 조회 기간: {year}년 {q}분기\n\n"
                    "가능한 원인:\n"
                    "• 서울시 외 지역 (서울시 행정동만 지원)\n"
                    "• 해당 지역에 해당 업종 데이터가 없음\n"
                    "• 지역명이 정확하지 않음\n\n"
                    "💡 서울시 내 지역명으로 다시 시도해 보세요.\n"
                    "예: 홍대, 강남, 잠실, 이태원, 서초, 건대 등"
                ),
                "location": location,
                "business_type": business_type,
                "quarter": quarter,
            }

        # 점포당 평균 매출 계산 (store_data 있을 때만)
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
                b["adm_name"]: b for b in store_data.get("breakdown", [])
            }
            for s in sales_data.get("breakdown", []):
                adm_name = s["adm_name"]
                s_count = store_breakdown_map.get(adm_name, {}).get("store_count", 0)
                s_sales = s.get("monthly_sales_krw", 0)
                s["avg_sales_per_store_krw"] = (
                    int(s_sales / s_count) if s_count > 0 else 0
                )

        # ── LLM 분석 + 유사상권 DB 쿼리 동시 실행 ──────────
        analysis, similar = await asyncio.gather(
            self._run_agent(
                location, business_type, quarter, sales_data, store_data
            ),
            loop.run_in_executor(
                _executor,
                self.repo.get_similar_locations,
                business_type,
                quarter,
                location,
                3,
            ),
        )

        # ── 차트 생성 (sales_summary 기반) ──────────────────
        chart_b64 = []
        if sales_data:
            chart_b64 = generate_analyze_charts(
                sales_data["summary"], location, business_type,
            )

        return {
            "location": location,
            "business_type": business_type,
            "quarter": quarter,
            "sales_data": sales_data,  # {summary, breakdown} — 원본 유지
            "store_data": store_data,  # {summary, breakdown} — 원본 유지
            "analysis": analysis,
            "similar_locations": similar,  # 추천 상권
            "charts": chart_b64,
        }

    async def _run_agent(
        self, location, business_type, quarter, sales_data, store_data
    ) -> str:
        kernel = _get_kernel()
        settings = AzureChatPromptExecutionSettings()
        year = quarter[:4]
        q = quarter[4]

        has_store = store_data is not None

        store_format = (
            ("")  # 점포 데이터 없으면 항목 자체 제외
            if not has_store
            else ("- 점포수: XX개\n" "- 점포당 평균 매출: X,XXX만원\n")
        )

        store_breakdown_format = (
            (
                "- **상권명**: 월매출 XXX억 X,XXX만원, 특징 1~2줄\n"
                "(점포수/개폐업률 데이터 없음 - 절대 점포수/개폐업률 수치 생성 금지)\n"
            )
            if not has_store
            else (
                "- **상권명**: 월매출 XXX억 X,XXX만원, 점포수 XX개, 점포당 평균 X,XXX만원, 개업률 X% / 폐업률 X%, 특징 1~2줄\n"
                "(모든 상권에 개업률과 폐업률을 반드시 포함할 것)\n"
            )
        )

        agent = ChatCompletionAgent(
            name="LocationAgent",
            instructions=(
                "You are a Seoul F&B startup commercial area analysis expert. "
                "Analyze the provided pre-computed data.\n\n"
                "## CRITICAL LANGUAGE RULE\n"
                "You MUST respond ONLY in Korean. "
                "NEVER use English, Russian, Chinese, Japanese, or any other language. "
                "Every single word in your response must be Korean or numbers. "
                "This is an absolute requirement with no exceptions.\n\n"
                "## Response Format (strictly follow this format)\n\n"
                f"📅 데이터 기준: {year}년 {q}분기\n\n"
                "📊 전체 합산 요약\n"
                "(합산 요약 데이터를 그대로 복사하여 출력)\n\n"
                "🏪 상권별 분리 분석\n" + store_breakdown_format + "\n✅ 기회 요인\n"
                "- 핵심 기회 2~3가지 (각 1줄)\n\n"
                "⚠️ 리스크 요인\n"
                "- 핵심 리스크 2~3가지 (각 1줄)\n\n"
                "## Rules (절대 준수)\n"
                "- monthly_sales, peak_time, top_age, weekday_pct 등 데이터에 이미 계산된 값을 반드시 그대로 사용. 절대 자체 판단으로 변경 금지\n"
                "- 피크타임은 반드시 데이터의 peak_time 값을 그대로 출력 (자체 추론 금지)\n"
                "- 지정된 섹션 외 추가 섹션(## 메모, ## 참고 등) 절대 생성 금지\n"
                + (
                    "- 점포 데이터 없으므로 점포수/점포당 평균 매출/개업률/폐업률 항목 절대 출력 금지\n"
                    if not has_store
                    else ""
                )
                + "- 원 단위 절대 사용 금지\n"
                "- 번호 매기기 절대 금지 (1. 2. 3. 사용 금지)\n"
                "- 800자 이내로 작성\n"
                "- 리스크 요인 이후 총평 문장 추가 금지\n"
                "- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지\n"
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        # ── 사전 계산된 데이터 구성 ─────────────────────────
        computed_summary = {}
        computed_breakdown = []
        if sales_data:
            computed_summary = _precompute_summary(
                sales_data["summary"],
                store_data["summary"] if store_data else None,
            )
            computed_breakdown = _precompute_breakdown(
                sales_data.get("breakdown", []),
                store_data.get("breakdown", []) if store_data else None,
            )

        # ── 합산 요약을 텍스트로 직접 구성 (LLM이 그대로 사용) ──
        cs = computed_summary
        summary_text = (
            f"- 월매출: {cs.get('monthly_sales', '0만원')}\n"
            f"- 주중/주말 비율: 주중 {cs.get('weekday_pct', 0)}% / 주말 {cs.get('weekend_pct', 0)}%\n"
            f"- 피크타임: {cs.get('peak_time', '')}\n"
            f"- 주요 고객층: 성별(남성 {cs.get('male_pct', 0)}% / 여성 {cs.get('female_pct', 0)}%), "
            f"연령({cs.get('top_age', '')} {cs.get('top_age_pct', 0)}%)"
        )
        if store_data and cs.get("store_count"):
            summary_text = (
                f"- 월매출: {cs.get('monthly_sales', '0만원')}\n"
                f"- 점포수: {cs.get('store_count', 0)}개\n"
                f"- 점포당 평균 매출: {cs.get('avg_sales_per_store', '0만원')}\n"
                f"- 개업률: {cs.get('open_rate_pct', 0)}% / 폐업률: {cs.get('close_rate_pct', 0)}%\n"
                f"- 주중/주말 비율: 주중 {cs.get('weekday_pct', 0)}% / 주말 {cs.get('weekend_pct', 0)}%\n"
                f"- 피크타임: {cs.get('peak_time', '')}\n"
                f"- 주요 고객층: 성별(남성 {cs.get('male_pct', 0)}% / 여성 {cs.get('female_pct', 0)}%), "
                f"연령({cs.get('top_age', '')} {cs.get('top_age_pct', 0)}%)"
            )

        prompt = (
            f"지역: {location} / 업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[합산 요약 — 아래 수치를 전체 합산 요약 섹션에 그대로 사용할 것]\n{summary_text}\n\n"
            f"[상권별]\n{json.dumps(computed_breakdown, ensure_ascii=False, indent=2)}"
        )

        thread = ChatHistoryAgentThread()
        result = None
        async for msg in agent.invoke(messages=prompt, thread=thread):
            result = str(msg.content)

        return result or ""

    # ── 복수 지역 비교 ──────────────────────────────────────
    async def compare(
        self, locations: list, business_type: str, quarter: str = "20244"
    ) -> dict:
        """복수 지역 비교 분석"""
        supported_industries = self.repo.get_supported_industries()
        if business_type not in supported_industries:
            return {"error": "업종 미지원", "business_type": business_type}

        year = quarter[:4]
        q = quarter[4]

        loop = asyncio.get_event_loop()

        # ── 모든 지역의 sales + store를 한번에 병렬 실행 ────
        tasks = []
        for loc in locations:
            tasks.append(
                loop.run_in_executor(
                    _executor, self.repo.get_sales, loc, business_type, quarter
                )
            )
            tasks.append(
                loop.run_in_executor(
                    _executor, self.repo.get_store_count, loc, business_type, quarter
                )
            )
        results = await asyncio.gather(*tasks)

        # 지역별 데이터 수집 (사전 계산 적용)
        location_data = []
        for i, loc in enumerate(locations):
            sales = results[i * 2]
            store = results[i * 2 + 1]

            if not sales and not store:
                continue

            ss = sales.get("summary", {}) if sales else {}
            st = store.get("summary", {}) if store else {}

            monthly = ss.get("monthly_sales_krw", 0)
            cnt = st.get("store_count", 0) if store else None
            avg = int(monthly / cnt) if (monthly and cnt) else None

            if sales and monthly:
                top_age, top_age_pct = _find_top_age(ss)
                item = {
                    "location": loc,
                    "monthly_sales": _format_krw(monthly),
                    "monthly_sales_raw": monthly,
                    "weekday_pct": _calc_pct(ss.get("weekday_sales_krw", 0), monthly),
                    "weekend_pct": _calc_pct(ss.get("weekend_sales_krw", 0), monthly),
                    "peak_time": _find_peak_time(ss),
                    "male_pct": _calc_pct(ss.get("male_sales_krw", 0), monthly),
                    "female_pct": _calc_pct(ss.get("female_sales_krw", 0), monthly),
                    "top_age": top_age,
                    "top_age_pct": top_age_pct,
                }
            else:
                item = {
                    "location": loc,
                    "monthly_sales": "데이터 없음",
                    "weekday_pct": None,
                    "weekend_pct": None,
                    "male_pct": None,
                    "female_pct": None,
                    "no_sales_data": True,
                }

            if store:
                item["store_count"] = cnt
                item["avg_sales_per_store"] = _format_krw(avg) if avg else "데이터 없음"
                item["avg_per_store_raw"] = avg or 0
                item["open_rate_pct"] = st.get("open_rate_pct", 0)
                item["close_rate_pct"] = st.get("close_rate_pct", 0)

            location_data.append(item)

        if not location_data:
            return {
                "error": (
                    "비교할 지역들의 데이터를 찾을 수 없습니다.\n\n"
                    "💡 서울시 내 지역명으로 다시 시도해 보세요.\n"
                    "예: '강남 vs 홍대 카페 비교'"
                ),
            }

        comparison = await self._run_compare_agent(
            location_data, business_type, year, q
        )

        # ── 비교 차트 생성 ────────────────────────────────────
        charts = generate_compare_charts(location_data, business_type)

        return {
            "locations": locations,
            "business_type": business_type,
            "quarter": quarter,
            "data": location_data,
            "comparison": comparison,
            "charts": charts,
        }

    async def _run_compare_agent(
        self, location_data: list, business_type: str, year: str, q: str
    ) -> str:
        kernel = _get_kernel()
        settings = AzureChatPromptExecutionSettings()

        has_store = "store_count" in location_data[0] if location_data else False

        store_rows = (
            (
                "| 점포수 | XX개 | XX개 |\n"
                "| 점포당 평균매출 | X,XXX만원 | X,XXX만원 |\n"
                "| 개업률 | X.X% | X.X% |\n"
                "| 폐업률 | X.X% | X.X% |\n"
            )
            if has_store
            else ""
        )

        store_rank_rule = (
            (
                "- 창업 추천 순위 기준: 점포당 평균매출 높음 > 폐업률 낮음 > 개업률 적정 순으로 평가\n"
            )
            if has_store
            else (
                "- 창업 추천 순위 기준: 점포 데이터 없으므로 월매출 높음 > 주중비율 높음 > 여성비율 순으로 평가\n"
                "- 점포수/점포당 평균매출/개업률/폐업률 항목 절대 출력 금지\n"
            )
        )

        agent = ChatCompletionAgent(
            name="LocationCompareAgent",
            instructions=(
                "You are a Seoul F&B startup commercial area comparison expert.\n\n"
                "## CRITICAL LANGUAGE RULE\n"
                "You MUST respond ONLY in Korean. "
                "NEVER use English, Russian, Chinese, Japanese, or any other language. "
                "Every single word in your response must be Korean or numbers. "
                "This is an absolute requirement with no exceptions.\n\n"
                "## Response Format (strictly follow this format)\n\n"
                f"📅 데이터 기준: {year}년 {q}분기 / 업종: {business_type}\n\n"
                "📊 지역별 비교표\n\n"
                "| 항목 | 지역A | 지역B | ... |\n"
                "|------|-------|-------|\n"
                "| 월매출 | [monthly_sales] | [monthly_sales] |\n"
                + store_rows
                + "| 주중/주말 | XX%/XX% | XX%/XX% |\n"
                "| 주요 성별 | 남XX%/여XX% | 남XX%/여XX% |\n\n"
                "✅ 창업 추천 순위\n"
                "- **1순위: XXX** - 추천 이유 1~2줄\n"
                "- **2순위: XXX** - 추천 이유 1~2줄\n\n"
                "⚠️ 유의사항\n"
                "- 각 지역별 리스크 1줄씩\n\n"
                "## Rules (절대 준수)\n"
                "- monthly_sales, peak_time, top_age 등 데이터에 이미 계산된 값을 반드시 그대로 사용. 절대 자체 판단으로 변경 금지\n"
                + store_rank_rule
                + "- 유의사항은 비교한 모든 지역에 대해 각각 1줄씩 반드시 작성\n"
                "- 원 단위 절대 사용 금지\n"
                "- 번호 매기기 절대 금지 (추천 순위 제외)\n"
                "- 유의사항 이후 총평 문장 추가 금지\n"
                "- 제공된 데이터만 사용, 임의로 수치 추론/생성 금지\n"
                "- no_sales_data가 true인 지역은 비교표에서 매출/주중주말/성별 항목을 '데이터 없음'으로 표시\n"
                "- 매출 데이터가 없는 지역도 점포수/개업률/폐업률은 정상 출력\n"
                "- 추천 순위 결정 시 매출 데이터 없는 지역은 점포 데이터만으로 평가하고 그 사실을 명시\n"
            ),
            kernel=kernel,
            arguments=KernelArguments(settings=settings),
        )

        prompt = (
            f"업종: {business_type} / 분기: {year}년 {q}분기\n\n"
            f"[지역별 데이터]\n{json.dumps(location_data, ensure_ascii=False, indent=2)}"
        )

        thread = ChatHistoryAgentThread()
        result = None
        async for msg in agent.invoke(messages=prompt, thread=thread):
            result = str(msg.content)

        return result or ""
