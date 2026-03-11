import os
from typing import List, Dict, Any
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

# --- 설정 정보 (사용자 제공 값 적용) ---
SEARCH_ENDPOINT = "https://choiasearchhh.search.windows.net"
SEARCH_KEY = "5GFdDYE4Bh23nl7ryfuRLqqW7gI9bT32tPyV6uQx3DAzSeD1B2b5"
INDEX_NAME = "legal-index"

AZURE_OPENAI_ENDPOINT = "https://student02-11-1604-resource.cognitiveservices.azure.com"
AZURE_OPENAI_KEY = "BQrdUVZyMVUpWd6Xtyvb7BAixaLikbxZlCzF5Zoj98f2pWYR6tJfJQQJ99CBACHYHv6XJ3w3AAAAACOGSqpw"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
AZURE_API_VERSION = "2024-02-01"

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

def perform_vector_search(query_text: str, top_k: int = 3):
    """
    사용자의 질문을 벡터로 변환하여 Azure AI Search에서 검색합니다.
    """
    print("질문 분석 중: '%s'" % query_text)
    
    # 1. 질문을 벡터(Embedding)로 변환
    embedding_response = ai_client.embeddings.create(
        input=query_text,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    )
    query_vector = embedding_response.data[0].embedding

    # 2. 벡터 쿼리 객체 생성
    vector_query = VectorizedQuery(
        vector=query_vector, 
        k_nearest_neighbors=top_k, 
        fields="content_vector"
    )

    # 3. 검색 실행
    results = search_client.search(
        search_text=None,  # 순수 벡터 검색인 경우 None
        vector_queries=[vector_query],
        select=["id", "title", "content", "category"] # 답변 생성에 필요한 필드만 선택
    )

    print("--- 검색 결과 (상위 %d건) ---" % top_k)
    search_results = []
    for result in results:
        score = result.get("@search.score")
        print("[%s] %s (유사도 점수: %.4f)" % (result['category'], result['title'], score))
        search_results.append(result)
    
    return search_results

if __name__ == "__main__":
    try:
        # 테스트: 실제 사용자가 물어볼 법한 질문
        user_query = "카페 창업하려는데 보건증 검사 항목이 뭐야?"
        
        found_docs = perform_vector_search(user_query)
        
        if not found_docs:
            print("관련 문서를 찾지 못했습니다.")
            
    except Exception as e:
        import traceback
        print("오류 발생: %s" % e)
        traceback.print_exc()