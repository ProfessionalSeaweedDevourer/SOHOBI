"""
정부지원사업 & 소상공인 금융지원 맞춤 추천 플러그인 (RAG)
- Azure AI Search 인덱스: gov-programs-index
- 데이터: 5,600건+ (정부24 + 창업진흥원 4종 + 중소벤처24 + 기업마당 + 큐레이션)
- 검색: 하이브리드 (BM25 키워드 + 벡터) + 시맨틱 랭커
- 임베딩: text-embedding-3-large (3072차원)
- 핵심: 단순 검색이 아닌 사용자 상황 기반 다중 카테고리 맞춤 추천
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

RECOMMEND_CATEGORIES = [
    {
        "name": "보조금/창업패키지",
        "query_template": "{업종} {지역} {창업단계} 창업 지원사업 보조금 패키지",
        "trigger_keywords": ["보조금", "지원금", "패키지", "창업지원", "지원사업", "창업"],
    },
    {
        "name": "대출/융자",
        "query_template": "{업종} 소상공인 정책자금 대출 융자 {자금용도}",
        "trigger_keywords": ["대출", "융자", "정책자금", "자금", "운전자금", "시설자금"],
    },
    {
        "name": "신용보증",
        "query_template": "{업종} 소상공인 신용보증 기술보증 보증서 {지역}",
        "trigger_keywords": ["보증", "신용보증", "기술보증", "보증서", "신보"],
    },
    {
        "name": "고용지원",
        "query_template": "소상공인 고용지원 채용장려금 사회보험 인건비 {직원수}",
        "trigger_keywords": ["고용", "채용", "직원", "인건비", "사회보험", "두루누리", "일자리"],
    },
    {
        "name": "교육/컨설팅",
        "query_template": "{업종} 소상공인 창업 교육 컨설팅 멘토링 {창업단계}",
        "trigger_keywords": ["교육", "컨설팅", "멘토링", "아카데미", "강의", "연수"],
    },
    {
        "name": "외식업/F&B 특화",
        "query_template": "{업종} 외식업 위생 HACCP 배달 공유주방 식품",
        "trigger_keywords": ["위생", "HACCP", "배달", "공유주방", "외식", "식품", "음식점", "카페"],
    },
]


class GovSupportPlugin:
    """사용자 상황 기반 정부지원사업·금융지원 맞춤 추천 플러그인"""

    def __init__(self):
        # GOV_* 전용 자격증명 우선 — 프로덕션 AZURE_* 변수와 충돌 방지
        # (gov-programs-index는 text-embedding-3-large 3072d로 구축됨)
        openai_endpoint = os.getenv("GOV_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        openai_key = os.getenv("GOV_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")
        search_key = (
            os.getenv("GOV_SEARCH_API_KEY")
            or os.getenv("AZURE_SEARCH_API_KEY")
            or os.getenv("AZURE_SEARCH_KEY", "")
        )
        search_endpoint = os.getenv("GOV_SEARCH_ENDPOINT") or os.getenv("AZURE_SEARCH_ENDPOINT", "")
        search_index = (
            os.getenv("GOV_SEARCH_INDEX_NAME")
            or os.getenv("AZURE_SEARCH_INDEX_NAME")
            or os.getenv("AZURE_SEARCH_INDEX", "gov-programs-index")
        )
        self._embedding_deployment = (
            os.getenv("GOV_EMBEDDING_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            or os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        )

        self._available = bool(search_key and search_endpoint and openai_endpoint and openai_key)
        if self._available:
            self._ai_client = AzureOpenAI(
                api_key=openai_key,
                api_version=os.getenv("GOV_OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=openai_endpoint,
            )
            self._search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=search_index,
                credential=AzureKeyCredential(search_key),
            )

    @staticmethod
    def _extract_region(text: str) -> str:
        for keyword, region in REGION_MAP.items():
            if keyword in text:
                return region
        return ""

    def _search_one(self, query: str, region: str, top_k: int = 5) -> list[dict]:
        """단일 쿼리 검색 실행, 결과를 dict 리스트로 반환"""
        resp = self._ai_client.embeddings.create(
            input=query, model=self._embedding_deployment
        )
        vector = resp.data[0].embedding
        vector_query = VectorizedQuery(
            vector=vector, k_nearest_neighbors=20, fields="embedding"
        )
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
            top=top_k,
        )
        return [dict(r) for r in results]

    @staticmethod
    def _select_categories(business_type: str, funding_purpose: str, additional_info: str) -> list[dict]:
        """사용자 입력에서 관련 카테고리만 선택. 매칭 없으면 보조금+대출 기본 제공."""
        context = f"{business_type} {funding_purpose} {additional_info}".lower()
        matched = [
            cat for cat in RECOMMEND_CATEGORIES
            if any(kw in context for kw in cat["trigger_keywords"])
        ]
        if not matched:
            # 기본: 보조금 + 대출 (가장 범용적인 2개)
            matched = [c for c in RECOMMEND_CATEGORIES if c["name"] in ("보조금/창업패키지", "대출/융자")]
        # 최대 3개 카테고리로 제한 (속도 + 품질)
        return matched[:3]

    @kernel_function(
        name="recommend_programs",
        description=(
            "사용자의 업종, 지역, 창업단계, 직원수, 필요자금 등 상황 정보를 받아 "
            "가장 적합한 정부지원사업과 금융상품을 추천합니다. "
            "사용자 질문과 관련된 카테고리만 선택적으로 검색합니다. "
            "반드시 사용자 상황을 먼저 파악한 뒤 이 함수를 호출하세요."
        ),
    )
    def recommend_programs(
        self,
        business_type: Annotated[str, "사용자 업종 (예: 카페, 음식점, 베이커리, 식품제조). 모르면 '미정'"],
        region: Annotated[str, "사용자 지역 (예: 서울, 경기, 부산). 모르면 빈 문자열"],
        startup_stage: Annotated[str, "예비창업/초기창업(3년이내)/운영중/폐업예정/재창업. 모르면 '미정'"],
        employee_count: Annotated[str, "현재 또는 예상 직원수 (예: 0명, 3명, 10명). 모르면 '미정'"] = "미정",
        funding_needed: Annotated[str, "필요한 자금 규모 (예: 3천만원, 1억). 모르면 '미정'"] = "미정",
        funding_purpose: Annotated[str, "자금 용도 (예: 인테리어, 운전자금, 장비구매). 모르면 '미정'"] = "미정",
        additional_info: Annotated[str, "기타 사용자 상황 (예: 폐업 경험 있음, 청년, 여성 등). 없으면 빈 문자열"] = "",
    ) -> str:
        if not self._available:
            return "추천 서비스가 설정되지 않았습니다. (AZURE_SEARCH_API_KEY, AZURE_SEARCH_ENDPOINT 확인)"

        try:
            if not region:
                region = ""
            extracted_region = self._extract_region(region) if region else ""

            profile = {
                "업종": business_type if business_type != "미정" else "소상공인",
                "지역": region or "전국",
                "창업단계": startup_stage if startup_stage != "미정" else "",
                "직원수": employee_count if employee_count != "미정" else "",
                "자금용도": funding_purpose if funding_purpose != "미정" else "운전자금",
            }

            profile_summary = (
                f"[사용자 프로필] 업종: {profile['업종']}, 지역: {profile['지역']}, "
                f"단계: {profile['창업단계'] or '미정'}, 직원: {employee_count}, "
                f"필요자금: {funding_needed}, 용도: {funding_purpose}"
            )
            if additional_info:
                profile_summary += f", 기타: {additional_info}"

            # 관련 카테고리만 선택 (최대 3개)
            selected_cats = self._select_categories(business_type, funding_purpose, additional_info)

            all_results = {}
            seen_names = set()

            for cat in selected_cats:
                query = cat["query_template"].format(**profile)
                results = self._search_one(query, extracted_region, top_k=5)

                cat_results = []
                for r in results:
                    name = r.get("program_name", "")
                    if name in seen_names:
                        continue
                    seen_names.add(name)
                    cat_results.append(r)

                if cat_results:
                    all_results[cat["name"]] = cat_results

            if not all_results:
                return f"{profile_summary}\n\n조건에 맞는 지원사업을 찾을 수 없습니다."

            output_parts = [profile_summary, ""]

            total_count = 0
            for cat_name, results in all_results.items():
                output_parts.append(f"━━━ {cat_name} ━━━")
                for r in results:
                    total_count += 1
                    output_parts.append(
                        f"\n■ {r.get('program_name', '-')}\n"
                        f"  분야: {r.get('field', '-')} | 유형: {r.get('support_type', '-')} | 지역: {r.get('target_region', '-')}\n"
                        f"  대상: {r.get('target', '-')}\n"
                        f"  선정기준: {r.get('criteria', '-')}\n"
                        f"  지원내용: {r.get('support_content', '-')}\n"
                        f"  신청방법: {r.get('apply_method', '-')}\n"
                        f"  신청기한: {r.get('apply_deadline', '-')}\n"
                        f"  기관: {r.get('org_name', '-')} | 문의: {r.get('phone', '-')}\n"
                        f"  링크: {r.get('url', '-')}"
                    )
                output_parts.append("")

            output_parts.insert(1, f"[총 {len(all_results)}개 카테고리에서 {total_count}건 추천]\n")

            return "\n".join(output_parts)

        except Exception as e:
            return f"추천 오류: {e}"

    @kernel_function(
        name="search_gov_programs",
        description=(
            "특정 키워드나 사업명으로 지원사업을 직접 검색합니다. "
            "사용자가 특정 사업에 대해 물어볼 때 사용합니다. "
            "일반적인 추천은 recommend_programs를 사용하세요."
        ),
    )
    def search_gov_programs(
        self,
        query: Annotated[str, "검색 질문 (예: '예비창업패키지 신청방법', '긴급경영자금 금리')"],
        top_k: int = 10,
        region: Annotated[str, "지역 필터 (예: 서울, 경기). 없으면 쿼리에서 자동 추출"] = "",
    ) -> str:
        if not self._available:
            return "검색 서비스가 설정되지 않았습니다."

        try:
            if not region:
                region = self._extract_region(query)

            results = self._search_one(query, region, top_k)

            if not results:
                return f"[검색: '{query}', 지역: {region or '전국'}]\n결과를 찾을 수 없습니다."

            programs = []
            for i, r in enumerate(results, 1):
                programs.append(
                    f"[{i}] {r.get('program_name', '-')}\n"
                    f"  분야: {r.get('field', '-')} | 유형: {r.get('support_type', '-')} | 지역: {r.get('target_region', '-')}\n"
                    f"  대상: {r.get('target', '-')}\n"
                    f"  선정기준: {r.get('criteria', '-')}\n"
                    f"  지원내용: {r.get('support_content', '-')}\n"
                    f"  신청방법: {r.get('apply_method', '-')}\n"
                    f"  신청기한: {r.get('apply_deadline', '-')}\n"
                    f"  기관: {r.get('org_name', '-')} | 문의: {r.get('phone', '-')}\n"
                    f"  링크: {r.get('url', '-')}"
                )

            header = f"[검색: '{query}', 지역: {region or '전국'}] {len(programs)}건\n\n"
            return header + "\n\n".join(programs)

        except Exception as e:
            return f"검색 오류: {e}"
