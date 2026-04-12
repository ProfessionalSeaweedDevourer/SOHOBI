# backend/plugins

Semantic Kernel 플러그인 모듈. 각 에이전트가 호출하는 도구(tool) 함수를 제공한다.

---

## 플러그인 목록

| 플러그인 | 사용 에이전트 | 역할 | 외부 의존성 |
|----------|---------------|------|-------------|
| `admin_procedure_plugin.py` | AdminAgent | 법령 검증된 5대 행정 절차 KB (영업신고·위생교육·사업자등록·보건증·소방) | 로컬 JSON (`data/admin_procedures.json`) |
| `gov_support_plugin.py` | AdminAgent | 정부지원사업 하이브리드 검색 RAG (5,600건+) | Azure AI Search (`gov-programs-index`) |
| `finance_simulation_plugin.py` | FinanceAgent | 몬테카를로 10,000회 재무 시뮬레이션 + 히스토그램 차트 생성 | Azure PostgreSQL (매출 데이터) |
| `legal_search_plugin.py` | LegalAgent | 법령 벡터 검색 RAG (하이브리드: BM25 + 벡터 + 시맨틱 리랭킹) | Azure AI Search (법령 인덱스) |
| `food_business_plugin.py` | AdminAgent | 식품영업신고서 PDF 자동 생성 (대화형 정보 수집 후) | 로컬 PDF 오버레이 |

## 공통 패턴

- 모든 플러그인은 `@kernel_function` 데코레이터로 Semantic Kernel에 등록
- 에이전트가 LLM function calling을 통해 자동 호출
- 환경변수는 `backend/.env`에서 로드 (`dotenv`)

## 관련 문서

- 에이전트 상세: [`../agents/README.md`](../agents/README.md)
- 아키텍처 다이어그램: [`../../docs/architecture/`](../../docs/architecture/)
