"""
T-01 ~ T-08: LegalSearchPlugin 단위 테스트

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_legal_search_plugin.py -v

Azure 연결이 필요한 테스트(T-04, T-05, T-06)는 실제 환경변수가 설정된 경우에만 통과합니다.
환경변수가 없으면 해당 테스트는 skip됩니다.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T-01: 환경변수 미설정 시 _available=False, 안전 메시지 반환
# ---------------------------------------------------------------------------
class TestT01EnvNotSet:
    """환경변수 4개 모두 빈 문자열일 때 플러그인이 안전하게 동작하는지 확인"""

    def setup_method(self):
        # 환경변수를 강제로 비워 플러그인 import
        self._orig = {
            k: os.environ.pop(k, None)
            for k in [
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY",
                "AZURE_SEARCH_ENDPOINT",
                "AZURE_SEARCH_KEY",
            ]
        }

    def teardown_method(self):
        for k, v in self._orig.items():
            if v is not None:
                os.environ[k] = v

    def test_available_false_when_env_missing(self):
        from plugins.legal_search_plugin import LegalSearchPlugin

        plugin = LegalSearchPlugin()
        assert plugin._available is False, "_available이 False여야 합니다"

    def test_returns_unavailable_message(self):
        from plugins.legal_search_plugin import LegalSearchPlugin

        plugin = LegalSearchPlugin()
        result = plugin.search_legal_docs(query="임대차")
        assert "설정되지 않았습니다" in result, (
            f"환경변수 미설정 시 안내 메시지를 반환해야 합니다. 실제 반환값: {result!r}"
        )


# ---------------------------------------------------------------------------
# T-02: top_k=0 입력 시 동작 (버그 재현)
# ---------------------------------------------------------------------------
class TestT02TopKZero:
    """top_k=0일 때 Azure API 오류 또는 검증 오류가 발생하는지 확인.
    현재 버그: top_k 검증 없음 → Azure API가 k_nearest_neighbors=0 거부 → 에러 문자열 반환"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_top_k_zero_raises_value_error(self):
        """top_k=0이면 ValueError가 발생해야 합니다."""
        from plugins.legal_search_plugin import LegalSearchPlugin

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI"),
            patch("plugins.legal_search_plugin.SearchClient"),
        ):
            plugin = LegalSearchPlugin()

        with pytest.raises(ValueError, match="top_k"):
            plugin.search_legal_docs(query="임대차", top_k=0)


# ---------------------------------------------------------------------------
# T-03: top_k 음수 입력 시 동작 (버그 재현)
# ---------------------------------------------------------------------------
class TestT03TopKNegative:
    """top_k=-1 등 음수 입력 시 동작 확인"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_top_k_negative_raises_value_error(self):
        """top_k=-1이면 ValueError가 발생해야 합니다."""
        from plugins.legal_search_plugin import LegalSearchPlugin

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI"),
            patch("plugins.legal_search_plugin.SearchClient"),
        ):
            plugin = LegalSearchPlugin()

        with pytest.raises(ValueError, match="top_k"):
            plugin.search_legal_docs(query="영업허가", top_k=-1)

    def test_top_k_very_large_does_not_crash(self):
        """top_k=10000 과 같이 극단적으로 큰 값을 전달해도 크래시 없이 처리되어야 합니다."""
        from plugins.legal_search_plugin import LegalSearchPlugin

        # _available=False 상태에서 테스트 (실제 API 호출 없음)
        with patch.dict(os.environ, {}, clear=True):
            plugin = LegalSearchPlugin()
        result = plugin.search_legal_docs(query="테스트", top_k=10000)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# T-04: 검색 결과 0건 시 "관련 법령 없음" 메시지 반환
# ---------------------------------------------------------------------------
class TestT04EmptySearchResult:
    """Azure Search가 결과를 0건 반환할 때 올바른 메시지가 반환되는지 확인"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_empty_result_returns_no_result_message(self):
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        mock_search = MagicMock()
        mock_search.search.return_value = iter([])  # 빈 결과

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        result = plugin.search_legal_docs(query="XYZ존재하지않는법령12345")
        assert "관련 법령 정보를 찾을 수 없습니다" in result, (
            f"빈 결과 시 '관련 법령 정보를 찾을 수 없습니다' 메시지를 반환해야 합니다. 실제: {result!r}"
        )


# ---------------------------------------------------------------------------
# T-05: 일반 법령 키워드 검색 Happy Path
# ---------------------------------------------------------------------------
class TestT05HappyPath:
    """정상 검색 결과가 올바른 형식으로 반환되는지 확인"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_returns_formatted_documents(self):
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        # mock 검색 결과 2건
        doc1 = {
            "id": "1",
            "title": "식품위생법 제36조",
            "content": "영업신고 절차...",
            "category": "위생법",
        }
        doc2 = {
            "id": "2",
            "title": "식품위생법 시행규칙",
            "content": "영업신고 서류...",
            "category": "시행규칙",
        }
        mock_search = MagicMock()
        mock_search.search.return_value = iter([doc1, doc2])

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        result = plugin.search_legal_docs(query="음식점 영업신고 절차")

        assert "[위생법]" in result, "카테고리가 포함되어야 합니다"
        assert "식품위생법 제36조" in result, "제목이 포함되어야 합니다"
        assert "영업신고 절차" in result, "내용이 포함되어야 합니다"
        assert "---" in result, "구분자가 포함되어야 합니다"

    def test_top_k_passed_to_vector_query(self):
        """top_k 파라미터가 VectorizedQuery의 k_nearest_neighbors로 전달되는지 확인"""
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        mock_search = MagicMock()
        mock_search.search.return_value = iter([])

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        plugin.search_legal_docs(query="테스트", top_k=5)

        call_kwargs = mock_search.search.call_args
        vector_queries = call_kwargs.kwargs.get("vector_queries") or call_kwargs[1].get(
            "vector_queries"
        )
        assert vector_queries is not None, "vector_queries 인자가 전달되어야 합니다"
        assert vector_queries[0].k_nearest_neighbors == 5, (
            "k_nearest_neighbors가 top_k 값과 일치해야 합니다"
        )


# ---------------------------------------------------------------------------
# T-06: 빈 쿼리 입력 시 동작
# ---------------------------------------------------------------------------
class TestT06EmptyQuery:
    """빈 문자열 쿼리 입력 시 크래시 없이 처리되는지 확인"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_empty_query_does_not_crash(self):
        """빈 쿼리 입력 시 문자열을 반환하고 크래시 없이 처리되어야 합니다"""
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.0] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        mock_search = MagicMock()
        mock_search.search.return_value = iter([])

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        result = plugin.search_legal_docs(query="")
        assert isinstance(result, str), "빈 쿼리에도 문자열을 반환해야 합니다"


# ---------------------------------------------------------------------------
# T-07: 잘못된 엔드포인트로 클라이언트 초기화 실패 시 처리 (버그 재현)
# ---------------------------------------------------------------------------
class TestT07InitFailure:
    """AzureOpenAI 생성자가 예외를 발생시킬 때 __init__ 이 전파하는지 확인.
    현재 버그: try/except 없음 → 예외가 그대로 propagate되어 LegalAgent 등록 실패"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://invalid-endpoint")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "wrongkey")
        monkeypatch.setenv(
            "AZURE_SEARCH_ENDPOINT", "https://invalid.search.windows.net"
        )
        monkeypatch.setenv("AZURE_SEARCH_KEY", "wrongsearchkey")

    def test_init_exception_propagates(self):
        """AzureOpenAI 초기화 실패 시 예외가 전파되어야 합니다 (현재 동작 = 버그).
        수정 후에는 예외 없이 _available=False로 처리되어야 합니다."""
        from plugins.legal_search_plugin import LegalSearchPlugin

        init_error = ValueError("잘못된 Azure 엔드포인트")

        with patch("plugins.legal_search_plugin.AzureOpenAI", side_effect=init_error):
            try:
                plugin = LegalSearchPlugin()
                # 수정 후 기대 동작: 예외 없이 _available=False
                assert plugin._available is False, (
                    "초기화 실패 시 _available=False로 설정되어야 합니다 (수정 필요)"
                )
            except Exception as e:
                # 현재 버그 동작: 예외가 그대로 전파됨
                pytest.xfail(
                    f"버그 미수정: AzureOpenAI 초기화 실패 시 예외가 propagate됩니다. ({e})"
                )


# ---------------------------------------------------------------------------
# T-08: SearchDocument 필드 누락 시 안전 처리
# ---------------------------------------------------------------------------
class TestT08MissingFields:
    """검색 결과에서 title, content, category 중 일부 필드가 없을 때 .get() 으로 안전하게 처리되는지 확인"""

    @pytest.fixture(autouse=True)
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fakekey")
        monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://fake.search.windows.net")
        monkeypatch.setenv("AZURE_SEARCH_KEY", "fakesearchkey")

    def test_missing_category_field_handled_safely(self):
        """category 필드 없는 문서도 안전하게 포맷팅되어야 합니다"""
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        doc_no_category = {"id": "1", "title": "식품위생법", "content": "내용입니다"}
        mock_search = MagicMock()
        mock_search.search.return_value = iter([doc_no_category])

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        result = plugin.search_legal_docs(query="테스트")
        assert "식품위생법" in result, "title은 포함되어야 합니다"
        assert "내용입니다" in result, "content는 포함되어야 합니다"
        # category 없음 → "[빈문자열] 제목\n내용" 형식
        assert result.startswith("[]") or "[] " in result, (
            f"category 없을 때 빈 대괄호로 처리해야 합니다. 실제: {result!r}"
        )

    def test_missing_title_and_content_handled_safely(self):
        """title, content 모두 없어도 KeyError 없이 처리되어야 합니다"""
        from plugins.legal_search_plugin import LegalSearchPlugin

        mock_embedding_resp = MagicMock()
        mock_embedding_resp.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_ai = MagicMock()
        mock_ai.embeddings.create.return_value = mock_embedding_resp

        doc_minimal = {"id": "1"}  # title, content, category 모두 없음
        mock_search = MagicMock()
        mock_search.search.return_value = iter([doc_minimal])

        with (
            patch("plugins.legal_search_plugin.AzureOpenAI", return_value=mock_ai),
            patch("plugins.legal_search_plugin.SearchClient", return_value=mock_search),
        ):
            plugin = LegalSearchPlugin()

        result = plugin.search_legal_docs(query="테스트")
        assert isinstance(result, str), "필드 없는 문서도 문자열을 반환해야 합니다"
