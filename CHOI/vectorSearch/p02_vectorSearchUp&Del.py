import os
from typing import List, Dict, Any
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# --- 환경 변수에서 설정 정보 로드 ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "legal-index")

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

def get_embedding(text: str):
    """텍스트를 벡터로 변환"""
    text = text.replace("\n", " ")
    return ai_client.embeddings.create(input=[text], model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT).data[0].embedding

def upload_documents(docs: List[Dict[str, Any]]):
    """문서 리스트를 받아 임베딩 생성 후 업로드"""
    enriched_docs = []
    for doc in docs:
        print("임베딩 생성 중: %s" % doc.get('title', doc.get('id')))
        doc["content_vector"] = get_embedding(doc["content"])
        enriched_docs.append(doc)
    
    results = search_client.upload_documents(documents=enriched_docs)
    for result in results:
        status = "성공" if result.succeeded else "실패"
        print("문서 ID %s: %s" % (result.key, status))

def delete_documents_by_id(doc_ids: List[str]):
    """문서 ID 리스트를 받아 삭제"""
    docs_to_delete = [{"id": doc_id} for doc_id in doc_ids]
    results = search_client.delete_documents(documents=docs_to_delete)
    for result in results:
        status = "삭제 성공" if result.succeeded else "삭제 실패"
        print("문서 ID %s: %s" % (result.key, status))

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
    
    print("\n[1] 테스트 데이터 업로드 시작...")
    upload_documents(sample_data)
    
    # --- 2. 삭제 테스트 ---
    print("\n[2] 테스트 데이터 삭제 시작...")
    delete_documents_by_id(["test-delete-001"])