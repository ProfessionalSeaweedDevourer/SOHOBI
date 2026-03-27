# SOHOBI 통합 에이전트 (integrated_PARK)

PARK · CHOI · CHANG · NAM 각자의 작업물을 하나의 Semantic Kernel 시스템으로 통합한 폴더입니다.

---

## 아키텍처

```text
사용자 질문 + session_id + founder_context
    │
    ▼
[API Server] ── session_id 발급·복원 / 창업자 프로필 저장
    │            _query_sessions[sid] = { profile, history }
    │
    ▼
[DomainRouter] ── 키워드(1차) / LLM(2차) 분류
    │
    ├─ admin    → [AdminAgent]
    │             ├─ 창업자 프로필 시스템 프롬프트 주입
    │             └─ SeoulCommercialPlugin (CHOI)
    │                서울시 상권 API — 지역·업종별 매출·점포수 자동 조회
    │             └─ GovSupportPlugin
    │                정부지원사업 벡터 검색 RAG (Azure AI Search, gov-programs-index)
    │
    ├─ finance  → [FinanceAgent]  ← 4단계 명시적 파이프라인
    │             ├─ 창업자 프로필 → 파라미터 추출 + 설명 생성 단계 주입
    │             └─ FinanceSimulationPlugin (CHANG)
    │                1) 자연어 → 시뮬레이션 파라미터 JSON 추출
    │                2) 몬테카를로 10,000회 시뮬레이션
    │                   (평균·표준편차·P5·P95·손실확률 5개 통계 반환)
    │                3) 가정 조건 + 통계 → LLM 설명 draft 생성
    │                4) 초기 투자 언급 시 투자 회수 시나리오 병합
    │
    ├─ legal    → [LegalAgent]
    │             ├─ 창업자 프로필 시스템 프롬프트 주입
    │             └─ LegalSearchPlugin (CHOI)
    │                Azure AI Search 법령 RAG 자동 조회
    │
    └─ location → [LocationAgent]  ← DB 조회 + LLM 분석 파이프라인 (CHOI)
                  ├─ 자연어 → {mode, locations, business_type, quarter} 파라미터 추출
                  └─ CommercialRepository (Oracle 외부 서버)
                     1) 단일 지역: 월매출·점포수·개폐업률·시간대·성별 조회
                        → LLM 분석 (상권별 분리 분석 + 기회·리스크)
                        → 유사 상권 추천 테이블 첨부
                     2) 복수 지역: 지역별 지표 비교표
                        → LLM 창업 추천 순위 생성
    │
    ▼
[SignOffAgent] (PARK) ── 도메인별 루브릭 판정
    ├─ grade A: issues 없음, warnings 없음 → 완전 통과
    ├─ grade B: issues 없음, warnings 있음 → 통과 + 사용자 주의 안내
    └─ grade C: issues 있음 → retry_prompt로 재작성
                (최대 max_retries회 → escalate)
    │
    ▼
[Logger] — JSONL 구조 로그 저장 (session_id + grade 포함)
    ├─ logs/queries.jsonl     (모든 요청)
    └─ logs/rejections.jsonl  (거부 이력이 있는 요청만)

별도 플로우:
POST /api/v1/doc/chat → [FoodBusinessPlugin] (NAM)
    대화형 정보 수집 → 식품 영업 신고서 PDF 생성

POST /api/v1/stream → [DomainRouter → Agent → Sign-off] (스트리밍)
    동일한 Q&A 파이프라인을 Server-Sent Events(SSE) 형식으로 스트리밍
```

---

## 최근 추가 기능

### 세션 컨텍스트 메모리 (v1.1)

`/api/v1/query` 요청에 `session_id`와 `founder_context`를 추가하면 창업자의 상황(지역·자본금·업종 등)이 세션 전체에 유지됩니다.

- 동일 `session_id`를 사용하는 한 창업자 프로필을 매 요청마다 반복할 필요가 없습니다.
- `founder_context`를 전달하지 않으면 일반 답변을, 전달하면 개인화된 답변을 생성합니다.
- 서버 프로세스가 재시작되면 인메모리 세션이 초기화됩니다.

### Sign-off 신뢰도 등급 (v1.1)

Sign-off 결과가 이분법(통과/반려)에서 **3단계 등급**으로 확장되었습니다.

| 등급 | 의미 | `approved` | 사용자 액션 |
| --- | --- | :---: | --- |
| **A** | 모든 항목 통과, 경고 없음 | `true` | 그대로 신뢰 가능 |
| **B** | 핵심 항목 통과, 보조 항목 교차 확인 권장 | `true` | `confidence_note` 확인 후 활용 |
| **C** | 핵심 항목 미통과, 재작성 필요 | `false` | 에이전트가 자동 재시도 |

B등급은 기존에 C(재시도)로 처리되던 "법령 개정일 미기재", "수치 출처 불명확" 같은 보조 항목을 통과로 처리하되 사용자에게 확인을 권장합니다.

---

## 필수 조건

- Python **3.12** (팀 공통 기준)
- Azure OpenAI 리소스 (GPT-4o 또는 동급 배포)
- Oracle DB 서버 접속 정보 (상권 분석 데이터 — 팀 공용 서버)
- (선택) Azure AI Search 인덱스 — 법령·정부지원사업 RAG 기능 사용 시
- (선택) Azure Cosmos DB — 서버리스 배포에서 세션 영속화 시
- (선택) 서울시 오픈API 인증키 — 상권 API 기능 사용 시

---

## 설치

```bash
# 1. 이 폴더로 이동
cd integrated_PARK

# 2. Python 3.12로 가상환경 생성
python3.12 -m venv .venv

# 3. 가상환경 활성화
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 4. 의존성 설치
pip install -r requirements.txt
```

---

## 환경 변수 설정

`.env` 파일을 `integrated_PARK/` 폴더 안에 직접 생성합니다.

```text
# ── Oracle DB (상권 에이전트 — 팀 공용 서버) ──
ORACLE_USER=shobi
ORACLE_PASSWORD=<password>
ORACLE_HOST=10.1.92.119
ORACLE_PORT=1521
ORACLE_SID=xe

# ── Azure OpenAI (핵심 — 전 에이전트 공통) ──
AZURE_OPENAI_ENDPOINT=https://<리소스명>.openai.azure.com/
AZURE_OPENAI_API_KEY=<API 키>
AZURE_DEPLOYMENT_NAME=gpt-4o

# ── Azure OpenAI — 임베딩 ──
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_API_VERSION=2024-02-01

# ── Azure AI Search (법령·정부지원사업 RAG) ──
AZURE_SEARCH_ENDPOINT=https://<검색 리소스명>.search.windows.net
AZURE_SEARCH_KEY=<검색 관리자 키>
AZURE_SEARCH_INDEX=legal-index

# ── 서울시 오픈 API (상권 분석) ──
SEOUL_API_KEY=<서울시 오픈API 인증키>

# ── 로그 내보내기 ──
EXPORT_SECRET=<generate-with-secrets.token_urlsafe-32>
```

| 변수 | 필수 | 설명 |
| ---- | :--: | ---- |
| `ORACLE_USER` | ✅ | Oracle DB 사용자명 |
| `ORACLE_PASSWORD` | ✅ | Oracle DB 비밀번호 |
| `ORACLE_HOST` | ✅ | Oracle DB 호스트 IP |
| `ORACLE_PORT` | ✅ | Oracle DB 포트 (기본 `1521`) |
| `ORACLE_SID` | ✅ | Oracle DB SID |
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI 리소스 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API 키 |
| `AZURE_DEPLOYMENT_NAME` | ✅ | 채팅 모델 배포명 (예: `gpt-4o`) |
| `AZURE_EMBEDDING_DEPLOYMENT` | ⬜ | 임베딩 모델 배포명 |
| `AZURE_EMBEDDING_API_VERSION` | ⬜ | 임베딩 API 버전 |
| `AZURE_SEARCH_ENDPOINT` | ⬜ | Azure AI Search 엔드포인트 (RAG) |
| `AZURE_SEARCH_KEY` | ⬜ | Azure AI Search 관리자 키 |
| `AZURE_SEARCH_INDEX` | ⬜ | 검색 인덱스명 (기본값: `legal-index`) |
| `SEOUL_API_KEY` | ⬜ | 서울시 오픈API 인증키 |
| `EXPORT_SECRET` | ⬜ | 로그 내보내기 인증 토큰 |
| `COSMOS_ENDPOINT` | ⬜ | Azure Cosmos DB 엔드포인트 (미설정 시 인메모리 세션) |
| `COSMOS_DATABASE` | ⬜ | Cosmos DB 데이터베이스명 (기본값: `sohobi`) |
| `COSMOS_CONTAINER` | ⬜ | Cosmos DB 컨테이너명 (기본값: `sessions`) |
| `COSMOS_SESSION_TTL` | ⬜ | 세션 TTL 초 (기본값: `86400` = 24시간) |

> ⬜ 선택 항목은 미설정 시 해당 기능이 비활성화되거나 안내 메시지를 반환합니다.
> `COSMOS_ENDPOINT`를 설정하지 않으면 인메모리 딕셔너리로 폴백합니다. 서버 재시작 시 세션이 초기화됩니다.

### 배포 환경 (Azure Container Apps)

현재 운영 배포는 **Azure Container Apps**를 사용합니다. `BACKEND_HOST` 및 `EXPORT_SECRET`은 `integrated_PARK/.env`를 참고하십시오.

---

## 서버 실행

```bash
# integrated_PARK/ 폴더 안에서 실행
.venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

실행 후 `http://localhost:8000/health` 에서 정상 동작을 확인할 수 있습니다.

---

## API 엔드포인트

### `GET /health`

서버 상태 및 사용 가능한 도메인·플러그인 목록 반환.

```bash
curl http://localhost:8000/health
```

---

### `POST /api/v1/query` — Q&A 플로우

질문을 도메인으로 분류하고 에이전트 → Sign-off 루프를 실행합니다.

#### 요청

```json
{
  "question": "홍대 카페 창업 시 예상 매출이 어느 정도인가요?",
  "session_id": "user-abc123",
  "founder_context": "서울 마포구 홍대입구역 인근, 자본금 1,000만 원, 테이크아웃 전문 카페",
  "domain": null,
  "max_retries": 3
}
```

| 필드 | 필수 | 설명 |
| --- | :---: | --- |
| `question` | ✅ | 창업자 질문 |
| `session_id` | ⬜ | 생략 시 서버가 새 UUID를 발급해 응답에 포함 |
| `founder_context` | ⬜ | 창업자 상황 요약. 동일 세션에서 한 번만 전달하면 이후 요청에 자동 적용 |
| `domain` | ⬜ | `"admin"` / `"finance"` / `"legal"` / `"location"`. `null`이면 자동 분류 |
| `max_retries` | ⬜ | Sign-off 재시도 횟수 (기본 3, 최대 10) |

#### 응답

```json
{
  "session_id": "user-abc123",
  "request_id": "a1b2c3d4",
  "status": "approved",
  "domain": "finance",
  "grade": "B",
  "confidence_note": "시뮬레이션 수치의 출처가 명시되지 않아 교차 확인을 권장합니다.",
  "draft": "...",
  "retry_count": 0,
  "agent_ms": 2341,
  "signoff_ms": 891,
  "message": "",
  "rejection_history": []
}
```

| 필드 | 설명 |
| --- | --- |
| `session_id` | 세션 ID (다음 요청 시 재사용) |
| `grade` | `"A"` (완전 신뢰) / `"B"` (교차 확인 권장) / `"C"` (escalate 시) |
| `confidence_note` | grade B일 때 사용자에게 전달할 주의사항. A/C이면 빈 문자열 |
| `agent_ms` | 마지막 에이전트 호출 소요 시간 (ms) |
| `signoff_ms` | 마지막 Sign-off 호출 소요 시간 (ms) |
| `status` | `"approved"` 또는 `"escalated"` (재시도 한도 초과) |

#### curl 예시 — 세션 컨텍스트 활용

```bash
# 1차 요청: 창업자 상황 등록
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "제 상황에서 분식집 수익성이 어떤가요?",
    "session_id": "park-001",
    "founder_context": "서울 마포구, 자본금 1000만원, 테이크아웃 분식집",
    "domain": "finance"
  }'

# 2차 요청: session_id만 전달하면 프로필이 자동 적용됨
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "식품 영업 신고 절차가 어떻게 되나요?",
    "session_id": "park-001",
    "domain": "admin"
  }'
```

#### curl 예시 — 기존 방식 (session 없이)

```bash
# 재무 도메인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집 수익성이 어떤가요?","domain":"finance"}'

# 법무 도메인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"임대차 계약 시 권리금 보호 규정이 있나요?","domain":"legal"}'
```

---

### `POST /api/v1/signoff` — Sign-off 단독 검증

기존 draft를 Sign-off Agent에 직접 전달해 판정합니다.

#### signoff 요청 예시

```json
{
  "domain": "legal",
  "draft": "[사용자 질문]\n...\n\n[에이전트 응답]\n..."
}
```

#### signoff 응답 예시

```json
{
  "grade": "B",
  "approved": true,
  "passed": ["C1", "C2", "C3", "C4", "C5", "G1", "G3", "G4"],
  "warnings": [{"code": "G2", "reason": "법령 개정 시점이 명시되지 않음"}],
  "issues": [],
  "retry_prompt": "",
  "confidence_note": "법령 개정일이 명시되지 않아 최신 법령 확인을 권장합니다."
}
```

---

### `POST /api/v1/doc/chat` — 문서 생성 플로우 (NAM)

대화를 통해 사용자 정보를 수집하고 식품 영업 신고서 PDF를 생성합니다.
Sign-off 대상이 아닌 별도 플로우입니다.

```json
{
  "message": "식품 영업 신고서 만들어주세요",
  "session_id": "user-001"
}
```

정보 수집이 완료되면 `pdf_url`에 다운로드 경로가 반환됩니다.

---

## 도메인 분류 기준

| 도메인 | 해당 질문 유형 | 활성화되는 데이터 소스 |
| ------ | ------------ | -------------------- |
| `admin` | 영업 신고, 허가, 행정 절차, 정부지원사업 | SeoulCommercialPlugin, GovSupportPlugin |
| `finance` | 매출 시뮬레이션, 투자 분析, 수익성 | FinanceSimulationPlugin |
| `legal` | 법령 해석, 계약, 임대차, 권리 의무 | LegalSearchPlugin |
| `location` | 상권 분析, 지역 비교, 매출 지역 데이터, 창업 입지 | CommercialRepository (Oracle DB) |

---

## 로그 시스템

`/api/v1/query` 엔드포인트는 요청마다 `logs/` 폴더에 JSONL 파일을 기록합니다.

| 파일                    | 내용                              |
|-------------------------|-----------------------------------|
| `logs/queries.jsonl`    | 모든 요청 (approved + escalated)  |
| `logs/rejections.jsonl` | Sign-off 거부 이력이 있는 요청만  |

각 줄은 JSON 객체 하나이며, 다음 필드를 포함합니다.

```jsonc
{
  "ts": "2025-03-01T12:34:56.789012",
  "session_id": "park-001",          // 세션 추적 키 (v1.1 추가)
  "request_id": "a1b2c3d4",
  "domain": "finance",
  "status": "approved",
  "grade": "B",                      // A / B / C (v1.1 추가)
  "retry_count": 0,
  "latency_ms": 4231,
  "question": "...",
  "final_draft": "...",
  "rejection_history": [
    {
      "attempt": 1,
      "approved": false,
      "grade": "C",
      "passed": ["C1", "C2", "C3", "C4", "C5", "F1", "F2"],
      "warnings": [],
      "issues": [{"code": "F3", "reason": "..."}, {"code": "F4", "reason": "..."}],
      "retry_prompt": "..."
    }
  ]
}
```

로그 파일 자체는 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

---

## Sign-off 루브릭 수정

도메인별 Sign-off 루브릭(평가 기준)은 `prompts/` 폴더에 있습니다.
루브릭 구조 설명, 항목별 해설, 실제 개선 사례, 테스트 방법은 아래를 참고하세요.

> [`prompts/README.md`](prompts/README.md)

### warnings 항목 가이드

v1.1부터 루브릭에 `warnings` 배열이 추가되었습니다.

- **issues** (기존): 재작성을 요구하는 blocking 결함. 하나라도 있으면 `approved=false`.
- **warnings** (신규): 통과는 하되 사용자가 교차 확인해야 할 사항. `approved`에 영향 없음.

```text
핵심 항목 (issues로만 분류)       보조 항목 (warnings 가능)
─────────────────────────────    ──────────────────────────────
C1 질문 응답성                   법령 개정일 표현이 약한 경우 (G2)
C3 내부 일관성                   수치 출처가 불명확한 경우 (F2)
G1 면책 조항                     서식 번호 출처가 불명확한 경우 (A2)
F1 수치 제시
```

---

## 개선 이력

| 문서                                                                          | 내용                                              |
|-------------------------------------------------------------------------------|---------------------------------------------------|
| [`docs/finance_signoff_improvement.md`](docs/finance_signoff_improvement.md) | 재무 Sign-off C2·C5·F3·F4·F5 개선 전후 상세 분석 |

---

## 폴더 구조

```text
integrated_PARK/
├── api_server.py                 # FastAPI 서버 (세션 관리 + 엔드포인트)
├── kernel_setup.py               # Azure OpenAI 커널 초기화
├── domain_router.py              # 도메인 분류 (키워드 + LLM) — location 포함
├── orchestrator.py               # 에이전트 → Sign-off 재시도 루프 (타이밍 측정 포함)
├── logger.py                     # JSONL 구조 로그 기록 (session_id + grade)
├── log_formatter.py              # JSONL 로그 → 사람이 읽기 편한 형태 변환 (CLI)
├── session_store.py              # 세션 스토어 (Cosmos DB / 인메모리 폴백)
├── variable_extractor.py         # 이전 응답에서 재무 변수 추출 (Path B)
├── agents/
│   ├── admin_agent.py            # 행정 에이전트 (프로필 주입 + 상권 플러그인)
│   ├── finance_agent.py          # 재무 에이전트 (프로필 주입 + 4단계 시뮬레이션)
│   ├── legal_agent.py            # 법무 에이전트 (프로필 주입 + 법령 RAG)
│   └── location_agent.py         # 상권분析 에이전트 (Oracle DB 조회 + LLM 분析, CHOI)
├── db/
│   ├── repository.py             # CommercialRepository — Oracle 연결 풀 포함
│   └── commercial.db             # 로컬 개발용 SQLite DB 13 MB (참고용)
├── plugins/
│   ├── seoul_commercial_plugin.py   # 서울시 상권 API (CHOI)
│   ├── finance_simulation_plugin.py # 몬테카를로 시뮬레이션 (CHANG)
│   ├── legal_search_plugin.py       # Azure AI Search 법령 RAG (CHOI)
│   ├── gov_support_plugin.py        # 정부지원사업 벡터 검색 RAG
│   ├── food_business_plugin.py      # 영업 신고서 PDF 생성 (NAM)
│   └── location_plugin.py           # 상권分析 SK Plugin 래퍼 (CHOI)
├── signoff/
│   └── signoff_agent.py          # Sign-off 판정 엔진 — grade A/B/C (PARK)
├── prompts/                      # 도메인별 Sign-off 평가 루브릭
│   ├── README.md                 # 루브릭 수정 가이드
│   ├── signoff_admin/evaluate/skprompt.txt      # A1~A5
│   ├── signoff_finance/evaluate/skprompt.txt    # F1~F5, warnings + grade
│   ├── signoff_legal/evaluate/skprompt.txt      # G1~G4, warnings + grade
│   └── signoff_location/evaluate/skprompt.txt  # S1~S5 (수치·기준·기회리스크·지역업종·면책)
├── scripts/
│   ├── pull_logs.py              # 배포 백엔드에서 로그 다운로드
│   └── merge_logs.py             # 로그 파일 병합
├── logs/                         # JSONL 로그 (Git 제외)
│   ├── queries.jsonl
│   └── rejections.jsonl
├── docs/
│   └── finance_signoff_improvement.md
├── Dockerfile                    # Azure Container Apps 빌드
├── requirements.txt
└── .env                          # 환경 변수 (Git 제외)
```
