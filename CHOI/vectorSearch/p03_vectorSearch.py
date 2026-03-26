import os
from typing import List, Dict, Any
from functools import lru_cache
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# --- 환경 변수에서 설정 정보 로드 ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01")

# --- 클라이언트 초기화 ---
ai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_KEY)
)

@lru_cache(maxsize=128)
def get_query_embedding(query_text: str) -> tuple:
    """쿼리 임베딩을 생성하고 캐싱합니다. 동일 질문 재호출 시 API 호출을 건너뜁니다."""
    response = ai_client.embeddings.create(
        input=query_text.replace("\n", " "),
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    )
    return tuple(response.data[0].embedding)


# --- 법령명 자동 감지 → 메타데이터 필터링 ---
LAW_NAMES = [
    "식품위생법", "근로기준법", "상가건물 임대차보호법",
    "최저임금법", "부가가치세법", "소방시설", "공중위생관리법",
    "소득세법", "중소기업창업 지원법", "건축법",
    "소상공인 보호 및 지원에 관한 법률", "국민건강증진법",
    "주세법", "폐기물관리법",
]


def detect_law_filter(query: str) -> str:
    """질문에서 법령명을 감지하여 OData 필터 생성"""
    for name in LAW_NAMES:
        if name in query:
            return "search.ismatch('%s*', 'lawName')" % name
    return None


def perform_vector_search(query_text: str, top_k: int = 5):
    """
    하이브리드 검색: 벡터 유사도 + BM25 키워드 + 시맨틱 리랭킹.
    질문에 법령명이 포함되면 해당 법령으로 필터링합니다.
    """
    print("질문 분석 중: '%s'" % query_text)

    # 1. 질문을 벡터(Embedding)로 변환 (캐싱 적용)
    query_vector = list(get_query_embedding(query_text))

    # 2. 벡터 쿼리 객체 생성 (리랭킹 여유분 확보)
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k * 2,
        fields="content_vector"
    )

    # 3. 법령명 필터 감지
    filter_expr = detect_law_filter(query_text)
    if filter_expr:
        print("법령 필터 적용: %s" % filter_expr)

    # 4. 하이브리드 검색 실행 (벡터 + 키워드 + 시맨틱 리랭킹)
    results = search_client.search(
        search_text=query_text,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="semantic-config",
        top=top_k,
        filter=filter_expr,
        select=[
            "id", "lawName", "mst", "articleNo",
            "chapterTitle", "sectionTitle", "articleTitle",
            "content", "fullText",
            "source", "docType"
        ]
    )

    print("--- 검색 결과 (상위 %d건) ---" % top_k)
    search_results = []

    for result in results:
        score = result.get("@search.score", 0.0)
        reranker_score = result.get("@search.reranker_score", 0.0)
        law_name = result.get('lawName', '법령명 없음')
        article_no = result.get('articleNo', '조항 미상')

        # 시맨틱 리랭커 점수 기준 필터링 (0~4 범위, 1.5 미만 제거)
        if reranker_score and reranker_score < 1.5:
            print("[%s] %s (리랭커: %.2f — 임계값 미달, 제외)" % (law_name, article_no, reranker_score))
            continue

        score_info = "점수: %.4f" % score
        if reranker_score:
            score_info += ", 리랭커: %.2f" % reranker_score
        print("[%s] %s (%s)" % (law_name, article_no, score_info))
        search_results.append(result)

    return search_results

if __name__ == "__main__":
    try:
        # 테스트용 질문
        user_query = input("질문 : ")   # "카페 창업 시 보건증 발급 주기와 검사항목"
        found_docs = perform_vector_search(user_query)
        
        if not found_docs:
            print("관련 문서를 찾지 못했습니다.")
        else:
            print("\n총 %d개의 검색 결과를 가져왔습니다." % len(found_docs))
            
    except Exception as e:
        import traceback
        print("오류 발생: %s" % e)
        traceback.print_exc()