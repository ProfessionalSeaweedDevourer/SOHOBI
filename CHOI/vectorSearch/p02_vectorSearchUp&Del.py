import os
from typing import List, Dict, Any
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

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

def get_embedding(text: str) -> List[float]:
    """텍스트를 벡터로 변환하는 함수"""
    response = ai_client.embeddings.create(
        input=text,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    )
    return response.data[0].embedding

def upload_documents(docs: List[Dict[str, Any]]):
    """데이터를 벡터화하여 AI Search에 업로드"""
    enriched_docs = []
    for doc in docs:
        print(f"임베딩 생성 중: {doc.get('title', doc.get('id'))}")
        doc["content_vector"] = get_embedding(doc["content"])
        enriched_docs.append(doc)
    
    results = search_client.upload_documents(documents=enriched_docs)
    for result in results:
        status = "성공" if result.succeeded else "실패"
        print(f"문서 ID {result.key}: {status}")

def delete_documents_by_id(doc_ids: List[str]):
    """문서 ID 리스트를 받아 인덱스에서 삭제하는 함수"""
    # 삭제할 때는 ID 값만 포함된 딕셔너리 리스트를 전달합니다.
    docs_to_delete = [{"id": doc_id} for doc_id in doc_ids]
    
    results = search_client.delete_documents(documents=docs_to_delete)
    for result in results:
        status = "삭제 성공" if result.succeeded else "삭제 실패"
        print(f"문서 ID {result.key}: {status}")

if __name__ == "__main__":
    # --- 1. 업로드 테스트 ---
    sample_data = [
        {
            "id": "test-delete-001",
            "title": "삭제 테스트 문서",
            "content": "이 문서는 잠시 후 삭제될 예정입니다.",
            "category": "테스트"
        }
    ]
    
    try:
        print(f"--- 업로드 단계 ---")
        upload_documents(sample_data)
        
        # --- 2. 삭제 테스트 ---
        print(f"\n--- 삭제 단계 ---")
        # 삭제하고 싶은 문서의 ID 리스트를 넘깁니다.
        target_ids = ["test-delete-001"]
        delete_documents_by_id(target_ids)
        
        print("\n모든 작업이 완료되었습니다.")
    except Exception as e:
        import traceback
        print(f"오류 발생: {e}")
        traceback.print_exc()