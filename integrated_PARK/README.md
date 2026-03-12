# SOHOBI 통합 에이전트 (integrated_PARK)

PARK · CHOI · CHANG · NAM 각자의 작업물을 하나의 Semantic Kernel 시스템으로 통합한 폴더입니다.

---

## 아키텍처

```
사용자 질문
    │
    ▼
[DomainRouter] ── 키워드(1차) / LLM(2차) 분류
    │
    ├─ admin   → [AdminAgent]
    │            └─ SeoulCommercialPlugin (CHOI)
    │               서울시 상권 API — 지역·업종별 매출·점포수 자동 조회
    │
    ├─ finance → [FinanceAgent]  ← 4단계 명시적 파이프라인
    │            └─ FinanceSimulationPlugin (CHANG)
    │               1) 자연어 → 시뮬레이션 파라미터 JSON 추출
    │               2) 몬테카를로 10,000회 시뮬레이션
    │                  (평균·표준편차·P5·P95·손실확률 5개 통계 반환)
    │               3) 가정 조건 + 통계 → LLM 설명 draft 생성
    │               4) 초기 투자 언급 시 투자 회수 시나리오 병합
    │
    └─ legal   → [LegalAgent]
                 └─ LegalSearchPlugin (CHOI)
                    Azure AI Search 법령 RAG 자동 조회
    │
    ▼
[SignOffAgent] (PARK) ── 도메인별 루브릭 판정
    ├─ approved → 최종 응답 반환
    └─ rejected → retry_prompt로 재작성 (최대 max_retries회 → escalate)
    │
    ▼
[Logger] — JSONL 구조 로그 저장
    ├─ logs/queries.jsonl     (모든 요청)
    └─ logs/rejections.jsonl  (거부 이력이 있는 요청만)

별도 플로우:
POST /api/v1/doc/chat → [FoodBusinessPlugin] (NAM)
    대화형 정보 수집 → 식품 영업 신고서 PDF 생성
```

---

## 필수 조건

- Python **3.12** (팀 공통 기준)
- Azure OpenAI 리소스 (GPT-4o 또는 동급 배포)
- (선택) Azure AI Search 인덱스 — 법령 RAG 기능 사용 시
- (선택) 서울시 오픈API 인증키 — 상권 분석 기능 사용 시

---

## 설치

```bash
# 1. 이 폴더로 이동
cd integrated_PARK

# 2. Python 3.12로 가상환경 생성 (시스템에 설치된 3.12 경로 사용)
/usr/local/bin/python3.12 -m venv .venv
# 또는: python3.12 -m venv .venv

# 3. 가상환경 활성화
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 4. 의존성 설치
pip install -r requirements.txt
```

---

## 환경 변수 설정

`.env` 파일을 `integrated_PARK/` 폴더 안에 직접 생성합니다.

```bash
cp .env.example .env   # 템플릿이 있는 경우
```

또는 아래 형식으로 직접 작성하세요.

```
AZURE_OPENAI_ENDPOINT=https://<리소스명>.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<API 키>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_DEPLOYMENT_NAME=gpt-4o
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_API_VERSION=2024-02-01
AZURE_SEARCH_ENDPOINT=https://<검색 리소스명>.search.windows.net
AZURE_SEARCH_KEY=<검색 관리자 키>
AZURE_SEARCH_INDEX=legal-index
SEOUL_API_KEY=<서울시 오픈API 인증키>
```

| 변수 | 필수 | 설명 |
|------|:----:|------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI 리소스 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API 키 |
| `AZURE_DEPLOYMENT_NAME` | ✅ | 채팅 모델 배포명 (예: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | ✅ | API 버전 (예: `2024-08-01-preview`) |
| `AZURE_EMBEDDING_DEPLOYMENT` | ⬜ | 임베딩 모델 배포명 |
| `AZURE_EMBEDDING_API_VERSION` | ⬜ | 임베딩 API 버전 |
| `AZURE_SEARCH_ENDPOINT` | ⬜ | Azure AI Search 엔드포인트 (법령 RAG) |
| `AZURE_SEARCH_KEY` | ⬜ | Azure AI Search 관리자 키 |
| `AZURE_SEARCH_INDEX` | ⬜ | 검색 인덱스명 (기본값: `legal-index`) |
| `SEOUL_API_KEY` | ⬜ | 서울시 오픈API 인증키 (상권 분석) |

> ⬜ 선택 항목은 미설정 시 해당 플러그인이 오류 대신 안내 메시지를 반환합니다.

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

**요청**
```json
{
  "question": "홍대 카페 창업 시 예상 매출이 어느 정도인가요?",
  "domain": null,
  "max_retries": 3
}
```

- `domain`: `"admin"` / `"finance"` / `"legal"` 중 하나를 직접 지정하거나, `null`로 두면 자동 분류합니다.
- `max_retries`: Sign-off 재시도 횟수 (기본값 3, 최대 10).

**응답**
```json
{
  "request_id": "a1b2c3d4",
  "status": "approved",
  "domain": "finance",
  "draft": "...",
  "retry_count": 1,
  "message": ""
}
```

- `status`: `"approved"` (Sign-off 통과) 또는 `"escalated"` (재시도 한도 초과)

#### curl 예시

```bash
# 재무 도메인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"월매출 700만원, 재료비 200만원, 직원 1명 월급 250만원으로 분식집을 창업하려 합니다. 수익성이 어떤가요?","domain":"finance"}'

# 행정 도메인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"홍대 카페 상권 분석해줘","domain":"admin"}'

# 법무 도메인
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"임대차 계약 시 권리금 보호 규정이 있나요?","domain":"legal"}'
```

---

### `POST /api/v1/signoff` — Sign-off 단독 검증

기존 draft를 Sign-off Agent에 직접 전달해 판정합니다.

**요청**
```json
{
  "domain": "legal",
  "draft": "[사용자 질문]\n...\n\n[에이전트 응답]\n..."
}
```

**응답**
```json
{
  "approved": true,
  "passed": ["C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"],
  "issues": [],
  "retry_prompt": ""
}
```

---

### `POST /api/v1/doc/chat` — 문서 생성 플로우 (NAM)

대화를 통해 사용자 정보를 수집하고 식품 영업 신고서 PDF를 생성합니다.
Sign-off 대상이 아닌 별도 플로우입니다.

**요청**
```json
{
  "message": "식품 영업 신고서 만들어주세요",
  "session_id": "user-001"
}
```

- `session_id`: 동일 사용자의 대화 세션을 유지하기 위한 임의 문자열.

**응답**
```json
{
  "reply": "안녕하세요! 신고서 작성을 도와드리겠습니다. 대표자 성함을 먼저 알려주세요.",
  "pdf_url": null
}
```

정보 수집이 완료되면 `pdf_url`에 다운로드 경로가 반환됩니다.

---

## 도메인 분류 기준

| 도메인 | 해당 질문 유형 | 활성화되는 플러그인 |
|--------|--------------|-------------------|
| `admin` | 영업 신고, 허가, 행정 절차, 상권 입지 | SeoulCommercialPlugin |
| `finance` | 매출 시뮬레이션, 투자 분석, 수익성 | FinanceSimulationPlugin |
| `legal` | 법령 해석, 계약, 임대차, 권리 의무 | LegalSearchPlugin |

---

## 로그 시스템

`/api/v1/query` 엔드포인트는 요청마다 `logs/` 폴더에 JSONL 파일을 기록합니다.

| 파일 | 내용 |
|------|------|
| `logs/queries.jsonl` | 모든 요청 (approved + escalated) |
| `logs/rejections.jsonl` | Sign-off 거부 이력이 있는 요청만 |

각 줄은 JSON 객체 하나이며, 다음 필드를 포함합니다.

```jsonc
{
  "ts": "2025-03-01T12:34:56.789012",   // 요청 시각 (UTC)
  "request_id": "a1b2c3d4",
  "domain": "finance",
  "status": "approved",
  "retry_count": 1,
  "latency_ms": 4231.5,
  "question": "...",
  "draft": "...",
  "rejection_history": [
    {
      "attempt": 1,
      "approved": false,
      "passed": ["C1", "C2", "C3", "C4", "C5", "F1", "F2"],
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

---

## 개선 이력

주요 변경 내역은 `docs/` 폴더에 마크다운 문서로 기록됩니다.

| 문서 | 내용 |
|------|------|
| [`docs/finance_signoff_improvement.md`](docs/finance_signoff_improvement.md) | 재무 Sign-off C2·C5·F3·F4·F5 개선 전후 상세 분석 |

---

## 폴더 구조

```
integrated_PARK/
├── api_server.py                 # FastAPI 서버 (엔드포인트 정의)
├── kernel_setup.py               # Azure OpenAI 커널 초기화
├── domain_router.py              # 도메인 분류 (키워드 + LLM)
├── orchestrator.py               # 에이전트 → Sign-off 재시도 루프
├── logger.py                     # JSONL 구조 로그 기록
├── agents/
│   ├── admin_agent.py            # 행정 에이전트 + 상권 플러그인
│   ├── finance_agent.py          # 재무 에이전트 + 4단계 시뮬레이션 파이프라인
│   └── legal_agent.py            # 법무 에이전트 + 법령 RAG
├── plugins/
│   ├── seoul_commercial_plugin.py   # 서울시 상권 API (CHOI)
│   ├── finance_simulation_plugin.py # 몬테카를로 시뮬레이션 (CHANG)
│   ├── legal_search_plugin.py       # Azure AI Search RAG (CHOI)
│   └── food_business_plugin.py      # 영업 신고서 PDF 생성 (NAM)
├── signoff/
│   └── signoff_agent.py          # Sign-off 판정 엔진 (PARK)
├── prompts/                      # 도메인별 Sign-off 평가 루브릭
│   ├── README.md                 # 루브릭 수정 가이드 (← 팀원 참고)
│   ├── signoff_finance/evaluate/skprompt.txt
│   ├── signoff_legal/evaluate/skprompt.txt
│   └── signoff_admin/evaluate/skprompt.txt
├── logs/                         # JSONL 로그 (Git 제외)
│   ├── queries.jsonl
│   └── rejections.jsonl
├── docs/                         # 개선 이력 문서
│   └── finance_signoff_improvement.md
├── requirements.txt              # Python 3.12 기준 의존성
└── .env                          # 환경 변수 (Git 제외)
```
