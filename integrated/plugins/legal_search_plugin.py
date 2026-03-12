"""
법령 벡터 검색 플러그인 (RAG)
출처: CHOI/vectorSearch/p03_vectorSearch.py, p04_vectorSearchSK.py
변경: 하드코딩된 자격증명 → 환경 변수
"""

import os
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI
from semantic_kernel.functions import kernel_function

load_dotenv()


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

        self._available = bool(search_key and search_endpoint and openai_endpoint and openai_key)
        if self._available:
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

        try:
            resp = self._ai_client.embeddings.create(
                input=query,
                model=self._embedding_deployment,
            )
            vector = resp.data[0].embedding

            results = self._search_client.search(
                search_text=None,
                vector_queries=[
                    VectorizedQuery(
                        vector=vector,
                        k_nearest_neighbors=top_k,
                        fields="content_vector",
                    )
                ],
                select=["id", "title", "content", "category"],
            )

            docs = [
                f"[{r.get('category', '')}] {r.get('title', '')}\n{r.get('content', '')}"
                for r in results
            ]
            return "\n\n---\n\n".join(docs) if docs else "관련 법령 정보를 찾을 수 없습니다."

        except Exception as e:
            return f"법령 검색 오류: {e}"
