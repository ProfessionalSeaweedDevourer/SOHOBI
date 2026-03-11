# Vector Search

Azure AI Search + Azure OpenAI Embedding을 활용한 벡터 검색 실습 코드입니다.

## 파일 구성

| 파일 | 설명 |
|------|------|
| `p02_vectorSearchUp_Del.py` | 문서 벡터화 후 AI Search 인덱스에 업로드 / 삭제 |
| `p03_vectorSearch.py` | 사용자 질문을 임베딩으로 변환하여 유사 문서 검색 |
| `p04_vectorSearchSK.py` | Semantic Kernel 플러그인으로 벡터 검색 연동 |

## 사용 기술

- Azure AI Search (Vector Index)
- Azure OpenAI Embeddings (`text-embedding-3-small`)
- Semantic Kernel (`FunctionChoiceBehavior.Auto`)

## 실행 순서

1. `p02` — 문서 업로드 (인덱스에 벡터 데이터 적재)
2. `p03` — 벡터 검색 단독 테스트
3. `p04` — SK 에이전트와 연동하여 자연어 질의응답
