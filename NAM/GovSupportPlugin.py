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
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME", "gov-programs-index")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

REGION_MAP = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
    "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
    "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남",
    "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남",
    "제주": "제주",
}


def get_embedding(text: str) -> list[float]:
    client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_API_KEY,
        api_version="2024-08-01-preview"
    )
    response = client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT)
    return response.data[0].embedding


def extract_region_from_query(query: str) -> str:
    for keyword, region in REGION_MAP.items():
        if keyword in query:
            return region
    return ""


def build_filter(region: str) -> str:
    filters = []
    if region:
        filters.append(f"(target_region eq '{region}' or target_region eq '전국')")
    return " and ".join(filters) if filters else None


class GovSupportPlugin:
    """정부지원사업 RAW 검색 - GPT가 분석/필터링/정리하도록 원본 데이터 반환"""

    @kernel_function(
        name="search_gov_programs",
        description="창업자의 업종, 지역, 창업단계를 입력받아 정부지원사업/혜택을 검색합니다. 결과는 GPT가 분석하여 관련성 높은 것만 사용자에게 안내합니다."
    )
    def search_gov_programs(
        self,
        query: Annotated[str, "검색할 내용. 예: '서울 카페 창업 초기 지원금', '외식업 소상공인 융자'"]
    ) -> str:
        try:
            search_client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX,
                credential=AzureKeyCredential(SEARCH_API_KEY)
            )

            vector = get_embedding(query)
            vector_query = VectorizedQuery(
                vector=vector,
                k_nearest_neighbors=20,
                fields="embedding"
            )

            region = extract_region_from_query(query)
            odata_filter = build_filter(region)

            results = search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=odata_filter,
                query_type="semantic",
                semantic_configuration_name="sohobi-semantic",
                select=[
                    "program_name", "field", "summary", "target",
                    "support_content", "criteria", "apply_deadline",
                    "apply_method", "org_name", "phone", "url",
                    "support_type", "target_region"
                ],
                top=15
            )

            programs = []
            for i, r in enumerate(results, 1):
                programs.append(
                    f"[결과 {i}]\n"
                    f"사업명: {r.get('program_name', '-')}\n"
                    f"분야: {r.get('field', '-')}\n"
                    f"유형: {r.get('support_type', '-')}\n"
                    f"지역: {r.get('target_region', '-')}\n"
                    f"대상: {r.get('target', '-')}\n"
                    f"선정기준: {r.get('criteria', '-')}\n"
                    f"지원내용: {r.get('support_content', '-')}\n"
                    f"신청방법: {r.get('apply_method', '-')}\n"
                    f"신청기한: {r.get('apply_deadline', '-')}\n"
                    f"기관: {r.get('org_name', '-')}\n"
                    f"문의: {r.get('phone', '-')}\n"
                    f"링크: {r.get('url', '-')}"
                )

            if not programs:
                return f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n검색 결과 0건. 조건에 맞는 정부지원사업이 없습니다."

            header = f"[검색조건: 쿼리='{query}', 지역={region or '전국'}]\n[총 {len(programs)}건 검색됨]\n\n"
            return header + "\n\n".join(programs)

        except Exception as e:
            return f"검색 중 오류가 발생했습니다: {str(e)}"
