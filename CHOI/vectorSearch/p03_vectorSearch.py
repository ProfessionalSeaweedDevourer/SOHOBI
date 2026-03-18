import os
from typing import List, Dict, Any
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

def perform_vector_search(query_text: str, top_k: int = 3):
    """
    사용자의 질문을 벡터로 변환하여 Azure AI Search에서 검색합니다.
    이미지에서 확인된 'fullText_vector' 필드 및 법령 상세 필드 구조를 반영합니다.
    """
    print("질문 분석 중: '%s'" % query_text)
    
    # 1. 질문을 벡터(Embedding)로 변환
    embedding_response = ai_client.embeddings.create(
        input=query_text.replace("\n", " "),
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    )
    query_vector = embedding_response.data[0].embedding

    # 2. 벡터 쿼리 객체 생성
    # 이미지에서 확인된 벡터 필드명 'fullText_vector'를 사용합니다.
    vector_query = VectorizedQuery(
        vector=query_vector, 
        k_nearest_neighbors=top_k, 
        fields="fullText_vector"
    )

    # 3. 검색 실행
    # 이미지에 정의된 모든 필드(lawName, mst, articleNo 등)를 select에 포함합니다.
    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        select=[
            "id", "lawName", "mst", "articleNo", 
            "chapterTitle", "content", "fullText", 
            "source", "lawType"
        ]
    )

    print("--- 검색 결과 (상위 %d건) ---" % top_k)
    search_results = []
    
    for result in results:
        score = result.get("@search.score", 0.0)
        law_name = result.get('lawName', '법령명 없음')
        article_no = result.get('articleNo', '조항 미상')
        
        # 로그 출력: [법령명] 제N조 (유사도 점수)
        print("[%s] %s (유사도 점수: %.4f)" % (law_name, article_no, score))
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