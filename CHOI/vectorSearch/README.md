# Vector Search — 법률 RAG 시스템

Azure AI Search + Azure OpenAI Embedding을 활용한 법률 벡터 검색 시스템입니다.
창업 관련 법령(식품위생법, 소득세법, 건축법 등 20여 개)을 조항 단위로 전처리하여 벡터 인덱스에 적재하고,
자연어 질의에 대해 관련 법령 조항을 검색·응답합니다.

## 파일 구성

| 파일 | 설명 |
|------|------|
| `lawIDExtractor.py` | 법령 API에서 법령 MST 코드 조회 |
| `lawDataExtractor.py` | MST 코드 기반으로 법령 원문 추출 (law.go.kr API) |
| `lawDataPreprocessing.py` | 추출된 법령 데이터를 조항 단위로 청킹·전처리 |
| `createOrUpdateIndex.py` | Azure AI Search 벡터 인덱스 생성/업데이트 (HNSW + 시맨틱 구성) |
| `p02_vectorSearchUp&Del.py` | 전처리된 문서를 임베딩 후 인덱스에 업로드 / 전체 삭제 |
| `p03_vectorSearch.py` | 사용자 질문을 임베딩하여 유사 법령 조항 검색 (쿼리 캐싱 포함) |
| `p04_vectorSearchSK.py` | Semantic Kernel 플러그인으로 벡터 검색 연동 (에이전트 질의응답) |
| `vectorSearchUpJson.py` | JSON 파일 기반 벡터 업로드 유틸리티 |

### 데이터 파일

| 파일 | 설명 |
|------|------|
| `법령id.txt` | 법령 MST 코드 목록 |
| `refined_law_data.json` | 추출된 법령 원문 데이터 |
| `law_data_for_embedding.json` | 전처리 완료된 임베딩용 데이터 |

## 수록 법령

식품위생법(+시행령), 상가건물 임대차보호법, 근로기준법(+시행령), 최저임금법,
부가가치세법(+시행령), 소방시설법(+시행령), 소득세법(+시행령), 중소기업창업 지원법(+시행령),
건축법(+시행령), 소상공인 보호 및 지원에 관한 법률, 국민건강증진법, 주세법, 폐기물관리법

## 사용 기술

- Azure AI Search — HNSW 벡터 인덱스 (efConstruction=200, efSearch=100) + 시맨틱 검색
- Azure OpenAI Embeddings (`text-embedding-3-large`, 3072차원)
- Semantic Kernel (`FunctionChoiceBehavior.Auto`)
- 쿼리 임베딩 LRU 캐싱 (동일 질문 반복 시 API 호출 절감)

## 실행 순서

```
1. lawIDExtractor.py      — 법령 MST 코드 조회
2. lawDataExtractor.py    — 법령 원문 추출 → refined_law_data.json
3. lawDataPreprocessing.py — 조항 단위 청킹 → law_data_for_embedding.json
4. createOrUpdateIndex.py  — 인덱스 생성 (최초 1회 또는 스키마 변경 시)
5. p02_vectorSearchUp&Del.py — 임베딩 + 인덱스 업로드
6. p03_vectorSearch.py     — 벡터 검색 단독 테스트
7. p04_vectorSearchSK.py   — SK 에이전트 연동 질의응답
```

## 환경 설정

`.env` 파일에 아래 값을 설정합니다.

```
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
```

## 요구사항

Python 3.12 기준. `pip install -r requirements.txt`
