import os
import json
import time
from typing import List, Dict, Any
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# --- 환경 변수 설정 ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_EMBEDDING_API_VERSION")

# --- 클라이언트 초기화 ---
openai_client = AzureOpenAI(
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
    """텍스트를 벡터로 변환 (text-embedding-3-small)"""
    if not text:
        return None
    # 줄바꿈 제거 등 전처리
    clean_text = text.replace("\n", " ").strip()
    if not clean_text:
        return None
        
    try:
        return openai_client.embeddings.create(
            input=[clean_text], 
            model=AZURE_EMBEDDING_DEPLOYMENT
        ).data[0].embedding
    except Exception as e:
        print(f"임베딩 생성 오류: {e}")
        return None

def upload_law_data(json_file_path: str):
    """JSON 파일을 읽어 Azure AI Search의 모든 필드 구조에 맞춰 업로드"""
    if not os.path.exists(json_file_path):
        print(f"파일을 찾을 수 없습니다: {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"총 {len(data)}개의 데이터를 인덱스 구조에 맞춰 업로드 시작합니다...")
    
    batch = []
    for i, item in enumerate(data):
        try:
            # 벡터 생성을 위한 기준 텍스트 (fullText 우선, 없으면 content)
            text_for_vector = item.get("fullText") or item.get("content") or ""
            
            # 이미지에서 확인된 모든 필드 매핑 (누락 금지)
            doc = {
                "id": str(item.get("id", i)),
                "lawName": item.get("lawName", ""),
                "mst": item.get("mst", ""),
                "articleNo": item.get("articleNo", ""),
                "chapterTitle": item.get("chapterTitle", ""),
                "content": item.get("content", ""),
                "fullText": item.get("fullText", ""),
                "source": item.get("source", ""),
                "lawType": item.get("lawType", ""),
                # 벡터 필드명: fullText_vector
                "fullText_vector": get_embedding(text_for_vector) if text_for_vector else None
            }
            
            batch.append(doc)

            # 10개 단위 배치 업로드 (안정성 확보)
            if len(batch) >= 10:
                search_client.upload_documents(documents=batch)
                print(f"[{i+1}/{len(data)}] 배치 업로드 성공 (ID: {doc['id']})")
                batch = []
                time.sleep(0.1) 

        except Exception as e:
            print(f"데이터 처리 중 오류 발생 ({i}번째 항목): {e}")
            continue

    if batch:
        search_client.upload_documents(documents=batch)
        print("최종 남은 데이터까지 모두 업로드 완료되었습니다.")

if __name__ == "__main__":
    # --- 파일 경로 설정 (요청하신 기준) ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "refined_law_data.json")
    
    # 실행
    upload_law_data(input_file)