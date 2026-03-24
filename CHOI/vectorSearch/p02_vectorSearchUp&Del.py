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

# --- 환경 변수에서 설정 정보 로드 ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "legal-index")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01")

# 배치 설정
BATCH_SIZE = 50          # 한 번에 업로드할 문서 수
EMBEDDING_DELAY = 0.5    # 임베딩 API 호출 간 대기(초) - rate limit 방지

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


def get_embedding(text):
    """텍스트를 벡터로 변환"""
    text = text.replace("\n", " ")
    return ai_client.embeddings.create(
        input=[text],
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    ).data[0].embedding


def upload_documents(docs):
    """
    refined_law_data.json 형식의 문서 리스트를 받아
    fullText 기반 임베딩 생성 후 업로드합니다.
    """
    total = len(docs)
    success_count = 0
    fail_count = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = docs[batch_start:batch_end]

        print("\n--- 배치 %s/%s (문서 %s~%s) ---" % (
            batch_start // BATCH_SIZE + 1,
            (total + BATCH_SIZE - 1) // BATCH_SIZE,
            batch_start + 1,
            batch_end
        ))

        enriched_batch = []
        for doc in batch:
            doc_label = doc.get("articleTitle") or doc.get("id")
            print("  임베딩 생성 중: %s" % doc_label)

            try:
                # fullText를 임베딩 대상으로 사용
                embedding_text = doc.get("fullText", doc.get("content", ""))
                doc["content_vector"] = get_embedding(embedding_text)
                enriched_batch.append(doc)
                time.sleep(EMBEDDING_DELAY)
            except Exception as e:
                print("  ⚠️  임베딩 실패 [%s]: %s" % (doc.get("id"), e))
                fail_count += 1
                continue

        if enriched_batch:
            try:
                results = search_client.upload_documents(documents=enriched_batch)
                for result in results:
                    if result.succeeded:
                        success_count += 1
                    else:
                        fail_count += 1
                        print("  ❌ 업로드 실패 문서 ID %s" % result.key)
            except Exception as e:
                print("  ❌ 배치 업로드 오류: %s" % e)
                fail_count += len(enriched_batch)

        print("  진행률: %s/%s (성공: %s, 실패: %s)" % (
            batch_end, total, success_count, fail_count
        ))

    print("\n" + "=" * 60)
    print("✅ 업로드 완료")
    print("=" * 60)
    print("  전체 문서 수  : %s개" % total)
    print("  성공          : %s개" % success_count)
    print("  실패          : %s개" % fail_count)
    print("=" * 60)


def delete_documents_by_id(doc_ids):
    """문서 ID 리스트를 받아 삭제"""
    docs_to_delete = [{"id": doc_id} for doc_id in doc_ids]
    results = search_client.delete_documents(documents=docs_to_delete)
    for result in results:
        status = "삭제 성공" if result.succeeded else "삭제 실패"
        print("문서 ID %s: %s" % (result.key, status))


def delete_documents_by_filter(filter_field, filter_value):
    """
    특정 필드 값으로 문서를 검색한 후 일괄 삭제합니다.
    예: delete_documents_by_filter("lawName", "식품위생법")
    """
    from azure.search.documents import SearchClient

    filter_str = "%s eq '%s'" % (filter_field, filter_value)
    print("필터 조건: %s" % filter_str)

    # 삭제 대상 ID 수집
    results = search_client.search(
        search_text="*",
        filter=filter_str,
        select=["id"],
        top=5000
    )

    doc_ids = [r["id"] for r in results]
    if not doc_ids:
        print("삭제 대상 문서가 없습니다.")
        return

    print("삭제 대상: %s개" % len(doc_ids))
    delete_documents_by_id(doc_ids)


def load_refined_data(file_path):
    """전처리된 JSON 파일 로드"""
    if not os.path.exists(file_path):
        print("❌ 파일을 찾을 수 없습니다: %s" % file_path)
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("📂 로드 완료: %s (%s개 문서)" % (file_path, len(data)))
    return data


if __name__ == "__main__":
    # --- 전처리된 데이터 파일 경로 ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(current_dir, "refined_law_data.json")

    # --- 1. 데이터 로드 ---
    print("\n[1] 전처리 데이터 로드...")
    docs = load_refined_data(data_file)
    if not docs:
        exit(1)

    # --- 2. 전체 업로드 ---
    print("\n[2] Azure AI Search 업로드 시작...")
    upload_documents(docs)

    # --- 3. 삭제 예시 (필요 시 주석 해제) ---
    # print("\n[3] 특정 문서 삭제...")
    # delete_documents_by_id(["law_277149_1_1"])

    # print("\n[3] 특정 법령 전체 삭제...")
    # delete_documents_by_filter("lawName", "식품위생법")