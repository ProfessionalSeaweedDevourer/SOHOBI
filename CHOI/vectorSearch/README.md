# Vector Search — 법률 RAG 시스템

Azure AI Search + Azure OpenAI Embedding을 활용한 법률 벡터 검색 시스템입니다.
창업 관련 법령(식품위생법, 소득세법, 건축법 등 20여 개)을 조항 단위로 전처리하여 벡터 인덱스에 적재하고,
자연어 질의에 대해 관련 법령 조항을 검색·응답합니다.

## 파일 구성

| 파일                        | 설명                                                           |
| --------------------------- | -------------------------------------------------------------- |
| `lawIDExtractor.py`         | 법령 API에서 법령 MST 코드 조회                                |
| `lawDataExtractor.py`       | MST 코드 기반으로 법령 원문 추출 (law.go.kr API)               |
| `lawDataPreprocessing.py`   | 추출된 법령 데이터를 조항 단위로 청킹·전처리                   |
| `createOrUpdateIndex.py`    | Azure AI Search 벡터 인덱스 생성/업데이트 (HNSW + 시맨틱 구성) |
| `p02_vectorSearchUp&Del.py` | 전처리된 문서를 임베딩 후 인덱스에 업로드 / 전체 삭제          |
| `p03_vectorSearch.py`       | 하이브리드 검색 엔진 (벡터 + BM25 + 시맨틱 리랭킹)             |
| `p04_vectorSearchSK.py`     | Semantic Kernel 에이전트 연동 질의응답                         |
| `vectorSearchUpJson.py`     | JSON 파일 기반 벡터 업로드 유틸리티                            |

### 데이터 파일

| 파일                          | 설명                          |
| ----------------------------- | ----------------------------- |
| `법령id.txt`                  | 법령 MST 코드 목록            |
| `refined_law_data.json`       | 추출된 법령 원문 데이터       |
| `law_data_for_embedding.json` | 전처리 완료된 임베딩용 데이터 |

## 수록 법령

식품위생법(+시행령), 상가건물 임대차보호법, 근로기준법(+시행령), 최저임금법,
부가가치세법(+시행령), 소방시설법(+시행령·시행규칙), 소득세법(+시행령), 중소기업창업 지원법(+시행령),
건축법(+시행령), 소상공인 보호 및 지원에 관한 법률, 국민건강증진법, 주세법, 폐기물관리법,
공중위생관리법

## 검색 아키텍처

### 하이브리드 3단계 검색 (p03)

```
사용자 질문
    │
    ├─ [1단계] 벡터 유사도 검색 (Azure OpenAI Embedding → HNSW cosine)
    ├─ [2단계] BM25 키워드 매칭 (search_text=query_text)
    └─ [3단계] 시맨틱 리랭킹 (semantic-config → reranker_score 기반 재정렬)
              │
              └─ 임계값 필터링: reranker_score < 1.5 → 제외
```

기존 순수 벡터 검색(`search_text=None`)에서 **하이브리드 검색**으로 전환하여
키워드 정확 매칭과 시맨틱 문맥 이해를 동시에 활용합니다.

### 법령명 자동 필터링

질문에 법령명이 포함되면 해당 법령으로 OData 필터를 자동 적용합니다.

```
"소방시설 설치 기준 알려줘"
  → detect_law_filter() → filter: search.ismatch('소방시설*', 'lawName')
  → 해당 법령 조문만 대상으로 검색
```

### 에이전트 응답 구조 (p04)

Semantic Kernel `FunctionChoiceBehavior.Auto`로 검색 도구를 자동 호출하며,
컨텍스트에 **장/절 계층 정보**를 포함하여 LLM이 법령 구조를 파악할 수 있도록 합니다.

```
[법령명 제N조(조문제목)] 장 > 절 >
조문 본문 내용...
```

### 시스템 프롬프트 답변 규칙

| 규칙        | 내용                                          |
| ----------- | --------------------------------------------- |
| 근거 인용   | `[법령명 제N조(조문제목)]` 형식으로 조항 명시 |
| 추측 금지   | 검색 결과에 없는 내용은 답변하지 않음         |
| 법령별 구분 | 여러 법령이 관련되면 구분하여 안내            |
| 시행령 포함 | 시행령/시행규칙의 세부 기준 함께 언급         |
| 추가 검색   | 불충분 시 키워드 변경 후 최대 1회 재검색      |

### 답변 말미 필수 요소 (Sign-off 루브릭 대응)

| 루브릭         | 필수 요소                                                                      |
| -------------- | ------------------------------------------------------------------------------ |
| G1 면책 조항   | "본 답변은 법적 효력을 갖는 조언이 아니며, 일반적인 법령 정보 안내입니다."     |
| G2 개정 가능성 | "인용된 법령은 개정될 수 있으므로 최신 법령을 확인하시기 바랍니다."            |
| G3 전문가 상담 | "정확한 적용을 위해 관련 전문가(변호사, 행정사 등)와 상담하시기를 권장합니다." |
| G4 법령 인용   | 답변 규칙 1번에 의해 `[법령명 제N조]` 형식 인용 보장                           |

## 사용 기술

| 기술                    | 상세                                                                                                |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| Azure AI Search         | HNSW 벡터 인덱스 (`efConstruction=200`, `efSearch=100`, `m=4`, cosine)                              |
| Azure AI Search         | 시맨틱 검색 (`semantic-config`: title=articleTitle, content=content, keywords=lawName+chapterTitle) |
| Azure OpenAI Embeddings | `text-embedding-3-large` (3072차원)                                                                 |
| Semantic Kernel         | `FunctionChoiceBehavior.Auto` (`auto_invoke_counting_limit=2`)                                      |
| 쿼리 캐싱               | `@lru_cache(maxsize=128)` — 동일 질문 반복 시 임베딩 API 호출 절감                                  |
| 리랭커 필터링           | `@search.reranker_score < 1.5` 미만 결과 자동 제외                                                  |
| 법령 필터               | `detect_law_filter()` — 질문 내 법령명 감지 시 OData 필터 적용                                      |

## 실행 순서

```
1. lawIDExtractor.py        — 법령 MST 코드 조회
2. lawDataExtractor.py      — 법령 원문 추출 → refined_law_data.json
3. lawDataPreprocessing.py   — 조항 단위 청킹 → law_data_for_embedding.json
4. createOrUpdateIndex.py    — 인덱스 생성 (최초 1회 또는 스키마 변경 시)
5. p02_vectorSearchUp&Del.py — 임베딩 + 인덱스 업로드 (전체 삭제 후 재업로드 지원)
6. p03_vectorSearch.py       — 하이브리드 검색 단독 테스트
7. p04_vectorSearchSK.py     — SK 에이전트 연동 질의응답
```

## 환경 설정

`.env` 파일에 아래 값을 설정합니다.

```
# Azure AI Search
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=

# Azure OpenAI (Embedding)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_EMBEDDING_DEPLOYMENT=
AZURE_EMBEDDING_API_VERSION=2024-02-01

# Azure OpenAI (Chat — SK 에이전트용)
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=
```

## 요구사항

Python 3.12 기준. `pip install -r requirements.txt`
