"""
법령 벡터 검색 플러그인 (RAG)
출처: CHOI/vectorSearch/p03_vectorSearch.py, p04_vectorSearchSK.py
변경: 하드코딩된 자격증명 → 환경 변수

개선 (CHOI p03/p04 반영):
- 쿼리 임베딩 LRU 캐싱 (@lru_cache)
- 하이브리드 검색: 벡터 + BM25 키워드
- 시맨틱 리랭킹 + 임계값 필터 (reranker_score < 1.5 제외)
- 법령명 자동 감지 → OData 필터 적용
- auto_invoke_counting_limit=2 (무한 루프 방지)
"""

import logging
import os
from functools import lru_cache
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI
from semantic_kernel.functions import kernel_function

load_dotenv()

logger = logging.getLogger(__name__)

# ── 법령명 목록 (자동 필터용) ──────────────────────────────────
_LAW_NAMES = [
    "식품위생법",
    "근로기준법",
    "상가건물 임대차보호법",
    "최저임금법",
    "부가가치세법",
    "소방시설",
    "공중위생관리법",
    "소득세법",
    "중소기업창업 지원법",
    "건축법",
    "소상공인 보호 및 지원에 관한 법률",
    "국민건강증진법",
    "주세법",
    "폐기물관리법",
]


def _detect_law_filter(query: str) -> str | None:
    """질문에서 법령명을 감지하여 OData 필터 문자열 반환"""
    for name in _LAW_NAMES:
        if name in query:
            return f"search.ismatch('{name}*', 'lawName')"
    return None


class LegalSearchPlugin:
    """Azure AI Search 기반 법령·세무 정보 벡터 검색 플러그인"""

    def __init__(self):
        self._embedding_deployment = os.getenv(
            "AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        )
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        search_key = os.getenv("AZURE_SEARCH_KEY", "")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        index_name = os.getenv("AZURE_SEARCH_INDEX", "legal-index")

        self._available = bool(
            search_key and search_endpoint and openai_endpoint and openai_key
        )
        if self._available:
            try:
                self._ai_client = AzureOpenAI(
                    api_key=openai_key,
                    api_version=os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01"),
                    azure_endpoint=openai_endpoint,
                )
                self._search_client = SearchClient(
                    endpoint=search_endpoint,
                    index_name=index_name,
                    credential=AzureKeyCredential(search_key),
                )
            except Exception:
                self._available = False

    def _get_embedding(self, text: str) -> list[float]:
        """쿼리 임베딩 생성 (인스턴스 메서드 → lru_cache는 모듈 레벨 함수로 위임)"""
        return _cached_embedding(self._ai_client, self._embedding_deployment, text)

    @kernel_function(
        name="search_legal_docs",
        description=(
            "F&B 창업 관련 법률, 위생, 세무, 인허가 정보를 "
            "법령 벡터 DB에서 검색합니다. 질문과 가장 유사한 문서를 반환합니다."
        ),
    )
    def search_legal_docs(
        self,
        query: Annotated[str, "검색할 질문 또는 키워드"],
        top_k: int = 3,
    ) -> str:
        if not self._available:
            return "법령 검색 서비스가 설정되지 않았습니다. (AZURE_SEARCH_KEY, AZURE_SEARCH_ENDPOINT 확인)"

        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError(f"top_k는 1 이상의 정수여야 합니다. (전달값: {top_k!r})")

        try:
            vector = self._get_embedding(query)

            # 법령명 자동 감지 필터 (CHOI p03)
            filter_expr = _detect_law_filter(query)
            if filter_expr:
                logger.debug("LegalSearch 법령 필터 적용: %s", filter_expr)

            # 하이브리드 검색: 벡터 + BM25 + 시맨틱 리랭킹 (CHOI p03)
            results = self._search_client.search(
                search_text=query,
                vector_queries=[
                    VectorizedQuery(
                        vector=vector,
                        k_nearest_neighbors=top_k * 2,  # 리랭킹 여유분
                        fields="content_vector",
                    )
                ],
                query_type="semantic",
                semantic_configuration_name="semantic-config",
                top=top_k,
                filter=filter_expr,
                select=[
                    "id",
                    "lawName",
                    "mst",
                    "articleNo",
                    "chapterTitle",
                    "sectionTitle",
                    "articleTitle",
                    "content",
                    "fullText",
                    "source",
                    "docType",
                    "category",
                ],
            )

            docs = []
            for r in results:
                # 시맨틱 리랭커 임계값 필터: 1.5 미만 제외 (CHOI p03)
                reranker_score = r.get("@search.reranker_score")
                if reranker_score is not None and reranker_score < 1.5:
                    logger.debug(
                        "LegalSearch 낮은 리랭커 점수 제외: %s %s (%.2f)",
                        r.get("lawName", ""),
                        r.get("articleNo", ""),
                        reranker_score,
                    )
                    continue

                # 계층 정보 포함 포매팅 (CHOI p04)
                law_name = r.get("lawName") or r.get("category", "")
                article_no = r.get("articleNo", "")
                article_title = r.get("articleTitle", "")
                chapter = r.get("chapterTitle", "")
                section = r.get("sectionTitle", "")
                content = r.get("fullText") or r.get("content", "")

                hierarchy = " > ".join(filter(None, [law_name, chapter, section]))
                header = f"[{hierarchy}] {article_title or article_no}".strip()
                docs.append(f"{header}\n{content}")

            return (
                "\n\n---\n\n".join(docs)
                if docs
                else "관련 법령 정보를 찾을 수 없습니다."
            )

        except Exception as e:
            logger.error("LegalSearch 검색 오류: %s", e)
            return f"법령 검색 오류: {e}"


# ── 모듈 레벨 LRU 캐시 (동일 쿼리 재호출 시 API 절약) ────────────
@lru_cache(maxsize=128)
def _cached_embedding(
    ai_client: AzureOpenAI,
    deployment: str,
    text: str,
) -> tuple:
    """임베딩 결과를 tuple로 캐싱 (lru_cache는 hashable 인자 필요)"""
    resp = ai_client.embeddings.create(
        input=text.replace("\n", " "),
        model=deployment,
    )
    return tuple(resp.data[0].embedding)
