"""
정부지원사업 & 소상공인 금융지원 통합 검색 플러그인 (RAG)
- Azure AI Search 인덱스: gov-programs-index
- 데이터: 정부24 공공서비스 API (정부지원사업 + 금융지원 + 고용지원 + 교육/컨설팅)
- 검색: 하이브리드 (BM25 키워드 + 벡터) + 시맨틱 랭커
- 임베딩: text-embedding-3-large (3072차원)
"""

from semantic_kernel.functions import kernel_function
from typing import Annotated
import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../sohobi-azure/.env"))

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY") or os.getenv("AZURE_SEARCH_KEY", "")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME", "gov-programs-index")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
)

REGION_MAP = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
    "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
    "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남",
    "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남",
    "제주": "제주",
}


class GovSupportPlugin:
    """정부지원사업 및 소상공인 금융지원 통합 검색 플러그인"""

    def __init__(self):
        self._available = bool(SEARCH_API_KEY and SEARCH_ENDPOINT and OPENAI_ENDPOINT and OPENAI_API_KEY)
        if self._available:
            self._ai_client = AzureOpenAI(
                azure_endpoint=OPENAI_ENDPOINT,
                api_key=OPENAI_API_KEY,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
            )
            self._search_client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX,
                credential=AzureKeyCredential(SEARCH_API_KEY)
            )

    def _get_embedding(self, text: str) -> list[float]:
        response = self._ai_client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT)
        return response.data[0].embedding

    @staticmethod
    def _extract_region(text: str) -> str:
        for keyword, region in REGION_MAP.items():
            if keyword in text:
                return region
        return ""

    @kernel_function(
        name="search_gov_programs",
        description=(
            "소상공인/F&B 창업자를 위한 정부지원사업, 보조금, 창업패키지, "
            "소상공인 정책자금(대출/융자), 신용보증, 고용지원, 교육/컨설팅 등 "
            "정부 및 공공기관의 지원 정보를 통합 검색합니다."
        ),
    )
    def search_gov_programs(
        self,
        query: Annotated[str, "검색 질문 (예: '서울 카페 창업 지원사업', '소상공인 대출', '긴급경영자금')"],
        top_k: int = 15,
        region: Annotated[str, "지역 필터 (예: 서울, 경기). 없으면 쿼리에서 자동 추출"] = "",
    ) -> str:
        if not self._available:
            return "검색 서비스가 설정되지 않았습니다. (AZURE_SEARCH_API_KEY, AZURE_SEARCH_ENDPOINT 확인)"

        try:
            vector = self._get_embedding(query)
            vector_query = VectorizedQuery(
                vector=vector,
                k_nearest_neighbors=20,
                fields="embedding"
            )

            if not region:
                region = self._extract_region(query)

            filter_str = None
            if region:
                filter_str = f"(target_region eq '{region}' or target_region eq '전국')"

            results = self._search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_str,
                query_type="semantic",
                semantic_configuration_name="sohobi-semantic",
                select=[
                    "program_name", "field", "summary", "target",
                    "support_content", "criteria", "apply_deadline",
                    "apply_method", "org_name", "phone", "url",
                    "support_type", "target_region"
                ],
                top=top_k
            )

            programs = []
            for i, r in enumerate(results, 1):
                programs.append(
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

            if not programs:
                return f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n조건에 맞는 지원사업을 찾을 수 없습니다."

            header = f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n[총 {len(programs)}건 검색됨]\n\n"
            return header + "\n\n".join(programs)

        except Exception as e:
            return f"검색 오류: {e}"
