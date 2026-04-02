"""
T-LA-01 ~ T-LA-19: LocationAgent / LocationPlugin 단위 테스트

실행:
    cd integrated_PARK
    .venv/bin/python -m pytest tests/test_location_agent.py -v

Azure LLM·PostgreSQL DB 호출 없이 mock만 사용합니다.

발견된 버그:
  Bug-1 (T-LA-15): location_plugin.py → str 주석이지만 dict 반환 (SK 직렬화 오류)
  Bug-2 (T-LA-13): _call_llm content_filter 재시도 시 user_msg 누락
  Bug-3 (T-LA-09): analyze()에서 trdar_name 키 접근 → KeyError (올바른 키: adm_name)

추가 이슈 수정:
  Issue-4 (T-LA-18): psycopg2 동기 호출 이벤트 루프 블로킹 → asyncio.to_thread() 적용
  Issue-5 (T-LA-19): _extract_params 정규식이 LLM 앞문장 처리 실패 → re.search() 적용
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ────────────────────────────────────────────────────────────────────────────
# 공통 샘플 데이터
# ────────────────────────────────────────────────────────────────────────────

SAMPLE_SALES = {
    "summary": {
        "location": "홍대",
        "business_type": "카페",
        "quarter": "20244",
        "adm_count": 1,
        "monthly_sales_krw": 1_000_000_000,
        "weekday_sales_krw": 600_000_000,
        "weekend_sales_krw": 400_000_000,
        "male_sales_krw": 400_000_000,
        "female_sales_krw": 600_000_000,
        "time_00_06_krw": 10_000_000,
        "time_06_11_krw": 80_000_000,
        "time_11_14_krw": 250_000_000,
        "time_14_17_krw": 300_000_000,
        "time_17_21_krw": 280_000_000,
        "time_21_24_krw": 80_000_000,
    },
    "breakdown": [
        {
            "adm_name": "홍대",
            "monthly_sales_krw": 1_000_000_000,
            "weekday_sales_krw": 600_000_000,
            "weekend_sales_krw": 400_000_000,
            "male_sales_krw": 400_000_000,
            "female_sales_krw": 600_000_000,
            "time_00_06_krw": 10_000_000,
            "time_06_11_krw": 80_000_000,
            "time_11_14_krw": 250_000_000,
            "time_14_17_krw": 300_000_000,
            "time_17_21_krw": 280_000_000,
            "time_21_24_krw": 80_000_000,
        }
    ],
}

SAMPLE_STORE = {
    "summary": {
        "location": "홍대",
        "business_type": "카페",
        "quarter": "20244",
        "adm_count": 1,
        "store_count": 50,
        "open_rate_pct": 45.0,
        "close_rate_pct": 20.0,
    },
    "breakdown": [
        {
            "adm_name": "홍대",
            "store_count": 50,
            "open_rate_pct": 45.0,
            "close_rate_pct": 20.0,
            "franchise_store_count": 10,
        }
    ],
}

SAMPLE_SIMILAR = [
    {
        "adm_name": "강남",
        "monthly_sales_krw": 2_000_000_000,
        "store_count": 80,
        "avg_sales_per_store_krw": 25_000_000,
        "open_rate_pct": 40.0,
        "close_rate_pct": 18.0,
        "score": 0.85,
    }
]

SUPPORTED_INDUSTRIES = ["카페", "한식", "치킨", "양식", "중식"]


# ────────────────────────────────────────────────────────────────────────────
# 공통 픽스처
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_kernel():
    """mock LLM 서비스가 등록된 가짜 Kernel"""
    mock_response = MagicMock()
    mock_response.__str__ = lambda self: "mock LLM 응답입니다."
    mock_service = AsyncMock()
    mock_service.get_chat_message_content = AsyncMock(return_value=mock_response)

    kernel = MagicMock()
    kernel.get_service = MagicMock(return_value=mock_service)
    return kernel


@pytest.fixture
def mock_repo():
    """CommercialRepository 전체 mock"""
    repo = MagicMock()
    repo.get_supported_industries = MagicMock(return_value=SUPPORTED_INDUSTRIES)
    repo.get_sales = MagicMock(return_value=SAMPLE_SALES)
    repo.get_store_count = MagicMock(return_value=SAMPLE_STORE)
    repo.get_similar_locations = MagicMock(return_value=SAMPLE_SIMILAR)
    repo._get_adm_codes = MagicMock(return_value=["11440660"])
    return repo


# ────────────────────────────────────────────────────────────────────────────
# T-LA-01 ~ T-LA-03: _extract_params JSON 파싱
# ────────────────────────────────────────────────────────────────────────────


class TestExtractParams:
    """_extract_params 파라미터 추출 로직 검증"""

    @pytest.mark.asyncio
    async def test_01_normal_json(self, fake_kernel, mock_repo):
        """T-LA-01: 정상 JSON 파싱"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        payload = json.dumps(
            {"mode": "analyze", "locations": ["홍대"], "business_type": "카페", "quarter": "20244"},
            ensure_ascii=False,
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: payload)
        )

        params = await agent._extract_params("홍대 카페 상권 분석")
        assert params["mode"] == "analyze"
        assert params["locations"] == ["홍대"]
        assert params["business_type"] == "카페"
        assert params["quarter"] == "20244"

    @pytest.mark.asyncio
    async def test_02_json_codeblock(self, fake_kernel, mock_repo):
        """T-LA-02: ```json 코드블록 래핑 제거 후 파싱"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        wrapped = (
            "```json\n"
            '{"mode": "compare", "locations": ["강남", "잠실"], "business_type": "한식", "quarter": "20244"}\n'
            "```"
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: wrapped)
        )

        params = await agent._extract_params("강남 vs 잠실 한식 비교")
        assert params["mode"] == "compare"
        assert params["locations"] == ["강남", "잠실"]

    @pytest.mark.asyncio
    async def test_03_invalid_json_fallback(self, fake_kernel, mock_repo):
        """T-LA-03: LLM이 JSON 반환 실패 시 기본값으로 폴백"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: "죄송합니다 분석할 수 없습니다")
        )

        params = await agent._extract_params("이상한 질문")
        # 폴백 기본값 검증
        assert params["mode"] == "analyze"
        assert params["locations"] == []
        assert params["business_type"] == ""
        assert params["quarter"] == "20244"


# ────────────────────────────────────────────────────────────────────────────
# T-LA-04 ~ T-LA-06: generate_draft 입력 검증
# ────────────────────────────────────────────────────────────────────────────


class TestGenerateDraftGuard:
    """generate_draft 진입점 입력 검증"""

    @pytest.mark.asyncio
    async def test_04_empty_locations(self, fake_kernel, mock_repo):
        """T-LA-04: locations 빈 배열 → 안내 메시지 반환 (LLM 호출 없음)"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        empty_params = json.dumps(
            {"mode": "analyze", "locations": [], "business_type": "카페", "quarter": "20244"},
            ensure_ascii=False,
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: empty_params)
        )

        result = await agent.generate_draft("...")
        assert isinstance(result, dict)
        assert "지역명" in result["draft"] or "명시" in result["draft"]

    @pytest.mark.asyncio
    async def test_05_empty_business_type(self, fake_kernel, mock_repo):
        """T-LA-05: business_type 빈 문자열 → 안내 메시지 반환"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        empty_params = json.dumps(
            {"mode": "analyze", "locations": ["홍대"], "business_type": "", "quarter": "20244"},
            ensure_ascii=False,
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: empty_params)
        )

        result = await agent.generate_draft("홍대 분석해줘")
        assert isinstance(result, dict)
        assert "업종" in result["draft"] or "명시" in result["draft"]

    @pytest.mark.asyncio
    async def test_06_prior_history_none(self, fake_kernel, mock_repo):
        """T-LA-06: prior_history=None 전달 시 예외 없이 처리"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        empty_params = json.dumps(
            {"mode": "analyze", "locations": [], "business_type": "", "quarter": "20244"},
            ensure_ascii=False,
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: empty_params)
        )

        # prior_history=None 이어도 TypeError 없이 반환
        result = await agent.generate_draft("질문", prior_history=None)
        assert isinstance(result, dict)


# ────────────────────────────────────────────────────────────────────────────
# T-LA-07 ~ T-LA-10: analyze() 경로
# ────────────────────────────────────────────────────────────────────────────


class TestAnalyze:
    """analyze() 단일 지역 분석 경로"""

    @pytest.mark.asyncio
    async def test_07_unsupported_industry(self, fake_kernel, mock_repo):
        """T-LA-07: 지원하지 않는 업종 → 안내 메시지 반환 (DB 호출 없음)"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.analyze("홍대", "피자", "20244")
        assert "피자" in result["draft"]
        assert result["adm_codes"] == []
        mock_repo.get_sales.assert_not_called()

    @pytest.mark.asyncio
    async def test_08_no_db_data(self, fake_kernel, mock_repo):
        """T-LA-08: DB 데이터 없음(None) → 안내 메시지 반환"""
        from agents.location_agent import LocationAgent

        mock_repo.get_sales.return_value = None
        mock_repo.get_store_count.return_value = None

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.analyze("부산", "카페", "20244")
        assert "찾을 수 없습니다" in result["draft"] or "확인" in result["draft"]
        assert result["adm_codes"] == []

    @pytest.mark.asyncio
    async def test_09_normal_analysis_no_key_error(self, fake_kernel, mock_repo):
        """T-LA-09 [Bug-3]: 정상 분석 시 KeyError 없이 dict 반환

        Bug: location_agent.py L266,268 에서 breakdown 키 'trdar_name' 접근 →
             실제 키는 'adm_name' → KeyError
        """
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        # KeyError가 발생하면 이 테스트가 실패합니다
        result = await agent.analyze("홍대", "카페", "20244")
        assert isinstance(result, dict)
        assert "draft" in result
        assert "adm_codes" in result
        assert result["type"] == "analyze"
        assert isinstance(result["draft"], str)
        assert len(result["draft"]) > 0

    @pytest.mark.asyncio
    async def test_10_zero_store_count_no_division_error(self, fake_kernel, mock_repo):
        """T-LA-10: store_count=0 일 때 ZeroDivisionError 없음"""
        from agents.location_agent import LocationAgent

        zero_store = dict(SAMPLE_STORE)
        zero_store["summary"] = dict(SAMPLE_STORE["summary"])
        zero_store["summary"]["store_count"] = 0
        zero_store["breakdown"] = [
            {**SAMPLE_STORE["breakdown"][0], "store_count": 0}
        ]
        mock_repo.get_store_count.return_value = zero_store

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        # ZeroDivisionError 없이 반환되어야 합니다
        result = await agent.analyze("홍대", "카페", "20244")
        assert isinstance(result, dict)
        assert "draft" in result


# ────────────────────────────────────────────────────────────────────────────
# T-LA-11 ~ T-LA-12: compare() 경로
# ────────────────────────────────────────────────────────────────────────────


class TestCompare:
    """compare() 복수 지역 비교 경로"""

    @pytest.mark.asyncio
    async def test_11_all_locations_no_data(self, fake_kernel, mock_repo):
        """T-LA-11: 전체 지역 DB 미조회 → 안내 메시지 반환"""
        from agents.location_agent import LocationAgent

        mock_repo.get_sales.return_value = None
        mock_repo.get_store_count.return_value = None

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.compare(["가나다", "라마바"], "카페", "20244")
        assert "찾을 수 없습니다" in result["draft"]
        assert result["adm_codes"] == []

    @pytest.mark.asyncio
    async def test_12_partial_locations(self, fake_kernel, mock_repo):
        """T-LA-12: 일부 지역만 DB 조회됨 → 조회된 지역으로 결과 생성"""
        from agents.location_agent import LocationAgent

        def selective_sales(loc, bt, q):
            return SAMPLE_SALES if loc == "홍대" else None

        def selective_store(loc, bt, q):
            return SAMPLE_STORE if loc == "홍대" else None

        mock_repo.get_sales.side_effect = selective_sales
        mock_repo.get_store_count.side_effect = selective_store

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.compare(["홍대", "없는지역"], "카페", "20244")
        # 데이터가 있는 홍대만으로라도 결과 생성
        assert isinstance(result, dict)
        assert "draft" in result
        assert result["type"] == "compare"


# ────────────────────────────────────────────────────────────────────────────
# T-LA-13 ~ T-LA-14: _call_llm 내부 검증
# ────────────────────────────────────────────────────────────────────────────


class TestCallLlm:
    """_call_llm 내부 동작 검증"""

    @pytest.mark.asyncio
    async def test_13_content_filter_retry_includes_user_msg(self, fake_kernel, mock_repo):
        """T-LA-13 [Bug-2]: content_filter 재시도 시 user_msg 포함 여부

        Bug: ChatHistory(system_message=safe_sys) 만 생성 → user_msg 누락
        Fix: safe_history에 add_user_message(user_msg) 추가
        """
        from agents.location_agent import LocationAgent
        from semantic_kernel.contents import ChatHistory

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        # 첫 호출에서 content_filter 예외, 두 번째 호출에서 정상 반환
        mock_response = MagicMock(__str__=lambda s: "재시도 응답")
        content_filter_error = Exception("content_filter policy violation")

        captured_histories = []

        async def mock_get_content(history, settings=None):
            captured_histories.append(history)
            if len(captured_histories) == 1:
                raise content_filter_error
            return mock_response

        fake_kernel.get_service.return_value.get_chat_message_content = mock_get_content

        result = await agent._call_llm("시스템 메시지", "유저 메시지")

        assert len(captured_histories) == 2, "content_filter 시 재시도가 1회 발생해야 합니다"
        retry_history = captured_histories[1]

        # Bug-2 수정 검증: 재시도 히스토리에 user 메시지가 포함되어야 함
        messages = list(retry_history.messages)
        # SK AuthorRole enum은 "authorrole.user" 형식으로 직렬화됨 → "user" 포함 여부로 확인
        roles = [str(m.role).lower() for m in messages]
        assert any("user" in r for r in roles), (
            "Bug-2: content_filter 재시도 ChatHistory에 user 메시지가 없습니다. "
            "ChatHistory(system_message=safe_sys)에 add_user_message를 추가해야 합니다."
        )

    @pytest.mark.asyncio
    async def test_14_empty_llm_response_raises(self, fake_kernel, mock_repo):
        """T-LA-14: LLM 빈 응답 → ValueError 발생"""
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: "None")
        )

        with pytest.raises(ValueError, match="빈 응답"):
            await agent._call_llm("sys", "user")


# ────────────────────────────────────────────────────────────────────────────
# T-LA-15 ~ T-LA-17: LocationPlugin 검증
# ────────────────────────────────────────────────────────────────────────────


class TestPlugin:
    """location_plugin.py SK Plugin 동작 검증"""

    @pytest.mark.asyncio
    async def test_15_analyze_returns_str(self, fake_kernel, mock_repo):
        """T-LA-15 [Bug-1]: analyze_commercial_area 반환값이 str 인지 확인

        Bug: self._agent.analyze() → dict 반환 → SK Plugin 직렬화 오류
        Fix: json.dumps()로 str 변환 필요
        """
        from plugins.location_plugin import LocationPlugin

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            plugin = LocationPlugin(fake_kernel)

        result = await plugin.analyze_commercial_area("홍대", "카페", "20244")
        assert isinstance(result, str), (
            f"Bug-1: analyze_commercial_area가 str이 아닌 {type(result).__name__}을 반환합니다. "
            "json.dumps()로 직렬화해야 합니다."
        )
        # JSON 파싱 가능한 문자열이어야 함
        parsed = json.loads(result)
        assert "draft" in parsed

    @pytest.mark.asyncio
    async def test_16_compare_locations_comma_split(self, fake_kernel, mock_repo):
        """T-LA-16: compare_commercial_areas 쉼표 파싱 정상 동작"""
        from plugins.location_plugin import LocationPlugin

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            plugin = LocationPlugin(fake_kernel)

        result = await plugin.compare_commercial_areas("홍대,강남,잠실", "카페", "20244")
        assert isinstance(result, str), (
            f"Bug-1: compare_commercial_areas가 str이 아닌 {type(result).__name__}을 반환합니다."
        )
        parsed = json.loads(result)
        assert "draft" in parsed

    @pytest.mark.asyncio
    async def test_17_compare_locations_with_spaces(self, fake_kernel, mock_repo):
        """T-LA-17: 쉼표+공백 구분자 처리 (예: '홍대, 강남, 잠실')"""
        from plugins.location_plugin import LocationPlugin

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            plugin = LocationPlugin(fake_kernel)

        result = await plugin.compare_commercial_areas("홍대, 강남, 잠실", "카페", "20244")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "draft" in parsed


# ────────────────────────────────────────────────────────────────────────────
# T-LA-18 ~ T-LA-19: Issue-4, Issue-5 추가 검증
# ────────────────────────────────────────────────────────────────────────────


class TestAsyncioAndRegex:
    """Issue-4(asyncio.to_thread) / Issue-5(정규식) 검증"""

    @pytest.mark.asyncio
    async def test_18_analyze_uses_asyncio_to_thread(self, fake_kernel, mock_repo):
        """T-LA-18 [Issue-4]: analyze() DB 호출이 asyncio.to_thread()를 사용하는지 검증

        Fix: psycopg2 동기 호출이 이벤트 루프를 블로킹하지 않도록 asyncio.to_thread() 래핑
        """
        import asyncio
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        to_thread_funcs = []
        original_to_thread = asyncio.to_thread

        async def capturing_to_thread(func, *args, **kwargs):
            to_thread_funcs.append(func)
            return await original_to_thread(func, *args, **kwargs)

        with patch("asyncio.to_thread", side_effect=capturing_to_thread):
            await agent.analyze("홍대", "카페", "20244")

        assert mock_repo.get_sales in to_thread_funcs, (
            "Issue-4: get_sales가 asyncio.to_thread()를 통해 호출되어야 합니다. "
            "직접 동기 호출하면 이벤트 루프가 블로킹됩니다."
        )
        assert mock_repo.get_store_count in to_thread_funcs, (
            "Issue-4: get_store_count가 asyncio.to_thread()를 통해 호출되어야 합니다."
        )
        assert mock_repo.get_similar_locations in to_thread_funcs, (
            "Issue-4: get_similar_locations가 asyncio.to_thread()를 통해 호출되어야 합니다."
        )

    @pytest.mark.asyncio
    async def test_19_extract_params_preamble_text(self, fake_kernel, mock_repo):
        """T-LA-19 [Issue-5]: LLM이 앞문장 + JSON 코드블록 형태로 반환할 때 정상 파싱

        Bug: re.sub으로 코드펜스만 제거하면 앞문장이 남아 json.loads() 실패 → 폴백
        Fix: re.search로 코드펜스 내부 JSON만 직접 추출
        """
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        # LLM이 설명 텍스트 + JSON 코드블록 형태로 반환
        preamble_response = (
            "아래는 요청하신 JSON입니다:\n"
            "```json\n"
            '{"mode": "analyze", "locations": ["홍대"], "business_type": "카페", "quarter": "20244"}\n'
            "```"
        )
        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            return_value=MagicMock(__str__=lambda s: preamble_response)
        )

        params = await agent._extract_params("홍대 카페 분석")
        # Issue-5 수정 검증: 앞문장이 있어도 JSON 정상 파싱
        assert params["locations"] == ["홍대"], (
            "Issue-5: LLM 앞문장이 있을 때 JSON 파싱에 실패하여 기본값으로 폴백됩니다. "
            "_extract_params의 정규식을 re.search()로 수정해야 합니다."
        )
        assert params["business_type"] == "카페"
        assert params["mode"] == "analyze"


# ────────────────────────────────────────────────────────────────────────────
# T-LA-20 ~ T-LA-22: generate_draft / compare 엣지케이스 추가 검증
# ────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """추가 발견 이슈 검증"""

    @pytest.mark.asyncio
    async def test_20_compare_unsupported_industry(self, fake_kernel, mock_repo):
        """T-LA-20: compare() 미지원 업종 → 안내 메시지 반환 (DB 호출 없음)

        T-LA-07의 analyze() 대응 케이스 — compare()도 동일 early-return 경로 보유
        """
        from agents.location_agent import LocationAgent

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.compare(["홍대", "강남"], "피자", "20244")
        assert "피자" in result["draft"]
        assert result["adm_codes"] == []
        assert result["type"] == "compare"
        mock_repo.get_sales.assert_not_called()

    @pytest.mark.asyncio
    async def test_21_generate_draft_retry_calls_llm_extra(self, fake_kernel, mock_repo):
        """T-LA-21: retry_prompt 있을 때 LLM 호출이 1회 추가되는지 검증

        흐름: _extract_params(1회) → _run_agent(1회) → retry(1회) = 총 3회
        retry_prompt 없을 때: _extract_params(1회) → _run_agent(1회) = 총 2회
        """
        from agents.location_agent import LocationAgent

        params_json = json.dumps(
            {"mode": "analyze", "locations": ["홍대"], "business_type": "카페", "quarter": "20244"},
            ensure_ascii=False,
        )
        r_params = MagicMock()
        r_params.__str__ = lambda self: params_json
        r_analysis = MagicMock()
        r_analysis.__str__ = lambda self: "1차 분석 결과입니다."
        r_retry = MagicMock()
        r_retry.__str__ = lambda self: "재시도 분석 결과입니다."

        fake_kernel.get_service.return_value.get_chat_message_content = AsyncMock(
            side_effect=[r_params, r_analysis, r_retry]
        )

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        result = await agent.generate_draft(
            "홍대 카페 분석해줘",
            retry_prompt="800자 이내로 작성하십시오.",
        )

        call_count = fake_kernel.get_service.return_value.get_chat_message_content.call_count
        assert call_count == 3, (
            f"retry_prompt 있을 때 LLM 호출이 3회여야 합니다. 실제: {call_count}회"
        )
        assert result["draft"] == "재시도 분석 결과입니다."

    @pytest.mark.asyncio
    async def test_22_generate_draft_llm_failure_returns_guidance(self, fake_kernel, mock_repo):
        """T-LA-22: _run_agent LLM 실패 시 ValueError가 전파되지 않고 안내 메시지 반환

        수정 전: ValueError가 generate_draft() 밖으로 전파 → FastAPI 500 오류
        수정 후: try/except로 잡아 "분석 중 오류" 안내 메시지 반환
        """
        from agents.location_agent import LocationAgent

        params_json = json.dumps(
            {"mode": "analyze", "locations": ["홍대"], "business_type": "카페", "quarter": "20244"},
            ensure_ascii=False,
        )
        call_count = 0

        async def selective_fail(history, settings=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # _extract_params 성공
                r = MagicMock()
                r.__str__ = lambda self: params_json
                return r
            raise ValueError("LLM이 빈 응답을 반환했습니다.")  # _run_agent 실패

        fake_kernel.get_service.return_value.get_chat_message_content = selective_fail

        with patch("agents.location_agent.CommercialRepository", return_value=mock_repo):
            agent = LocationAgent(fake_kernel)

        # ValueError가 전파되지 않고 dict 반환되어야 함
        result = await agent.generate_draft("홍대 카페 분석해줘")
        assert isinstance(result, dict), "ValueError가 전파되면 dict 반환 불가"
        assert "오류" in result["draft"] or "다시 시도" in result["draft"], (
            "LLM 실패 시 사용자 안내 메시지가 draft에 포함되어야 합니다."
        )
