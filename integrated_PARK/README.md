# SOHOBI 통합 에이전트

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
    ├─ finance → [FinanceAgent]
    │            └─ FinanceSimulationPlugin (CHANG)
    │               몬테카를로 시뮬레이션 3단계 파이프라인
    │               (파라미터 추출 → 시뮬레이션 → 설명 생성)
    │
    └─ legal   → [LegalAgent]
                 └─ LegalSearchPlugin (CHOI)
                    Azure AI Search 법령 RAG 자동 조회
    │
    ▼
[SignOffAgent] (PARK) ── 도메인별 루브릭 판정
    ├─ approved → 최종 응답
    └─ rejected → retry_prompt로 재작성 (최대 3회 → escalate)

별도 플로우:
POST /api/v1/doc/chat → [FoodBusinessPlugin] (NAM)
    대화형 정보 수집 → 식품 영업 신고서 PDF 생성
```

---

## 필수 조건

- Python 3.12
- Azure OpenAI 리소스 (GPT-4o 또는 동급 배포)
- (선택) Azure AI Search 인덱스 — 법령 RAG 기능 사용 시
- (선택) 서울시 오픈API 인증키 — 상권 분석 기능 사용 시

---

## 설치

```bash
# 1. 이 폴더로 이동
cd integrated

# 2. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt
```

---

## 환경 변수 설정

```bash
# 템플릿 복사
cp .env.example .env
```

`.env` 파일을 열고 아래 값을 채웁니다.

| 변수 | 필수 | 설명 |
|------|:----:|------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI 리소스 엔드포인트 |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API 키 |
| `AZURE_DEPLOYMENT_NAME` | ✅ | 채팅 모델 배포명 (예: `gpt-4o`) |
| `AZURE_EMBEDDING_DEPLOYMENT` | ⬜ | 임베딩 모델 배포명 (기본값: `text-embedding-3-small`) |
| `AZURE_EMBEDDING_API_VERSION` | ⬜ | 임베딩 API 버전 (기본값: `2024-02-01`) |
| `AZURE_SEARCH_ENDPOINT` | ⬜ | Azure AI Search 엔드포인트 (법령 RAG) |
| `AZURE_SEARCH_KEY` | ⬜ | Azure AI Search 관리자 키 |
| `AZURE_SEARCH_INDEX` | ⬜ | 검색 인덱스명 (기본값: `legal-index`) |
| `SEOUL_API_KEY` | ⬜ | 서울시 오픈API 인증키 (상권 분석) |

> ⬜ 선택 항목은 미설정 시 해당 플러그인이 오류 대신 안내 메시지를 반환합니다.

---

## 서버 실행

```bash
# integrated/ 폴더 안에서 실행
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

실행 후 `http://localhost:8000/health` 에서 정상 동작을 확인할 수 있습니다.

---

## API 엔드포인트

### `GET /health`
서버 상태 및 사용 가능한 도메인·플러그인 목록 반환.

---

### `POST /api/v1/query` — Q&A 플로우

질문을 도메인으로 분류하고 강화된 에이전트 → Sign-off 루프를 실행합니다.

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
  "domain": "admin",
  "draft": "...",
  "retry_count": 1,
  "message": ""
}
```

- `status`: `"approved"` (통과) 또는 `"escalated"` (한도 초과)

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

## 폴더 구조

```
integrated/
├── kernel_setup.py               # Azure OpenAI 커널 초기화
├── domain_router.py              # 도메인 분류 (키워드 + LLM)
├── orchestrator.py               # 에이전트 → Sign-off 루프
├── api_server.py                 # FastAPI 서버
├── agents/
│   ├── admin_agent.py            # 행정 에이전트 + 상권 플러그인
│   ├── finance_agent.py          # 재무 에이전트 + 시뮬레이션 파이프라인
│   └── legal_agent.py            # 법무 에이전트 + 법령 RAG
├── plugins/
│   ├── seoul_commercial_plugin.py  # 서울시 상권 API (CHOI)
│   ├── finance_simulation_plugin.py # 몬테카를로 시뮬레이션 (CHANG)
│   ├── legal_search_plugin.py      # Azure AI Search RAG (CHOI)
│   └── food_business_plugin.py     # 영업 신고서 PDF 생성 (NAM)
├── signoff/
│   └── signoff_agent.py          # Sign-off 판정 엔진 (PARK)
├── prompts/                      # 도메인별 Sign-off 평가 프롬프트
├── requirements.txt
└── .env.example
```
