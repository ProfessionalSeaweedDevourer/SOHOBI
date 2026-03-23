"""
정부지원사업 벡터 검색 플러그인 (RAG)
- Azure AI Search 인덱스: gov-programs-index
- 데이터 소스: 정부24 공공서비스 API (1,440건)
- 검색: 하이브리드 (키워드 + 벡터) + 시맨틱 랭커
- 행정 에이전트(AdminAgent)에서 사용
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

REGION_MAP = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
    "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
    "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남",
    "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남",
    "제주": "제주",
}


class GovSupportPlugin:
    """정부지원사업 벡터 검색 플러그인 — gov-programs-index 기반 RAG"""

    def __init__(self):
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        search_key = os.getenv("AZURE_SEARCH_API_KEY", "") or os.getenv("AZURE_SEARCH_KEY", "")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        self._embedding_deployment = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        )

        self._available = bool(search_key and search_endpoint and openai_endpoint and openai_key)
        if self._available:
            self._ai_client = AzureOpenAI(
                api_key=openai_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=openai_endpoint,
            )
            self._search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "gov-programs-index"),
                credential=AzureKeyCredential(search_key),
            )

    @staticmethod
    def _extract_region(text: str) -> str:
        for keyword, region in REGION_MAP.items():
            if keyword in text:
                return region
        return ""

    @kernel_function(
        name="search_gov_programs",
        description=(
            "F&B 창업자를 위한 정부지원사업, 보조금, 창업패키지 정보를 검색합니다. "
            "업종, 지역, 신청기간 등을 고려해 적합한 지원사업을 반환합니다."
        ),
    )
    def search_gov_programs(
        self,
        query: Annotated[str, "검색할 질문 또는 키워드 (예: 서울 카페 창업 지원사업)"],
        top_k: int = 10,
        region: Annotated[str, "지역 필터 (예: 서울, 경기, 전국). 없으면 쿼리에서 자동 추출"] = "",
    ) -> str:
        if not self._available:
            return "정부지원사업 검색 서비스가 설정되지 않았습니다. (AZURE_SEARCH_API_KEY, AZURE_SEARCH_ENDPOINT 확인)"

        try:
            resp = self._ai_client.embeddings.create(
                input=query,
                model=self._embedding_deployment,
            )
            vector = resp.data[0].embedding

            if not region:
                region = self._extract_region(query)

            filter_str = None
            if region:
                filter_str = f"(target_region eq '{region}' or target_region eq '전국')"

            results = self._search_client.search(
                search_text=query,
                vector_queries=[
                    VectorizedQuery(
                        vector=vector,
                        k_nearest_neighbors=20,
                        fields="embedding",
                    )
                ],
                filter=filter_str,
                query_type="semantic",
                semantic_configuration_name="sohobi-semantic",
                select=[
                    "program_name", "field", "summary", "target",
                    "support_content", "criteria", "apply_deadline",
                    "apply_method", "org_name", "phone", "url",
                    "support_type", "target_region"
                ],
                top=top_k,
            )

            docs = []
            for i, r in enumerate(results, 1):
                doc = (
                    f"[결과 {i}]\n"
                    f"사업명: {r.get('program_name', '-')}\n"
                    f"분야: {r.get('field', '-')} | 유형: {r.get('support_type', '-')} | 지역: {r.get('target_region', '-')}\n"
                    f"대상: {r.get('target', '-')}\n"
                    f"선정기준: {r.get('criteria', '-')}\n"
                    f"지원내용: {r.get('support_content', '-')}\n"
                    f"신청방법: {r.get('apply_method', '-')}\n"
                    f"신청기한: {r.get('apply_deadline', '-')}\n"
                    f"기관: {r.get('org_name', '-')} | 문의: {r.get('phone', '-')}\n"
                    f"링크: {r.get('url', '-')}"
                )
                docs.append(doc)

            if not docs:
                return f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n조건에 맞는 정부지원사업을 찾을 수 없습니다."

            header = f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n[총 {len(docs)}건 검색됨]\n\n"
            return header + "\n\n".join(docs)

        except Exception as e:
            return f"정부지원사업 검색 오류: {e}"
