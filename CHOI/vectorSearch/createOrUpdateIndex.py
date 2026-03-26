import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from dotenv import load_dotenv

# 유지보수 및 상세설정을 위한 인덱스 생성 및 업데이트 파일

# 실행순서
# 1. createOrUpdateIndex.py (인덱스생성)
# 2. lawDataPreprocessing.py (데이터 전처리)
# 3. p02_vectorSearchUp&Del.py (임베딩 + 업로드)

# .env 로드
load_dotenv()

# --- 환경 변수에서 설정 정보 로드 ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "legal-index")

# 임베딩 차원 수 (text-embedding-3-large = 3072, text-embedding-3-small = 1536)
EMBEDDING_DIMENSIONS = int(os.getenv("AZURE_EMBEDDING_DIMENSIONS", "3072"))


def create_legal_index():
    """
    refined_law_data.json 구조에 맞는 Azure AI Search 인덱스를 생성합니다.

    필드 구조:
        id           : 문서 고유 키
        lawName      : 법령명 (필터링/패싯용)
        mst          : 법령 MST 코드
        articleNo    : 조문 번호
        chapterTitle : 장 제목 (필터링/패싯용)
        sectionTitle : 절 제목 (필터링/패싯용)
        articleTitle  : 조문 제목 (검색용)
        content      : 정제된 조문 본문 (전문 검색 대상)
        fullText     : 계층+본문 통합 텍스트 (임베딩 대상)
        content_vector : fullText 임베딩 벡터
        source       : 출처
        docType      : 법령 유형
        chunkIndex   : 분할 순서 (0부터)
        isChunked    : 분할 여부
    """

    # --- 클라이언트 초기화 ---
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    # --- 벡터 검색 설정 ---
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config",
                parameters={
                    "m": 4,
                    "efConstruction": 200,
                    "efSearch": 100,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config"
            )
        ]
    )

    # --- 시맨틱 검색 설정 ---
    semantic_config = SemanticConfiguration(
        name="semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="articleTitle"),
            content_fields=[
                SemanticField(field_name="content")
            ],
            keywords_fields=[
                SemanticField(field_name="lawName"),
                SemanticField(field_name="chapterTitle")
            ]
        )
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    # --- 필드 정의 ---
    fields = [
        # 키 필드
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True
        ),

        # 법령 메타 정보 (필터링/패싯)
        SearchableField(
            name="lawName",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            sortable=True
        ),
        SimpleField(
            name="mst",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="articleNo",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),

        # 계층 구조 (장/절)
        SearchableField(
            name="chapterTitle",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SearchableField(
            name="sectionTitle",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),

        # 조문 제목 (시맨틱 검색 title)
        SearchableField(
            name="articleTitle",
            type=SearchFieldDataType.String,
            filterable=True
        ),

        # 본문 (전문 검색 대상)
        SearchableField(
            name="content",
            type=SearchFieldDataType.String
        ),

        # 임베딩 대상 텍스트 (계층 + 본문 통합)
        SearchableField(
            name="fullText",
            type=SearchFieldDataType.String
        ),

        # 벡터 필드
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="vector-profile"
        ),

        # 부가 정보
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="docType",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SimpleField(
            name="chunkIndex",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="isChunked",
            type=SearchFieldDataType.Boolean,
            filterable=True
        ),
    ]

    # --- 인덱스 생성 ---
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )

    try:
        result = index_client.create_or_update_index(index)
        print("=" * 60)
        print("✅ 인덱스 생성/업데이트 완료")
        print("=" * 60)
        print("  인덱스 이름        : %s" % result.name)
        print("  필드 수            : %s개" % len(result.fields))
        print("  벡터 프로필        : vector-profile (HNSW, cosine)")
        print("  벡터 차원          : %s" % EMBEDDING_DIMENSIONS)
        print("  시맨틱 설정        : semantic-config")
        print("  엔드포인트         : %s" % SEARCH_ENDPOINT)
        print("=" * 60)

        print("\n  필드 목록:")
        for field in result.fields:
            attrs = []
            if getattr(field, 'key', False):
                attrs.append("KEY")
            if getattr(field, 'filterable', False):
                attrs.append("filterable")
            if getattr(field, 'facetable', False):
                attrs.append("facetable")
            if getattr(field, 'sortable', False):
                attrs.append("sortable")
            if getattr(field, 'searchable', False):
                attrs.append("searchable")
            attr_str = ", ".join(attrs) if attrs else ""
            print("    %-18s %-40s %s" % (field.name, str(field.type), attr_str))

    except Exception as e:
        print("❌ 인덱스 생성 실패: %s" % e)


if __name__ == "__main__":
    # 기존 인덱스 삭제 후 재생성
    # index_client = SearchIndexClient(
    #     endpoint=SEARCH_ENDPOINT,
    #     credential=AzureKeyCredential(SEARCH_KEY)
    # )
    # try:
    #     index_client.delete_index(INDEX_NAME)
    #     print("🗑️ 기존 인덱스 '%s' 삭제 완료" % INDEX_NAME)
    # except Exception as e:
    #     print("기존 인덱스 없음 또는 삭제 스킵: %s" % e)

    create_legal_index()