# 2026-04-20 — 법무 RAG 무기능 상태 발견 + gov_support 로컬 환경 동기화

## 요약

`backend/plugins/gov_support_plugin.py` 가 사용하는 AI Search 가 rg-ejp 외부 리소스인지 확인하는 질문에서 출발하여, Azure Container App 실측을 통해 두 건의 독립적인 발견을 하였다.

1. **gov_support RAG 는 정상 동작 중이나 centralus 소재 외부 구독 리소스(`sohobi-search`, `sohobi-openai`)를 사용한다.** 로컬 `.env` 에는 `GOV_*` 전용 변수가 없어 `choiasearchhh` 로 폴백되는 상태였음 → 프로덕션 값과 동기화 완료.
2. **법무 RAG 는 현 프로덕션 배포 전 기간에 걸쳐 한 번도 정상 작동한 적이 없는 것으로 보인다.** `choiasearchhh.search.windows.net` 은 DNS NXDOMAIN 상태이며, Container App 의 `azure-search-endpoint` / `azure-search-key` 시크릿은 치환되지 않은 literal placeholder (`<AZURE_SEARCH_ENDPOINT>`, `<AZURE_SEARCH_KEY>`) 가 들어 있다. 쿼리 로그 분석 결과 로그 보존 전 구간(2026-03-12 ~ 04-20, 79건)에서 RAG 성공 신호 0건, 실패 자백 1건 확인.

## 브랜치 및 커밋 상태

- 현재 브랜치: `docs/park-defender-evaluation`
- 이번 세션에서 새로 생성한 커밋: 없음 (조사·진단만 수행)
- 수정 파일:

  | 파일 | 변경 내용 | 상태 |
  |---|---|---|
  | `backend/.env` | `GOV_SEARCH_ENDPOINT/API_KEY/INDEX_NAME`, `GOV_OPENAI_ENDPOINT/API_KEY/API_VERSION`, `GOV_EMBEDDING_DEPLOYMENT` 7개 추가. legal-index 섹션에 NXDOMAIN 경고 주석 삽입 | gitignored (커밋 대상 아님) |

- 새로 생성한 문서: 본 handoff

## 실측 데이터

### Azure Container App (`sohobi-backend` / `rg-ejp-9638`) 환경변수 실측

| 변수 | 값 | 유효성 |
|---|---|---|
| `GOV_SEARCH_ENDPOINT` | `https://sohobi-search.search.windows.net` | **정상 (centralus 외부 구독)** |
| `GOV_SEARCH_API_KEY` | secret:`gov-search-api-key` (52자 실키) | **정상** |
| `GOV_SEARCH_INDEX_NAME` | `gov-programs-index` | **정상** |
| `GOV_OPENAI_ENDPOINT` | `https://sohobi-openai.openai.azure.com/` | **정상 (외부 구독)** |
| `GOV_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` (3072d) | **정상** |
| `AZURE_SEARCH_ENDPOINT` | secret 값이 literal 문자열 `<AZURE_SEARCH_ENDPOINT>` | **무효 (placeholder)** |
| `AZURE_SEARCH_KEY` | secret 값이 literal 문자열 `<AZURE_SEARCH_KEY>` | **무효 (placeholder)** |
| `AZURE_SEARCH_INDEX` | `legal-index` | — (endpoint 무효로 무의미) |

### DNS / Network 실측

- `choiasearchhh.search.windows.net`: **NXDOMAIN** (168.126.63.1 / 8.8.8.8 / 1.1.1.1 3곳 모두)
- `sohobi-search.search.windows.net`: 정상 해석, centralus 리전 (`azsiesm.centralus.cloudapp.azure.com`)
- `sohobi-openai.openai.azure.com`: 정상 해석, eastus 계열 APIM
- Korea → centralus Search RTT: 680~1400ms/req (3샘플)

### 쿼리 로그 분석 결과 (2026-03-12 ~ 2026-04-20, `/api/v1/logs?type=queries&limit=10000`)

| 구분 | 건수 |
|---|---:|
| 전체 쿼리 | 1,112 |
| `domain=legal` | 79 |
| RAG 성공 신호 (`①②③` 원문 번호 또는 `[법령명 > 장 > 절]` 헤더) | **0** |
| 명시적 실패 자백 (`"법령 검색 도구에서 결과를 가져오지 못"`) | 1 (2026-04-06T18:54) |
| 나머지 (LLM 지식 기반으로 추정) | 78 |

### 정황 타임라인 추정

| 시점 | 이벤트 | 근거 |
|---|---|---|
| ~2026-03 이전 | CHOI 개인 구독에 `choiasearchhh` 및 `legal-index` 구축 | 커밋 `22ad5e9` |
| 2026-03-12 | 쿼리 로그 보존 시작 시점 | `/api/v1/logs` oldest |
| 2026-03-23 07:29 | 현 `sohobi-backend` Container App 생성 (`eric.park@miee.dev`) | systemData.createdAt |
| ??? | CHOI 측에서 `choiasearchhh` Search 리소스 삭제 | DNS NXDOMAIN |
| 2026-04-03 | 최초 남아있는 Container App 리비전 (`0000084`) | revision list |
| 2026-04-03 | `backend/.env.example` 실 API 키 제거 → placeholder 치환 | 커밋 `f2a620b` |
| 2026-04-19 03:12 | 현재 active 리비전 (`0000183`) 배포 | systemData.lastModifiedAt |
| 2026-04-20 04:02 | 가장 최근 legal 쿼리 — LLM 생성 답변 | request_id `9390cc7b` |

## 미완료 / 결정 필요 사항

1. **사용자 노출 문제 대응 결정 필요** — 법무 에이전트가 grade A 로 "법적 조언 아님" 고지만 붙인 LLM hallucination 을 답변하고 있음. 옵션: (a) 프런트 "법령 DB 점검 중" 배너, (b) `legal` 도메인 일시 비활성화, (c) 그냥 두고 조용히 수리
2. **CHOI 연락 필요** — `choiasearchhh` 삭제 시점·경위, `legal-index` 원본 데이터 (lawName / articleNo / fullText 스키마) 또는 임베딩 재구축용 소스 csv/json 확보 가능 여부
3. **Blob 아카이브 탐색 미실행** — `sohobi9638logs` 에 3-12 이전 쿼리 로그가 있을 수 있음. 있으면 정상 RAG 샘플 시점 식별 가능
4. **Korea Central 이관 계획 수립 미착수** — 사용자 요청사항. `sohobi-search-kr` (Basic/S1) 신규 프로비저닝 + koreacentral 에 `text-embedding-3-large` 쿼터 확인 + 데이터 재인덱싱. `legal-index` 도 동일 과정에 묶어 일괄 재구축 가능
5. **`legal_search_plugin.py` `_available` 가드 강화 미실시** — placeholder 문자열(`<…>`) 감지 로직 없음. 검색 실패 시 에이전트가 hallucination fallback 하는 현 동작을 "법령 DB 미가용" 명시 응답으로 바꿀지 결정 필요

## 다음 세션 인수 (3-5줄)

1. 가장 먼저 **사용자 노출 문제 대응 결정**을 받고 그에 따라 프런트 배너 or legal 도메인 비활성화 수행
2. `sohobi9638logs` Blob 아카이브 조회 (`az storage blob list --account-name sohobi9638logs --container-name <logs>`) — 3-12 이전 로그가 있으면 정상 RAG 마지막 날짜 특정
3. CHOI에게 `choiasearchhh` 원본 데이터 확보 여부 질의 → 확보 가능: 복구 중심 재구축, 불가능: 국가법령정보센터 OpenAPI 기반 신규 구축
4. Korea Central 이관은 `legal-index` 재구축과 함께 일괄 `rg-ejp-9638` 로 옮기는 플랜으로 묶어 `docs/plans/2026-04-20-ai-search-koreacentral-consolidation.md` 작성

---

<!-- CLAUDE_HANDOFF_START
branch: docs/park-defender-evaluation
pr: none
prev: 2026-04-19-pr315-oauth-cookie-log-hardening-handoff.md

[unresolved]
- HIGH legal_search_plugin.py 프로덕션 무기능. Container App 시크릿이 literal `<AZURE_SEARCH_ENDPOINT>` placeholder, choiasearchhh NXDOMAIN. 에이전트는 LLM hallucination 으로 grade A 응답 중 — 사용자 노출 대응 결정 필요
- HIGH choiasearchhh 삭제 시점·경위 불명. 외부 구독 소유라 본 계정 Activity Log 로 추적 불가 — CHOI 문의 필수
- MED legal-index 원본 데이터 확보 여부 미확인 — lawName/articleNo/fullText 스키마. 확보 가능성에 따라 재구축 전략 갈림
- MED sohobi9638logs Blob 아카이브 미탐색. 2026-03-12 이전 쿼리 로그 존재 시 정상 RAG 시점 특정 가능
- MED Korea Central 통합 이관 계획 미수립. gov-programs-index + legal-index 재구축 일괄 진행이 비용·운영 효율 높음. text-embedding-3-large koreacentral 쿼터 확인 필요
- LOW legal_search_plugin._available 체크가 placeholder 문자열을 유효값으로 오인 (bool of non-empty str). 가드 강화 필요하나 근본 수리 전 미봉책 성격

[decisions]
- 로컬 .env 는 Azure Container App env 와 동기화 정책 채택 — GOV_* 7개 추가, choiasearchhh 섹션은 NXDOMAIN 경고 주석으로 보존
- gov_support RAG 정상 작동 경로: rg-ejp-9638 외부 sohobi-search(centralus)/sohobi-openai(eastus) 사용. 로컬 .env 의 AZURE_SEARCH_* 폴백은 사용 안 됨
- legal RAG 무기능 원인은 "choiasearchhh 삭제 + Container App 시크릿 placeholder 주입" 복합. 단일 원인 아님
- 로그 retention 기본은 limit=1000 (API 기본값). 전체 retention 확인 시 limit=5000 이상 명시. docs/guides/backend-logs.md 에 미기재

[next]
1. 사용자 결정: 법무 에이전트 사용자 노출 문제 대응 (배너 / 비활성화 / 조용히 수리)
2. sohobi9638logs Blob 아카이브 탐색 → 2026-03-12 이전 정상 RAG 로그 샘플 확보 시도
3. CHOI 연락 — choiasearchhh 삭제 시점 + legal-index 원본 데이터
4. text-embedding-3-large koreacentral 쿼터 확인 (Azure Portal)
5. docs/plans/2026-04-20-ai-search-koreacentral-consolidation.md 작성 (gov + legal 일괄 이관 플랜)
6. legal_search_plugin._available placeholder 감지 가드 추가 (단기 미봉책, 근본 수리와 별도)
7. (carried) sohobi.security stderr client_ip 포맷 Azure Log Stream 에서 1회 육안 확인 — 이벤트 발생 시
8. (carried) App Insights 도입 재평가 · 튜닝 가이드 실사용 피드백 — 이벤트 시점 대응
9. (carried) docs/plans/2026-04-17-backend-load-*.json 6건 담당 세션 확인

[traps]
- 로컬 .env 에 추가된 GOV_SEARCH_API_KEY / GOV_OPENAI_API_KEY 는 실 프로덕션 시크릿 — 커밋·공유 절대 금지. backend/.env 는 gitignored 이나 다른 디렉토리·pastebin 복사 주의
- `/api/v1/logs` 는 기본 limit=1000. 조사 시 limit=5000 이상 지정 필요
- legal_search_plugin._available 이 placeholder 문자열을 truthy 로 판정 — SearchClient init 은 성공, 실제 search() 호출 시 실패. 에이전트는 에러 문자열을 무시하고 LLM 지식으로 fallback → 사용자에게 조용히 hallucination 전달됨
- choiasearchhh 는 외부 구독 리소스라 본 계정(ME-M365EDU102388-joowonjeong-1) 에서 삭제 이벤트 / Activity Log 추적 불가
- Korea Central 이관 시 임베딩 모델 버전 동일 확인 필수. text-embedding-3-large v1 로 구축된 벡터는 동일 v1 재사용 시에만 호환
- gov-programs-index 는 3072d (text-embedding-3-large) 전용. legal-index 재구축 시 같은 AI Search 인스턴스에 두더라도 인덱스별 차원 분리 유지
CLAUDE_HANDOFF_END -->
