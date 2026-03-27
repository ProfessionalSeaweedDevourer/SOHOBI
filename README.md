# SOHOBI: 소상공인 창업 지원 다중 에이전트 AI 시스템

> **MS SAY 2-2 팀** | 2026년 2월 25일 ~ 2026년 4월 10일

---

## 프로젝트 개요

소규모 자영업자(식음료·카페·푸드트럭 등 F&B 업종)를 위한 **다중 에이전트 AI 플랫폼**입니다.
창업을 준비하는 소상공인이 자연어로 질문하면, 전문 하위 에이전트들이 협력하여 법률·세무·상권 분석·재무 시뮬레이션 등 검증된 답변과 실질적인 문서를 제공합니다.

---

## 팀 구성

| 이름 | 역할 |
|------|------|
| 남대은 | 제품 책임자 (PO) |
| 박주현 | 프로젝트 관리자 (PM) |
| 우태희 | 데이터 엔지니어 |
| 장우경 | 로직 엔지니어 |
| 최진영 | 풀스택 개발 |
| 장진태 | 외부 멘토 (Microsoft) |

---

## 시스템 아키텍처

```
사용자 자연어 입력
        │
        ▼
┌─────────────────────────────────────┐
│         FastAPI  (api_server.py)     │
│                                     │
│  POST /api/v1/query   ─┐            │
│  POST /api/v1/doc/chat  ├── 진입점  │
│  POST /api/v1/signoff  ─┘            │
│  GET  /api/v1/logs                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       도메인 라우터 (domain_router)   │
│                                     │
│  1단계: 키워드 매칭 (2개 이상 일치)   │
│  2단계: LLM 분류 (JSON 응답)         │
│  → admin / finance / legal / location│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    오케스트레이터 (orchestrator.py)   │  ← Semantic Kernel
│                                     │
│  도메인 → 에이전트 클래스 매핑        │
│  세션 컨텍스트(profile) 전달          │
│  에이전트 호출 + 타이밍 측정          │
│  SSE 스트리밍 지원 (run_stream)      │
└──┬──────────┬──────────┬────────┬───┘
   │          │          │        │
   ▼          ▼          ▼        ▼
법률·세무   상권 분석   재무 엔진  행정 서류
에이전트    에이전트    에이전트   에이전트
   │          │          │        │
   └──────────┴──────────┴────────┘
                    │  draft
                    ▼
   ┌──────────────────────────────────┐
   │     Sign-off 검증 에이전트        │
   │                                  │
   │  도메인별 루브릭 코드 체크         │
   │  grade A → 통과                  │
   │  grade B → 경고 포함 통과         │
   │  grade C → retry_prompt 생성     │
   │            → 에이전트 재호출      │
   │            (최대 3회)             │
   └──────────────────────────────────┘
```

### 도메인 라우팅 상세

`domain_router.py`는 2단계로 질문을 분류합니다.

1. **키워드 매칭** — 미리 정의된 키워드 목록에서 2개 이상 일치하면 즉시 반환 (confidence 0.85)
2. **LLM 분류** — 키워드 매칭 실패 시 GPT-4o에 JSON 분류 요청 (fallback: `admin`)

| 도메인 | 분류 기준 키워드 예시 |
| ------ | -------------------- |
| `admin` | 신고, 허가, 인허가, 서류, 위생, 영업신고 |
| `finance` | 재무, 대출, 수익, 비용, 투자, 시뮬레이션 |
| `legal` | 법, 계약, 소송, 보증금, 임대차, 판례 |
| `location` | 상권, 지역, 홍대, 강남, 잠실, 비교 |

### Sign-off 루브릭

에이전트가 생성한 draft는 도메인별 루브릭 코드 전체를 충족해야 통과합니다.

| 도메인 | 필수 코드 |
| ------ | --------- |
| `admin` | C1~C5 (공통) + A1~A5 (행정) |
| `finance` | C1~C5 (공통) + F1~F5 (재무) |
| `legal` | C1~C5 (공통) + G1~G4 (법무) |
| `location` | C1~C5 (공통) + S1~S5 (상권) |

### 하위 에이전트 상세

#### 법률·세무 에이전트 (`agents/legal_agent.py`)

- **플러그인**: `LegalSearchPlugin` — Azure AI Search로 법령 문서 벡터 검색
- **동작**: 질문 수신 → `LegalSearch-search_legal_docs` 자동 호출 → 검색 결과 인용 후 응답
- **출력 기준**: 법령명·조항 번호 필수 인용, 면책 문구 3줄 포함, 단정 표현 금지
- **재처리**: Sign-off C 판정 시 `retry_prompt` 반영하여 전체 응답 재작성

#### 상권 분석 에이전트 (`agents/location_agent.py`)

- **데이터**: Oracle DB (외부 서버, `CommercialRepository`)
- **동작 2단계**:
  1. LLM으로 질문에서 `{mode, locations, business_type, quarter}` JSON 추출
  2. DB 조회 결과를 LLM에 전달 → 한국어 분석 리포트 생성
- **모드**: `analyze` (단일 지역) / `compare` (2개 이상 지역 비교)
- **기본 분기**: 언급 없으면 서울 2024년 4분기 데이터 사용

#### 재무 엔진 에이전트 (`agents/finance_agent.py`)

- **플러그인**: `FinanceSimulationPlugin` — 몬테카를로 시뮬레이션 Python 실행
- **동작 3단계 파이프라인**:
  1. LLM으로 질문에서 시뮬레이션 파라미터 JSON 추출 (revenue, cost, rent, initial_investment 등)
  2. `FinanceSimulationPlugin` 실행 → 수치 결과 + base64 PNG 차트 반환
  3. LLM으로 결과 해설 draft 생성
- **특이사항**: 미입력 항목은 지역·업종 평균치 적용, 단위 미명시 시 만원 기준 해석

#### 행정 서류 에이전트 (`agents/admin_agent.py`)

- **플러그인**: `SeoulCommercialPlugin` — 지역·업종별 상권 데이터 조회
- **동작**: 식품위생법 제37조 기반 영업신고 절차 단계별 안내, 서울 상권 데이터 응답에 반영
- **출력 기준**: 관할 기관(시·군·구청 위생과) 명시, 처리 기한(3~7영업일) 포함
- **문서 생성**: `/api/v1/doc/chat` 엔드포인트에서 대화형으로 정보 수집 후 식품영업신고서 PDF 출력

---

## 기술 스택

### 백엔드 (`integrated_PARK/`)

| 분류 | 기술 |
|------|------|
| AI 오케스트레이션 | Semantic Kernel 1.40.0 |
| AI 모델 플랫폼 | Azure AI Foundry (GPT-4o) |
| API 서버 | FastAPI 0.115 + Uvicorn |
| RAG 파이프라인 | Azure AI Search |
| 세션 저장소 | Azure Cosmos DB |
| 로그 저장소 | Azure Blob Storage |
| 상권 DB | Oracle DB (외부 서버) |
| PDF 생성 | ReportLab + pdfkit + Jinja2 |
| 재무 시각화 | Matplotlib + NumPy |
| 배포 | Railway (Nixpacks) |

### 프론트엔드 (`frontend/`)

| 분류 | 기술 |
|------|------|
| UI 프레임워크 | React 19 + Vite 7 |
| 스타일링 | Tailwind CSS 3 |
| 라우팅 | React Router DOM 7 |
| 마크다운 렌더링 | react-markdown 10 |

---

## 주요 기능

- **법령 RAG** — 생활법령정보 기반 검색 증강 생성으로 최신 법규 정확 인용
- **상권 분석** — 서울 2024 Q4 데이터 기반 매출 현황, 유동인구, 실거래가 분석
- **재무 시뮬레이션** — 몬테카를로 기반 창업 리스크 수치 분석 및 PNG 차트 반환
- **행정 서류 자동 생성** — 대화형 정보 수집 후 식품영업신고서 PDF 출력
- **Sign-off 검증** — 응답 품질 사후 평가, 기준 미달 시 최대 3회 재처리
- **로그 뷰어** — 에이전트 처리 과정 JSONL 로그 실시간 조회

---

## 디렉토리 구조

```
SOHOBI/
├── integrated_PARK/          # 메인 통합 백엔드
│   ├── api_server.py         # FastAPI 진입점
│   ├── orchestrator.py       # Semantic Kernel 오케스트레이션
│   ├── domain_router.py      # 질문 → 에이전트 라우팅
│   ├── agents/               # 하위 에이전트
│   │   ├── legal_agent.py    # 법률·세무
│   │   ├── location_agent.py # 상권 분석
│   │   ├── finance_agent.py  # 재무 시뮬레이션
│   │   └── admin_agent.py    # 행정 서류
│   ├── signoff/              # Sign-off 검증 에이전트
│   ├── db/                   # SQLite 상권 DB (서울 2024 Q4)
│   ├── prompts/              # 에이전트 시스템 프롬프트
│   ├── plugins/              # Semantic Kernel 플러그인
│   └── requirements.txt
├── frontend/                 # React + Vite 프론트엔드
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx      # 메인 랜딩
│       │   ├── UserChat.jsx  # 사용자 챗 인터페이스
│       │   ├── DevChat.jsx   # 개발자 디버그 챗
│       │   └── LogViewer.jsx # 에이전트 로그 뷰어
│       └── components/       # 공통 UI 컴포넌트
├── docs/
│   ├── session-reports/      # 세션 리포트 (날짜별)
│   ├── architecture/         # 아키텍처 다이어그램 (HTML)
│   └── plans/                # 개선·테스트 플랜 문서
└── CHANG/ CHOI/ NAM/ PARK/ TERRY/  # 팀원별 개발 폴더
```

---

## 로컬 실행

### 사전 요구사항

- Python 3.12
- Node.js 18+
- `.env` 파일 (Azure API 키 등, `.env.example` 참고)

### 백엔드

```bash
cd integrated_PARK
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
.venv/bin/python3 api_server.py    # http://localhost:8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

### API 동작 확인

```bash
# 헬스 체크
curl http://localhost:8000/health

# 질문 쿼리
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "서울 강남구에서 카페 창업 시 필요한 인허가는?"}'
```

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
| ------ | ---- | ---- |
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/v1/query` | 자연어 질문 → 에이전트 처리 → Sign-off |
| `POST` | `/api/v1/signoff` | draft 단독 Sign-off 검증 |
| `POST` | `/api/v1/doc/chat` | 문서 생성 대화 (식품영업신고서 PDF) |
| `GET` | `/api/v1/logs` | JSONL 로그 조회 |

---

## 개발 환경

- Azure 테넌트: `soldeskms.onmicrosoft.com`
- 배포: Railway (`integrated_PARK/railway.json`)
- 협업: Slack (`mssay2-2.slack.com`), GitHub, Trello

---

## 설계 원칙

- MVP 범위: **서울 기반 F&B 업종** → 이후 전국 및 타 업종으로 확장 예정
- 에이전트 간 정보 공유는 Semantic Kernel 기반 구조적 처리
- 버전은 `==`으로 고정하여 재현성 보장 (Python 3.12)
