"""
data_pipeline.py
수집된 데이터를 Cosmos DB에 적재하고 AI Search 인덱스를 재구축하는 모듈

Azure Functions에서 호출됨 — 로컬 파일 I/O 없이 메모리에서 직접 처리
"""

import os
import time
import uuid
import logging
from azure.cosmos import CosmosClient, PartitionKey
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticSearch,
    SemanticPrioritizedFields, SemanticField,
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI


# ── 지역 추출 ─────────────────────────────────────────

REGION_KEYWORDS = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
    "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
    "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남",
    "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남",
    "제주": "제주",
}


def _extract_region(org_name: str, program_name: str, target: str) -> str:
    text = f"{org_name} {program_name} {target}"
    for kw, region in REGION_KEYWORDS.items():
        if kw in text:
            return region
    return "전국"


def _build_embedding_text(row: dict, region: str) -> str:
    parts = []
    if region:
        parts.append(f"[지역: {region}]")
    if row.get("field"):
        parts.append(f"[분야: {row['field']}]")
    if row.get("support_type"):
        parts.append(f"[유형: {row['support_type']}]")

    target = row.get("target", "")
    target_tags = []
    for kw in ["소상공인", "자영업", "외식업", "음식점", "카페", "창업", "청년", "중소기업", "식품"]:
        if kw in target:
            target_tags.append(kw)
    if target_tags:
        parts.append(f"[대상: {', '.join(target_tags)}]")

    parts.append(f"사업명: {row.get('program_name', '')}")
    if row.get("summary"):
        parts.append(f"요약: {row['summary']}")
    if row.get("support_content"):
        parts.append(f"지원내용: {row['support_content'][:200]}")
    if target:
        parts.append(f"지원대상: {target[:200]}")

    return " ".join(parts)


# ── 파이프라인 ────────────────────────────────────────

def run_pipeline(data: list[dict]) -> dict:
    """수집된 데이터를 Cosmos DB + AI Search에 적재"""

    cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
    cosmos_key = os.getenv("COSMOS_KEY")
    cosmos_db_name = os.getenv("COSMOS_DATABASE_NAME", "sohobidb")
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "gov-programs-index")
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY")
    embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    embedding_dims = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMS", "3072"))

    # ── Step 1: Cosmos DB 적재 ──
    logging.info("[Pipeline] Cosmos DB 적재 시작...")
    cosmos = CosmosClient(cosmos_endpoint, cosmos_key)
    db = cosmos.get_database_client(cosmos_db_name)

    # 컨테이너 없으면 생성
    try:
        db.create_container_if_not_exists(
            id="gov_programs",
            partition_key=PartitionKey(path="/field"),
            offer_throughput=400,
        )
    except Exception:
        pass

    container = db.get_container_client("gov_programs")
    cosmos_count = 0

    for row in data:
        region = _extract_region(
            row.get("org_name", ""),
            row.get("program_name", ""),
            row.get("target", ""),
        )
        embedding_text = _build_embedding_text(row, region)

        doc = {
            "id": row.get("service_id") or str(uuid.uuid4()),
            "field": row.get("field", "기타"),
            "program_name": row.get("program_name", ""),
            "summary": row.get("summary", ""),
            "target": row.get("target", ""),
            "criteria": row.get("criteria", ""),
            "support_content": row.get("support_content", ""),
            "apply_method": row.get("apply_method", ""),
            "apply_deadline": row.get("apply_deadline", ""),
            "org_name": row.get("org_name", ""),
            "phone": row.get("phone", ""),
            "url": row.get("url", ""),
            "support_type": row.get("support_type", ""),
            "target_region": region,
            "source": row.get("source_name", "unknown"),
            "embedding_text": embedding_text,
        }
        container.upsert_item(doc)
        cosmos_count += 1

        if cosmos_count % 200 == 0:
            logging.info(f"  Cosmos DB: {cosmos_count}/{len(data)}건...")

    logging.info(f"[Pipeline] Cosmos DB 완료: {cosmos_count}건")

    # ── Step 2: AI Search 인덱스 재구축 ──
    logging.info("[Pipeline] AI Search 인덱싱 시작...")

    openai_client = AzureOpenAI(
        azure_endpoint=openai_endpoint,
        api_key=openai_key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    )
    credential = AzureKeyCredential(search_key)

    # 인덱스 생성/업데이트
    index_client = SearchIndexClient(search_endpoint, credential)
    index = SearchIndex(
        name=index_name,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="program_name", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SearchableField(name="summary", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SearchableField(name="target", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SearchableField(name="support_content", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SearchableField(name="criteria", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SimpleField(name="field", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="support_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="target_region", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="apply_method", type=SearchFieldDataType.String),
            SimpleField(name="apply_deadline", type=SearchFieldDataType.String),
            SimpleField(name="org_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="phone", type=SearchFieldDataType.String),
            SimpleField(name="url", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=embedding_dims,
                vector_search_profile_name="sohobi-vector-profile",
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="sohobi-hnsw")],
            profiles=[VectorSearchProfile(name="sohobi-vector-profile", algorithm_configuration_name="sohobi-hnsw")],
        ),
        semantic_search=SemanticSearch(
            default_configuration_name="sohobi-semantic",
            configurations=[SemanticConfiguration(
                name="sohobi-semantic",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="program_name"),
                    content_fields=[
                        SemanticField(field_name="summary"),
                        SemanticField(field_name="support_content"),
                        SemanticField(field_name="target"),
                    ],
                    keywords_fields=[
                        SemanticField(field_name="field"),
                        SemanticField(field_name="target_region"),
                    ],
                ),
            )],
        ),
    )
    index_client.create_or_update_index(index)
    logging.info(f"  인덱스 준비 완료: {index_name}")

    # Cosmos DB에서 읽어서 임베딩 + 인덱싱
    search_client = SearchClient(search_endpoint, index_name, credential)
    all_docs = list(container.read_all_items())
    search_count = 0
    batch = []

    for doc in all_docs:
        embedding_text = doc.get("embedding_text", doc.get("summary", ""))
        resp = openai_client.embeddings.create(input=embedding_text, model=embedding_model)
        embedding = resp.data[0].embedding

        batch.append({
            "id": doc["id"],
            "program_name": doc.get("program_name", ""),
            "summary": doc.get("summary", ""),
            "target": doc.get("target", ""),
            "support_content": doc.get("support_content", ""),
            "criteria": doc.get("criteria", ""),
            "field": doc.get("field", ""),
            "support_type": doc.get("support_type", ""),
            "target_region": doc.get("target_region", "전국"),
            "apply_method": doc.get("apply_method", ""),
            "apply_deadline": doc.get("apply_deadline", ""),
            "org_name": doc.get("org_name", ""),
            "phone": doc.get("phone", ""),
            "url": doc.get("url", ""),
            "source": doc.get("source", ""),
            "embedding": embedding,
        })

        if len(batch) >= 100:
            search_client.upload_documents(batch)
            search_count += len(batch)
            logging.info(f"  AI Search: {search_count}/{len(all_docs)}건...")
            batch = []
            time.sleep(0.5)

    if batch:
        search_client.upload_documents(batch)
        search_count += len(batch)

    logging.info(f"[Pipeline] AI Search 완료: {search_count}건")

    return {
        "cosmos_count": cosmos_count,
        "search_count": search_count,
    }
