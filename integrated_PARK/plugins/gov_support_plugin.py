"""
정부지원사업 & 소상공인 금융지원 맞춤 추천 플러그인 (RAG)
- Azure AI Search 인덱스: gov-programs-index
- 데이터: 5,600건+ (정부24 + 창업진흥원 4종 + 중소벤처24 + 기업마당 + 큐레이션)
- 검색: 하이브리드 (BM25 키워드 + 벡터) + 시맨틱 랭커
- 임베딩: text-embedding-3-large (3072차원)
- 핵심: 단순 검색이 아닌 사용자 상황 기반 다중 카테고리 맞춤 추천
- 행정 에이전트(AdminAgent)에서 사용
"""

import logging
import os
from collections.abc import Mapping
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI
from semantic_kernel.functions import kernel_function

import re

load_dotenv()

logger = logging.getLogger(__name__)

_AMT_RE = re.compile(r'(\d[\d,]*)\s*(만원|천만원|백만원|억원|억|만)')
_AMT_UNIT = {"만원": 10000, "만": 10000, "천만원": 10000000, "백만원": 1000000, "억원": 100000000, "억": 100000000}


def _parse_amount(text: str) -> int:
    if not text or text == "미정":
        return 0
    m = _AMT_RE.search(text)
    if not m:
        return 0
    return int(int(m.group(1).replace(",", "")) * _AMT_UNIT.get(m.group(2), 1))

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
        "query_template": "{업종} {지역} {창업단계} 소상공인 창업 지원사업 보조금 사업화 패키지",
        "trigger_keywords": ["보조금", "지원금", "패키지", "창업지원", "지원사업", "창업"],
    },
    {
        "name": "대출/융자",
        "query_template": "{업종} 소상공인 정책자금 대출 융자 {자금용도} 경영안정자금",
        "trigger_keywords": ["대출", "융자", "정책자금", "자금", "운전자금", "시설자금", "인테리어"],
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
        "query_template": "{업종} 외식업 음식점 카페 소상공인 {창업단계} 지원사업 {지역}",
        "trigger_keywords": ["위생", "HACCP", "배달", "공유주방", "외식", "식품", "음식점", "카페", "베이커리", "제과"],
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

    # reranker score 임계값 — 0~4 범위에서 1.2 미만은 부적합으로 판단
    RERANKER_THRESHOLD = 1.2

    def _search_one(
        self,
        query: str,
        region: str,
        top_k: int = 5,
        apply_threshold: bool = True,
        startup_stage: str = "",
        support_type_filter: str = "",
        min_amount: int = 0,
        exclude_industries: list[str] | None = None,
    ) -> list[dict]:
        """단일 쿼리 하이브리드+시맨틱 검색. apply_threshold=True이면 reranker score 필터링 후 상위 top_k 반환."""
        resp = self._ai_client.embeddings.create(
            input=query, model=self._embedding_deployment
        )
        vector = resp.data[0].embedding
        vector_query = VectorizedQuery(
            vector=vector, k_nearest_neighbors=top_k * 4, fields="embedding"
        )

        filters = []
        if region:
            filters.append(f"(target_region eq '{region}' or target_region eq '전국')")

        if startup_stage:
            stage_map = {
                "예비창업": "예비창업", "예비": "예비창업",
                "초기창업": "초기창업", "초기": "초기창업",
                "운영중": "운영중", "운영": "운영중",
                "폐업": "폐업재기", "재창업": "폐업재기",
            }
            mapped = stage_map.get(startup_stage, "")
            if mapped:
                filters.append(
                    f"(startup_stages/any(s: s eq '{mapped}') or startup_stages/any(s: s eq '전체'))"
                )

        if support_type_filter:
            filters.append(f"support_types/any(t: t eq '{support_type_filter}')")

        if min_amount > 0:
            filters.append(f"max_amount ge {min_amount}")

        for ind in (exclude_industries or []):
            filters.append(f"not industries/any(i: i eq '{ind}')")

        filter_str = " and ".join(filters) if filters else None

        results = self._search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_str,
            query_type="semantic",
            semantic_configuration_name="sohobi-semantic",
            query_caption="extractive",
            select=[
                "program_name", "field", "summary", "target",
                "support_content", "criteria", "apply_deadline",
                "apply_method", "org_name", "phone", "url",
                "support_type", "target_region",
                "startup_stages", "industries", "support_types",
                "max_amount", "quality_score",
            ],
            top=top_k * 3,
        )

        scored = []
        for r in results:
            if not isinstance(r, Mapping):
                logger.warning("gov_support_plugin: 예상치 못한 결과 타입 %s — 건너뜀", type(r))
                continue
            reranker_score = r.get("@search.reranker_score") or 0.0
            if not apply_threshold or reranker_score >= self.RERANKER_THRESHOLD:
                d = dict(r)
                d["_reranker_score"] = reranker_score
                scored.append(d)

        scored.sort(key=lambda x: x["_reranker_score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _select_categories(business_type: str, funding_purpose: str, additional_info: str, startup_stage: str = "") -> list[dict]:
        """사용자 입력에서 관련 카테고리만 선택. 매칭 없으면 보조금+대출 기본 제공."""
        context = f"{business_type} {funding_purpose} {additional_info}".lower()
        matched = [
            cat for cat in RECOMMEND_CATEGORIES
            if any(kw in context for kw in cat["trigger_keywords"])
        ]
        if not matched:
            matched = [c for c in RECOMMEND_CATEGORIES if c["name"] in ("보조금/창업패키지", "대출/융자")]

        # 예비창업/초기창업이면 보조금/창업패키지 강제 포함
        if startup_stage in ("예비창업", "예비", "초기창업", "초기"):
            subsidy = next((c for c in RECOMMEND_CATEGORIES if c["name"] == "보조금/창업패키지"), None)
            if subsidy and subsidy not in matched:
                matched.insert(0, subsidy)

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
            selected_cats = self._select_categories(business_type, funding_purpose, additional_info, startup_stage)

            flat_results = []
            seen_names = set()

            # 외식업 계열이면 제조업 전용 사업 제외
            _FB_TYPES = ["카페", "음식점", "식당", "베이커리", "제과", "푸드트럭", "주점", "외식"]
            exclude_inds = ["제조업"] if any(t in business_type for t in _FB_TYPES) else []

            for cat in selected_cats:
                query = cat["query_template"].format(**profile)
                results = self._search_one(
                    query, extracted_region, top_k=8,
                    startup_stage=startup_stage if startup_stage != "미정" else "",
                    min_amount=_parse_amount(funding_needed),
                    exclude_industries=exclude_inds,
                )
                for r in results:
                    name = r.get("program_name", "")
                    if name in seen_names:
                        continue
                    seen_names.add(name)
                    flat_results.append(r)

            if not flat_results:
                return f"{profile_summary}\n\n조건에 맞는 지원사업을 찾을 수 없습니다. (검색 결과가 관련성 기준 score {self.RERANKER_THRESHOLD} 을 충족하지 못했습니다)"

            # 창업단계 불일치 후처리 필터
            # (startup_stages가 "전체" 태깅이어서 OData 필터를 통과했지만 실제로는 다른 단계 전용인 경우)
            _STAGE_EXCLUSION = {
                "예비창업": ["폐업재기"],
                "예비": ["폐업재기"],
                "초기창업": ["폐업재기"],
                "초기": ["폐업재기"],
            }
            exclude_stages = _STAGE_EXCLUSION.get(startup_stage, [])
            if exclude_stages:
                flat_results = [
                    r for r in flat_results
                    if not (
                        set(r.get("startup_stages") or []) <= set(exclude_stages)
                        and "전체" not in (r.get("startup_stages") or [])
                    )
                ]

            # reranker score 기준 전역 정렬 후 상위 5개만 선별
            flat_results.sort(key=lambda x: x.get("_reranker_score", 0.0), reverse=True)
            top_results = flat_results[:5]

            output_parts = [profile_summary, f"[상위 {len(top_results)}건 추천]\n"]
            for i, r in enumerate(top_results, 1):
                output_parts.append(
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

            return "\n\n".join(output_parts)

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

            results = self._search_one(query, region, top_k, apply_threshold=False)

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
