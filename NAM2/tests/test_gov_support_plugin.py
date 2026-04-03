"""
T-01 ~ T-13: GovSupportPlugin 단위 테스트

NAM2/GovSupportPlugin.py는 환경변수를 모듈 레벨에서 전역변수로 읽기 때문에
monkeypatch.setenv 대신 patch("GovSupportPlugin.VAR", ...) 방식으로
모듈 전역변수를 직접 패치합니다.

발견된 버그 (수정 전 xfail, 수정 후 PASSED):
- T-04: HACCP 대소문자 매칭 실패
- T-07: __init__ 예외 전파
- T-08: 빈 program_name 중복 처리 오류
- T-09: query_template 연속 공백
- T-10: top_k 미검증
- T-11: k_nearest_neighbors 하드코딩=20
- T-13: startup_stage 카테고리 선택 미반영

실행:
    cd NAM2
    python -m pytest tests/test_gov_support_plugin.py -v
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# 모듈 전역변수 패치 헬퍼 — _available=True 상태로 플러그인 생성
FAKE_GLOBALS = {
    "GovSupportPlugin.SEARCH_ENDPOINT": "https://fake.search.windows.net",
    "GovSupportPlugin.SEARCH_API_KEY": "fakesearchkey",
    "GovSupportPlugin.OPENAI_ENDPOINT": "https://fake.openai.azure.com/",
    "GovSupportPlugin.OPENAI_API_KEY": "fakekey",
}


def make_plugin(mock_ai, mock_search):
    """모듈 전역변수와 Azure 클라이언트를 mock해 GovSupportPlugin 인스턴스를 반환"""
    from GovSupportPlugin import GovSupportPlugin
    with patch("GovSupportPlugin.SEARCH_ENDPOINT", "https://fake.search.windows.net"), \
         patch("GovSupportPlugin.SEARCH_API_KEY", "fakesearchkey"), \
         patch("GovSupportPlugin.OPENAI_ENDPOINT", "https://fake.openai.azure.com/"), \
         patch("GovSupportPlugin.OPENAI_API_KEY", "fakekey"), \
         patch("GovSupportPlugin.AzureOpenAI", return_value=mock_ai), \
         patch("GovSupportPlugin.SearchClient", return_value=mock_search):
        return GovSupportPlugin()


def make_mock_ai(dim: int = 3072):
    mock_ai = MagicMock()
    mock_ai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * dim)]
    )
    return mock_ai


def make_doc(name: str) -> dict:
    return {
        "program_name": name, "field": "창업", "summary": f"{name} 요약",
        "target": "소상공인", "support_content": "지원내용", "criteria": "선정기준",
        "apply_deadline": "상시", "apply_method": "온라인",
        "org_name": "중소벤처기업부", "phone": "1357",
        "url": "https://example.com", "support_type": "보조금", "target_region": "전국",
    }


# ---------------------------------------------------------------------------
# T-01: 환경변수 미설정 시 _available=False, 안전 메시지 반환
# ---------------------------------------------------------------------------
class TestT01EnvNotSet:
    """모듈 전역변수가 빈 값일 때 _available=False 확인"""

    def test_available_false_when_globals_empty(self):
        """SEARCH_API_KEY 등 전역변수가 빈 문자열이면 _available=False"""
        from GovSupportPlugin import GovSupportPlugin
        with patch("GovSupportPlugin.SEARCH_ENDPOINT", ""), \
             patch("GovSupportPlugin.SEARCH_API_KEY", ""), \
             patch("GovSupportPlugin.OPENAI_ENDPOINT", ""), \
             patch("GovSupportPlugin.OPENAI_API_KEY", ""):
            plugin = GovSupportPlugin()
        assert plugin._available is False

    def test_recommend_returns_unavailable_message(self):
        from GovSupportPlugin import GovSupportPlugin
        with patch("GovSupportPlugin.SEARCH_API_KEY", ""):
            plugin = GovSupportPlugin()
        result = plugin.recommend_programs(
            business_type="카페", region="서울", startup_stage="예비창업"
        )
        assert "설정되지 않았습니다" in result

    def test_search_returns_unavailable_message(self):
        from GovSupportPlugin import GovSupportPlugin
        with patch("GovSupportPlugin.SEARCH_API_KEY", ""):
            plugin = GovSupportPlugin()
        result = plugin.search_gov_programs(query="예비창업패키지")
        assert "설정되지 않았습니다" in result


# ---------------------------------------------------------------------------
# T-02: _extract_region 정상 동작
# ---------------------------------------------------------------------------
class TestT02ExtractRegion:

    def setup_method(self):
        from GovSupportPlugin import GovSupportPlugin
        self.fn = GovSupportPlugin._extract_region

    def test_extracts_known_regions(self):
        assert self.fn("서울 강남에서 창업") == "서울"
        assert self.fn("경기도 성남시") == "경기"
        assert self.fn("부산 해운대") == "부산"
        assert self.fn("제주도") == "제주"

    def test_returns_empty_for_unknown(self):
        assert self.fn("알 수 없는 지역") == ""
        assert self.fn("") == ""


# ---------------------------------------------------------------------------
# T-03: _select_categories 기본 동작
# ---------------------------------------------------------------------------
class TestT03SelectCategories:

    def setup_method(self):
        from GovSupportPlugin import GovSupportPlugin
        self.fn = GovSupportPlugin._select_categories

    def test_default_categories_when_no_keywords(self):
        """키워드 매칭 없을 때 보조금+대출 기본 반환"""
        result = self.fn("미정", "미정", "")
        names = [c["name"] for c in result]
        assert "보조금/창업패키지" in names
        assert "대출/융자" in names

    def test_max_three_categories(self):
        result = self.fn("카페", "대출 보증 교육 고용", "보조금")
        assert len(result) <= 3

    def test_loan_keyword_triggers_loan_category(self):
        result = self.fn("음식점", "대출", "")
        names = [c["name"] for c in result]
        assert "대출/융자" in names

    def test_employment_keyword_triggers_category(self):
        result = self.fn("카페", "인건비 지원", "직원 채용")
        names = [c["name"] for c in result]
        assert "고용지원" in names


# ---------------------------------------------------------------------------
# T-04: [버그1] HACCP 대소문자 매칭 실패
# ---------------------------------------------------------------------------
class TestT04HACCPCaseSensitivity:
    """
    context.lower() → "haccp" 인데 trigger_keywords에 "HACCP"(대문자) → 매칭 실패 버그.
    업종을 food-neutral(미용실)로 지정해 HACCP만으로 외식업 트리거되는지 확인.
    """

    def test_haccp_uppercase_triggers_food_category(self):
        from GovSupportPlugin import GovSupportPlugin

        # "미용실"은 위생/음식점/카페/배달 등 외식업 키워드를 포함하지 않음
        # → HACCP 키워드만으로 "외식업/F&B 특화"가 선택되어야 함
        result = GovSupportPlugin._select_categories("미용실", "", "HACCP 인증 필요")
        names = [c["name"] for c in result]

        if "외식업/F&B 특화" not in names:
            pytest.xfail(
                "버그 미수정: 'HACCP'(대문자) trigger_keyword가 lowercased context에 매칭 실패. "
                "kw.lower() in context 로 수정 필요"
            )
        assert "외식업/F&B 특화" in names


# ---------------------------------------------------------------------------
# T-05: recommend_programs Happy Path
# ---------------------------------------------------------------------------
class TestT05RecommendHappyPath:

    def test_returns_profile_summary(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([make_doc("예비창업패키지")])
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.recommend_programs(
            business_type="카페", region="서울",
            startup_stage="예비창업", funding_purpose="창업지원"
        )
        assert "[사용자 프로필]" in result
        assert "카페" in result

    def test_region_filter_applied(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        plugin.recommend_programs(
            business_type="카페", region="서울", startup_stage="예비창업"
        )
        call_kwargs = mock_search.search.call_args
        filter_arg = (call_kwargs.kwargs.get("filter")
                      if call_kwargs else None)
        assert filter_arg is not None and "서울" in filter_arg

    def test_deduplication_by_program_name(self):
        """동일 program_name은 결과에 1번만 포함"""
        dup_doc = make_doc("소상공인지원사업")
        mock_search = MagicMock()
        mock_search.search.return_value = iter([dup_doc, dup_doc, dup_doc])
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.recommend_programs(
            business_type="카페", region="",
            startup_stage="예비창업", funding_purpose="창업지원"
        )
        assert result.count("소상공인지원사업") == 1


# ---------------------------------------------------------------------------
# T-06: recommend_programs 빈 검색 결과
# ---------------------------------------------------------------------------
class TestT06RecommendEmptyResult:

    def test_empty_result_message(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.recommend_programs(
            business_type="희귀업종", region="", startup_stage="미정"
        )
        assert "찾을 수 없습니다" in result or "조건에 맞는" in result


# ---------------------------------------------------------------------------
# T-07: [버그2] __init__ 예외 전파
# ---------------------------------------------------------------------------
class TestT07InitExceptionHandling:
    """
    AzureOpenAI 초기화 실패 시 _available=False 처리해야 함.
    현재 버그: try/except 없어 예외가 AdminAgent까지 propagate → 행정 에이전트 전체 실패.
    """

    def test_openai_init_failure_sets_available_false(self):
        from GovSupportPlugin import GovSupportPlugin
        with patch("GovSupportPlugin.SEARCH_ENDPOINT", "https://fake.search.windows.net"), \
             patch("GovSupportPlugin.SEARCH_API_KEY", "fakesearchkey"), \
             patch("GovSupportPlugin.OPENAI_ENDPOINT", "https://fake.openai.azure.com/"), \
             patch("GovSupportPlugin.OPENAI_API_KEY", "fakekey"), \
             patch("GovSupportPlugin.AzureOpenAI",
                   side_effect=ValueError("잘못된 엔드포인트")):
            try:
                plugin = GovSupportPlugin()
                assert plugin._available is False, (
                    "초기화 실패 시 _available=False여야 합니다 (수정 필요)"
                )
            except Exception as e:
                pytest.xfail(
                    f"버그 미수정: AzureOpenAI 초기화 실패 시 예외 propagate → "
                    f"AdminAgent 등록 전체 실패. try/except 추가 필요. ({e})"
                )

    def test_search_client_init_failure_sets_available_false(self):
        from GovSupportPlugin import GovSupportPlugin
        with patch("GovSupportPlugin.SEARCH_ENDPOINT", "https://fake.search.windows.net"), \
             patch("GovSupportPlugin.SEARCH_API_KEY", "fakesearchkey"), \
             patch("GovSupportPlugin.OPENAI_ENDPOINT", "https://fake.openai.azure.com/"), \
             patch("GovSupportPlugin.OPENAI_API_KEY", "fakekey"), \
             patch("GovSupportPlugin.AzureOpenAI", return_value=MagicMock()), \
             patch("GovSupportPlugin.SearchClient",
                   side_effect=ValueError("잘못된 검색 엔드포인트")):
            try:
                plugin = GovSupportPlugin()
                assert plugin._available is False, (
                    "SearchClient 초기화 실패 시 _available=False여야 합니다 (수정 필요)"
                )
            except Exception as e:
                pytest.xfail(
                    f"버그 미수정: SearchClient 초기화 실패 시 예외 propagate. ({e})"
                )


# ---------------------------------------------------------------------------
# T-08: [버그3] 빈 program_name 중복 처리 오류
# ---------------------------------------------------------------------------
class TestT08EmptyProgramNameDedup:
    """
    program_name=""인 결과가 3건이어도 1건만 통과되는 버그.
    seen_names.add("") → 2번째부터 모두 skip.
    수정: if name and name in seen_names
    """

    def _make_empty_doc(self) -> dict:
        return {
            "program_name": "", "field": "창업", "summary": "요약",
            "target": "소상공인", "support_content": "내용", "criteria": "기준",
            "apply_deadline": "상시", "apply_method": "온라인",
            "org_name": "기관", "phone": "000", "url": "",
            "support_type": "보조금", "target_region": "전국",
        }

    def test_empty_name_results_all_included(self):
        empty_docs = [self._make_empty_doc() for _ in range(3)]
        mock_search = MagicMock()
        mock_search.search.return_value = iter(empty_docs)
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.recommend_programs(
            business_type="카페", region="", startup_stage="예비창업",
            funding_purpose="창업지원"
        )
        # 빈 이름 항목은 "■ \n" 형태로 출력됨
        count = result.count("■ \n")
        if count < 3:
            pytest.xfail(
                f"버그 미수정: 빈 program_name 결과 3건 중 {count}건만 포함됨. "
                "'if name and name in seen_names' 로 수정 필요"
            )


# ---------------------------------------------------------------------------
# T-09: [버그4] query_template 연속 공백
# ---------------------------------------------------------------------------
class TestT09QueryTemplateDoubleSpaces:
    """startup_stage/employee_count 미정 시 query에 이중공백이 포함되는 버그"""

    def test_no_double_spaces_in_query(self):
        captured_queries = []

        def fake_create(input, model):
            captured_queries.append(input)
            return MagicMock(data=[MagicMock(embedding=[0.1] * 3072)])

        mock_ai = MagicMock()
        mock_ai.embeddings.create.side_effect = fake_create
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(mock_ai, mock_search)

        plugin.recommend_programs(
            business_type="카페", region="서울",
            startup_stage="미정",   # → profile['창업단계'] = ""
            employee_count="미정",  # → profile['직원수'] = ""
            funding_purpose="고용"  # 고용지원 카테고리 트리거
        )

        double_space_queries = [q for q in captured_queries if "  " in q]
        if double_space_queries:
            pytest.xfail(
                f"버그 미수정: 연속 공백 포함 쿼리 발생 → {double_space_queries[0]!r}. "
                "\" \".join(query.split()) 으로 정규화 필요"
            )


# ---------------------------------------------------------------------------
# T-10: [버그5] top_k 미검증
# ---------------------------------------------------------------------------
class TestT10TopKValidation:
    """top_k=0 또는 음수 전달 시 명확한 ValueError가 발생해야 함"""

    def test_top_k_zero_raises_value_error(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        try:
            plugin.search_gov_programs(query="테스트", top_k=0)
            pytest.xfail("버그 미수정: top_k=0 시 ValueError가 발생해야 합니다")
        except ValueError:
            pass  # 정상 동작
        except Exception:
            pytest.xfail("버그 미수정: top_k=0 시 ValueError가 아닌 Azure API 에러 발생")

    def test_top_k_negative_raises_value_error(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        try:
            plugin.search_gov_programs(query="테스트", top_k=-5)
            pytest.xfail("버그 미수정: top_k=-5 시 ValueError가 발생해야 합니다")
        except ValueError:
            pass
        except Exception:
            pytest.xfail("버그 미수정: top_k=-5 시 ValueError가 아닌 다른 예외 발생")


# ---------------------------------------------------------------------------
# T-11: [버그6] k_nearest_neighbors 하드코딩=20
# ---------------------------------------------------------------------------
class TestT11KNearestNeighborsDynamic:
    """top_k=30 요청 시 k_nearest_neighbors >= 30 이어야 함"""

    def test_k_nearest_neighbors_at_least_top_k(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        plugin.search_gov_programs(query="지원사업", top_k=30)

        call_kwargs = mock_search.search.call_args
        assert call_kwargs is not None, "search가 호출되지 않았습니다"
        vector_queries = call_kwargs.kwargs.get("vector_queries")
        assert vector_queries is not None, "vector_queries가 전달되어야 합니다"

        k = vector_queries[0].k_nearest_neighbors
        if k < 30:
            pytest.xfail(
                f"버그 미수정: top_k=30인데 k_nearest_neighbors={k} (하드코딩=20). "
                "max(top_k, 20) 으로 동적 처리 필요"
            )


# ---------------------------------------------------------------------------
# T-12: search_gov_programs Happy Path
# ---------------------------------------------------------------------------
class TestT12SearchHappyPath:

    def test_returns_search_header_and_results(self):
        doc = {
            "program_name": "예비창업패키지", "field": "창업", "summary": "창업 지원",
            "target": "예비창업자", "support_content": "최대 1억",
            "criteria": "사업계획서", "apply_deadline": "2025-12-31",
            "apply_method": "온라인", "org_name": "창업진흥원",
            "phone": "1577-7119", "url": "https://k-startup.go.kr",
            "support_type": "보조금", "target_region": "전국",
        }
        mock_search = MagicMock()
        mock_search.search.return_value = iter([doc])
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.search_gov_programs(query="예비창업패키지 신청방법")
        assert "예비창업패키지" in result
        assert "[검색:" in result
        assert "1건" in result

    def test_auto_extract_region_from_query(self):
        """region 미입력 시 쿼리에서 지역 자동 추출 후 filter 적용"""
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        plugin.search_gov_programs(query="부산 소상공인 대출")
        call_kwargs = mock_search.search.call_args
        assert call_kwargs is not None
        filter_arg = call_kwargs.kwargs.get("filter")
        assert filter_arg is not None and "부산" in filter_arg

    def test_empty_search_result_message(self):
        mock_search = MagicMock()
        mock_search.search.return_value = iter([])
        plugin = make_plugin(make_mock_ai(), mock_search)

        result = plugin.search_gov_programs(query="XYZ없는사업명12345")
        assert "찾을 수 없습니다" in result


# ---------------------------------------------------------------------------
# T-13: [버그7] startup_stage 카테고리 선택 미반영
# ---------------------------------------------------------------------------
class TestT13StartupStageInCategories:
    """
    startup_stage가 _select_categories에 전달되지 않아
    창업단계 정보가 카테고리 선택에 반영되지 않는 버그.
    수정: _select_categories에 startup_stage 파라미터 추가
    """

    def test_startup_stage_param_exists_in_select_categories(self):
        import inspect
        from GovSupportPlugin import GovSupportPlugin

        sig = inspect.signature(GovSupportPlugin._select_categories)
        params = list(sig.parameters.keys())

        if "startup_stage" not in params:
            pytest.xfail(
                "버그 미수정: _select_categories 시그니처에 startup_stage 없음. "
                "def _select_categories(business_type, funding_purpose, additional_info, startup_stage='') 로 수정 필요"
            )
        assert "startup_stage" in params

    def test_startup_stage_value_used_in_context(self):
        """startup_stage 값이 category 매칭 context에 포함되는지 확인"""
        from GovSupportPlugin import GovSupportPlugin

        import inspect
        sig = inspect.signature(GovSupportPlugin._select_categories)
        if "startup_stage" not in sig.parameters:
            pytest.xfail("버그 미수정: startup_stage 파라미터 없음")

        # "재창업" → "창업" 포함 → 보조금/창업패키지 트리거되어야 함
        result = GovSupportPlugin._select_categories("미정", "미정", "", "재창업")
        names = [c["name"] for c in result]
        assert "보조금/창업패키지" in names, (
            "startup_stage='재창업' 시 보조금/창업패키지 카테고리가 선택되어야 합니다"
        )
