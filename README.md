# SOHOBI: 소상공인 창업 지원 다중 에이전트 AI 시스템

> **MS SAY 2-2 팀** | 2026년 2월 25일 ~ 2026년 4월 10일
> **라이브 서비스**: [sohobi.net](https://sohobi.net)

---

## 프로젝트 개요

소규모 자영업자(식음료·카페·푸드트럭 등 F&B 업종)를 위한 **다중 에이전트 AI 플랫폼**입니다.
창업을 준비하는 소상공인이 자연어로 질문하면, **5개 전문 하위 에이전트**가 협력하여 법률·세무·상권 분석·재무 시뮬레이션·행정 절차 안내 등 **검증된 답변과 실질적인 문서**를 제공합니다.

### 핵심 가치

| 기존 방식 | SOHOBI |
|-----------|--------|
| 변호사·세무사·부동산 개별 상담 (수십~수백만원) | 5개 AI 전문 에이전트가 원스톱 무료 컨설팅 |
| 5,600+ 정부 지원 프로그램 중 본인 해당 여부 파악 불가 | 하이브리드 RAG로 수혜 가능 프로그램 자동 매칭 |
| 감에 의존한 수익 판단 | Monte Carlo 10,000회 시뮬레이션 확률 분포 |
| 행정 서류 작성법 모름 | 대화형 정보 수집 → PDF 자동 생성 |

---

## 팀 구성

| 이름 | 역할 |
|------|------|
| 남대은 | 제품 책임자 (PO) |
| 박주현 | 프로젝트 관리자 (PM) |
| 우태희 | 데이터 엔지니어 |
| 장우경 | 로직 엔지니어 |
| 최진영 | 풀스택 개발 |
| 정주원 | 외부 멘토 (Microsoft) |

---

## 시스템 아키텍처

```text
사용자 자연어 입력
        │
        ▼
┌─────────────────────────────────────┐
│         FastAPI  (api_server.py)     │
│                                     │
│  POST /api/v1/query   ─┐            │
│  POST /api/v1/stream    ├── 진입점  │
│  POST /api/v1/doc/chat  │           │
│  POST /api/v1/signoff  ─┘           │
│  GET  /api/v1/stats                 │
│  GET  /api/v1/logs                  │
│  + auth / map / feedback / roadmap  │
│    checklist / report 라우터        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       도메인 라우터 (domain_router)   │
│                                     │
│  1단계: 키워드 매칭 (2개 이상 일치)   │
│  2단계: LLM 분류 (JSON 응답)         │
│  → admin / finance / legal          │
│    / location / chat                │
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
│  chat 도메인은 Sign-off 바이패스     │
└──┬──────────┬──────────┬──────┬───┬─┘
   │          │          │      │   │
   ▼          ▼          ▼      ▼   ▼
법률·세무   상권 분석   재무 엔진  행정  안내
에이전트    에이전트    에이전트  에이전트 에이전트
   │          │          │      │
   └──────────┴──────────┴──────┘
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
| `admin` | 신고, 허가, 인허가, 서류, 위생, 영업신고, 지원금, 보조금 |
| `finance` | 재무, 대출, 수익, 비용, 투자, 시뮬레이션 |
| `legal` | 법, 계약, 소송, 보증금, 임대차, 판례 |
| `location` | 상권, 지역, 홍대, 강남, 잠실, 비교 |
| `chat` | 안녕, 사용법, 어떻게 사용, 기능 설명 (Sign-off 바이패스) |

### Sign-off 루브릭

에이전트가 생성한 draft는 도메인별 루브릭 코드 전체를 충족해야 통과합니다.

| 도메인 | 필수 코드 |
| ------ | --------- |
| `admin` | C1~C5 (공통) + A1~A5 (행정) + SEC1~SEC3 (보안) + RJ1~RJ3 (거절) |
| `finance` | C1~C5 (공통) + F1~F5 (재무) + SEC1~SEC3 (보안) + RJ1~RJ3 (거절) |
| `legal` | C1~C5 (공통) + G1~G4 (법무) + SEC1~SEC3 (보안) + RJ1~RJ3 (거절) |
| `location` | C1~C5 (공통) + S1~S5 (상권) + SEC1~SEC3 (보안) + RJ1~RJ3 (거절) |
| `chat` | Sign-off 없음 (즉시 반환) |

등급 판정은 이슈의 severity로 결정된다: `high`/`medium` severity 이슈 → **grade C** (재처리), `low` severity 이슈만 있거나 경고만 있음 → **grade B** (경고 포함 통과), 이슈·경고 없음 → **grade A** (통과). SEC1~SEC3·RJ1~RJ3 코드는 severity 무관 항상 `high`로 강제된다.

### 하위 에이전트 상세

#### 안내 에이전트 (`agents/chat_agent.py`)

- **플러그인**: 없음 (Sign-off 바이패스, 즉시 반환)
- **동작**: 서비스 안내, 에이전트 사용법 설명, 일상 대화 처리
- **출력 기준**: 4가지 전문 에이전트의 기능·입력값·예시 질문을 친절하게 안내

#### 법률·세무 에이전트 (`agents/legal_agent.py`)

- **플러그인**: `LegalSearchPlugin` — Azure AI Search로 법령 문서 벡터 검색 (top-3)
- **동작**: 질문 수신 → `LegalSearch-search_legal_docs` 자동 호출 → 검색 결과 인용 후 응답
- **출력 기준**: 법령명·조항 번호 필수 인용, 면책 문구 3줄 포함, 단정 표현 금지
- **재처리**: Sign-off C 판정 시 `retry_prompt` 반영하여 전체 응답 재작성

#### 상권 분석 에이전트 (`agents/location_agent.py`)

- **데이터**: Azure PostgreSQL Flexible Server (`CommercialRepository`)
- **동작 2단계**:
  1. LLM으로 질문에서 `{mode, locations, business_type, quarter}` JSON 추출
  2. DB 조회 결과를 LLM에 전달 → 한국어 분석 리포트 생성
- **모드**: `analyze` (단일 지역, 시간대·성별·연령대·유사상권 포함) / `compare` (2개 이상 비교)
- **기본 분기**: 언급 없으면 서울 2024년 4분기 데이터 사용

#### 재무 엔진 에이전트 (`agents/finance_agent.py`)

- **플러그인**: `FinanceSimulationPlugin` — 몬테카를로 10,000회 시뮬레이션 (ThreadPoolExecutor 비동기)
- **동작 4단계 파이프라인**:
  1. LLM으로 질문에서 시뮬레이션 파라미터 JSON 추출 (revenue, cost, rent, initial_investment 등)
  2. `FinanceSimulationPlugin` 실행 → 수치 결과 (P5·P20·P95·손실확률·안전마진) + base64 히스토그램 차트
  3. LLM으로 결과 해설 draft 생성
  4. 초기 투자 입력 시 투자 회수 시나리오 병합
- **특이사항**: 미입력 항목은 지역·업종 평균치 적용, 단위 미명시 시 만원 기준 해석

#### 행정 서류 에이전트 (`agents/admin_agent.py`)

- **플러그인**:
  - `AdminProcedurePlugin` — 법령 검증된 5대 절차 KB (영업신고·위생교육·사업자등록·보건증·소방)
  - `GovSupportPlugin` — 정부지원사업 하이브리드 검색 RAG (5,600건+, 보조금·대출·신용보증·고용지원·교육컨설팅)
  - `SeoulCommercialPlugin` — 지역·업종별 상권 데이터 조회
- **동작**: 식품위생법 기반 영업신고 절차 단계별 안내 + 창업자 상황 맞춤 정부지원사업 추천
- **출력 기준**: 관할 기관(시·군·구청 위생과) 명시, 처리 기한(3~7영업일) 포함
- **문서 생성**: `/api/v1/doc/chat` 엔드포인트에서 `FoodBusinessPlugin`(BusinessDoc)을 통해 대화형으로 정보 수집 후 식품영업신고서 PDF 출력 (Sign-off 바이패스, 별도 kernel)

---

## 프로젝트 성과

### 프로젝트 기간 (2026-02-25 ~ 2026-04-10)

| 지표 | 수치 |
| ---- | ---- |
| 총 커밋 | 770건 (non-merge 575건) |
| Pull Request (merged) | 255건 |
| AI 에이전트 | 5개 (행정·재무·법률·상권·안내) |
| Sign-off 루브릭 코드 | 4계층 33개 |
| 정부지원사업 RAG 데이터 | 5,600건+ |
| 몬테카를로 시뮬레이션 | 10,000회/요청 |
| 응답 레이턴시 개선 | -63.6% (avg 32.7s → 11.9s) |
| 일일 개발 요약 | 81건 |
| 플랜 문서 | 114건 |
| 세션 인수인계 | 48건 |

> GitHub 저장소에 표시되는 총 커밋 수(현재 776)는 이후 유지보수 커밋과 merge 커밋을 포함한 누적 합계입니다. 위 표는 프로젝트 종료일 기준 스냅샷입니다.

### 프로젝트 후 유지보수 (2026-04-11 ~ )

| 지표 | 수치 |
| ---- | ---- |
| 추가 커밋 | 9건 |
| 추가 PR (merged) | 5건 |
| 주요 작업 | 린트 도구 도입 (Ruff·Prettier·pre-commit), axios 공급망 공격 대응·의존성 핀 |

---

## 주요 기능

### AI 에이전트

- **법령 RAG** — 생활법령정보 기반 검색 증강 생성으로 최신 법규 정확 인용
- **상권 분석** — 서울 2024 Q4 데이터 기반 매출 현황, 시간대·성별·연령대별 분석, 유사 상권 추천
- **재무 시뮬레이션** — 몬테카를로 10,000회 기반 창업 리스크 수치 분석 및 히스토그램 차트 반환
- **정부지원사업 추천** — 창업자 상황 맞춤 보조금·대출·신용보증·고용지원 하이브리드 검색 (5,600+건)
- **행정 서류 자동 생성** — 대화형 정보 수집 후 식품영업신고서 PDF 출력
- **Sign-off 검증** — 응답 품질 사후 평가 (grade A/B/C), 기준 미달 시 최대 3회 재처리

### 프론트엔드

- **인터랙티브 지도** — OpenLayers 기반 서울 행정동 상권 지도 (업종별 점포, 매출, 인구, 지적도, 공시지가 레이어)
- **창업 체크리스트** — 8개 항목(업종 결정~임대차계약) 자동 진행률 추적, 에이전트 답변 기반 자동 체크
- **재무 시뮬레이션 차트** — Monte Carlo 히스토그램 (손실/위험/수익 구간 시각화)
- **SSE 스트리밍** — 에이전트 응답 실시간 표시
- **사용자 인증** — Google OAuth 로그인, 세션별 대화 이력 관리
- **로드맵 투표** — 사용자가 원하는 기능에 투표, 개발 우선순위 반영
- **My Report** — 세션 통계, 에이전트 사용 분석, 체크리스트 기반 추천
- **My Logs** — 인증된 사용자의 과거 세션 이력 열람

### 개발자 도구

- **DevChat** — Sign-off 검증 상세 (등급, 루브릭 결과, 재시도 이력) 실시간 확인
- **LogViewer** — 에이전트 처리 과정 JSONL 로그 조회
- **StatsPage** — 에이전트별 레이턴시, 등급 분포, 에러율 모니터링 대시보드
- **Changelog** — GitHub 커밋 히스토리 자동 표시

---

## 기술 스택

### 백엔드 (`backend/`)

| 분류 | 기술 |
|------|------|
| AI 오케스트레이션 | Semantic Kernel 1.41.1 |
| AI 모델 플랫폼 | Azure AI Foundry (GPT-4o) |
| API 서버 | FastAPI 0.135 + Uvicorn 0.42 |
| RAG 파이프라인 | Azure AI Search 11.6 |
| 세션 저장소 | Azure Cosmos DB |
| 로그 저장소 | Azure Blob Storage |
| 상권 DB | Azure PostgreSQL Flexible Server |
| PDF 생성 | ReportLab 4.4 + pdfkit + Jinja2 3.1 |
| 재무 시각화 | Matplotlib 3.10 + NumPy 2.4 |
| 인증 | Authlib 1.3 + python-jose (JWT) |
| Rate Limiting | slowapi 0.1.9 |
| 배포 | Azure Container Apps + GitHub Actions CI/CD |

### 프론트엔드 (`frontend/`)

| 분류 | 기술 |
|------|------|
| UI 프레임워크 | React 19 + Vite 7 |
| 스타일링 | Tailwind CSS 4 |
| 라우팅 | React Router DOM 7 |
| 지도 | OpenLayers 10.8 + Turf.js 7.3 |
| 차트 | Chart.js 4.5 |
| 마크다운 렌더링 | react-markdown 10 + remark-gfm |
| UI 컴포넌트 | Radix UI (select, tabs, collapsible, tooltip 등) |
| 애니메이션 | Motion 12.38 (Framer Motion) |
| HTTP 클라이언트 | Axios 1.15 |
| SEO | react-helmet-async, JSON-LD, sitemap |
| 호스팅 | Azure Static Web Apps |

---

## API 엔드포인트

### 핵심 API (`api_server.py`)

| 메서드 | 경로 | 설명 |
| ------ | ---- | ---- |
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/v1/query` | 자연어 질문 → 에이전트 처리 → Sign-off |
| `POST` | `/api/v1/stream` | SSE 스트리밍 응답 |
| `POST` | `/api/v1/signoff` | draft 단독 Sign-off 검증 |
| `POST` | `/api/v1/doc/chat` | 문서 생성 대화 (식품영업신고서 PDF) |
| `GET` | `/api/v1/stats` | 에이전트별 레이턴시·등급 통계 |
| `GET` | `/api/v1/logs` | JSONL 로그 조회 |
| `GET` | `/api/v1/logs/export` | 로그 내보내기 |
| `GET` | `/api/v1/logs/users` | 사용자별 로그 조회 |
| `GET` | `/api/v1/my-ip` | 클라이언트 IP 확인 (rate limit 면제 IP 등록용) |
| `GET` | `/wms/{path:path}` | VWorld WMS 프록시 (프론트엔드 지도 타일용) |

### 라우터 모듈

| 라우터 | 경로 접두사 | 설명 |
| ------ | ----------- | ---- |
| `auth_router` | `/auth` | Google OAuth 로그인/콜백 |
| `my_router` | `/my` | 사용자 세션·이력 관리 |
| `map_router` | `/map` | 지도 타일·행정동 데이터 |
| `map_data_router` | `/map-data` | 상권 상세 데이터 (점포, 매출, 인구) |
| `realestate_router` | `/realestate` | 부동산 시세·공시지가 |
| `feedback_router` | `/feedback` | 사용자 피드백 수집 |
| `event_router` | `/event` | 이벤트 트래킹 |
| `checklist_router` | `/checklist` | 창업 체크리스트 CRUD |
| `report_router` | `/report` | 세션 리포트 생성 |
| `roadmap_router` | `/roadmap` | 로드맵 기능 투표 |

---

## 프론트엔드 페이지

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | Landing | 랜딩 페이지 (제품 소개, CTA) |
| `/home` | Home | 모드 선택 (사용자/지도/개발자) |
| `/user` | UserChat | 메인 AI 채팅 인터페이스 + 체크리스트 |
| `/map` | MapPage | 인터랙티브 서울 상권 지도 |
| `/features` | Features | 기능 상세 소개 |
| `/my-report` | MyReport | 세션 통계·에이전트 사용 분석 |
| `/my-logs` | MyLogs | 과거 세션 이력 (인증 필요) |
| `/roadmap` | Roadmap | 기능 로드맵 + 투표 |
| `/changelog` | Changelog | Git 커밋 히스토리 |
| `/privacy` | PrivacyPolicy | 개인정보처리방침 |
| `/auth/callback` | AuthCallback | OAuth 콜백 |
| `/dev/login` | DevLogin | 개발자 인증 |
| `/dev` | DevChat | 개발자 디버그 채팅 (인증 필요) |
| `/dev/logs` | LogViewer | 에이전트 로그 뷰어 (인증 필요) |
| `/dev/stats` | StatsPage | 성능 모니터링 대시보드 (인증 필요) |

---

## 디렉토리 구조

```text
SOHOBI/
├── backend/              # 메인 통합 백엔드
│   ├── api_server.py             # FastAPI 진입점
│   ├── orchestrator.py           # Semantic Kernel 오케스트레이션
│   ├── domain_router.py          # 질문 → 에이전트 라우팅
│   ├── kernel_setup.py           # Semantic Kernel 초기화
│   ├── session_store.py          # Cosmos DB 세션 관리 (LRU 폴백)
│   ├── auth.py / auth_router.py  # OAuth 인증
│   ├── my_router.py              # 사용자 세션·이력 API
│   ├── map_router.py             # 지도 타일·행정동 API
│   ├── map_data_router.py        # 상권 상세 데이터 API
│   ├── realestate_router.py      # 부동산·공시지가 API
│   ├── checklist_router.py       # 체크리스트 CRUD
│   ├── feedback_router.py        # 사용자 피드백
│   ├── report_router.py          # 세션 리포트
│   ├── roadmap_router.py         # 로드맵 투표
│   ├── event_router.py           # 이벤트 트래킹
│   ├── variable_extractor.py     # 재무 변수 자동 추출 (백그라운드)
│   ├── security_logging.py       # 보안 이벤트 로거
│   ├── agents/                   # 하위 에이전트
│   │   ├── chat_agent.py         # 안내 (Sign-off 바이패스)
│   │   ├── legal_agent.py        # 법률·세무
│   │   ├── location_agent.py     # 상권 분석
│   │   ├── finance_agent.py      # 재무 시뮬레이션
│   │   └── admin_agent.py        # 행정 서류
│   ├── signoff/                  # Sign-off 검증 에이전트
│   ├── db/                       # CommercialRepository (Azure PostgreSQL)
│   ├── prompts/                  # 도메인별 Sign-off 루브릭
│   ├── plugins/                  # Semantic Kernel 플러그인
│   ├── scripts/                  # 분석 스크립트 (analyze_logs.py 등)
│   ├── chart/                    # 차트 생성 유틸리티
│   └── requirements.txt
├── frontend/                     # React + Vite 프론트엔드
│   └── src/
│       ├── pages/                # 15개 페이지 컴포넌트
│       ├── components/           # 공통 UI 컴포넌트
│       │   ├── checklist/        # 체크리스트 컴포넌트
│       │   ├── feedback/         # 피드백 컴포넌트
│       │   ├── layout/           # 레이아웃 컴포넌트 (MyPageLayout, EmptyStateCTA)
│       │   ├── map/              # 지도 컴포넌트 (레이어, 패널, 팝업)
│       │   ├── report/           # 리포트 컴포넌트
│       │   └── ui/               # Radix UI 기반 공통 UI
│       ├── hooks/                # 커스텀 훅 (chat/, map/)
│       ├── contexts/             # React Context (AuthContext 등)
│       ├── config/               # 환경별 API URL·설정
│       ├── constants/            # 도메인 키워드 등 상수
│       ├── utils/                # 범용 유틸리티
│       ├── lib/                  # 외부 라이브러리 래퍼
│       ├── data/                 # 정적 데이터
│       ├── styles/               # 전역 스타일
│       └── assets/               # 이미지·아이콘
├── docs/                         # → docs/README.md 참조
│   ├── architecture/             # Mermaid 아키텍처 다이어그램 (HTML 7개)
│   ├── dev-summary/              # 팀원별 일일 개발 요약 (81건)
│   ├── guides/                   # 운영 가이드 (로그 조회, 인프라 등)
│   ├── plans/                    # 설계·분석 플랜 문서 (116건)
│   ├── session-reports/          # 세션 인수인계 리포트 (48건)
│   └── test-reports/             # 보안 테스트·성능 베이스라인 리포트
├── .github/workflows/            # CI/CD (프론트 배포, 백엔드 배포, 스모크 테스트)
└── CLAUDE.md                     # Claude Code 영구 지시
```

---

## 로컬 실행

### 사전 요구사항

- Python 3.12
- Node.js 18+
- `.env` 파일 (Azure API 키 등)

### 백엔드

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
.venv/bin/python3 api_server.py    # http://localhost:8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev                        # http://localhost:3000
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

## 개발 도구

### 린트 & 포맷

| 대상 | 도구 | 명령 |
|------|------|------|
| Python | Ruff | `ruff check --fix backend/` |
| Python | Ruff Format | `ruff format backend/` |
| JS/CSS | Prettier | `cd frontend && npx prettier --write src/` |
| JS | ESLint | `cd frontend && npx eslint --fix src/` |

### pre-commit 훅

최초 1회 설치:

```bash
pip install pre-commit
pre-commit install
```

이후 커밋 시 Ruff·Prettier가 자동 실행됩니다. 설정 파일:

- `pyproject.toml` — Ruff 규칙 (target: Python 3.12)
- `frontend/.prettierrc` — Prettier 포맷 규칙
- `frontend/eslint.config.js` — ESLint 규칙
- `.pre-commit-config.yaml` — 훅 설정

---

## 성능 지표

5단계 체계적 최적화를 통해 전체 응답 레이턴시 **63.6% 감소**를 달성했습니다.

### 응답 시간 (Before → After)

| 지표 | Before (n=532) | After (n=416) | 개선율 |
|------|----------------|---------------|--------|
| 전체 avg | 32.7s | 11.9s | **-63.6%** |
| p90 | 68.2s | 21.2s | **-68.9%** |
| max | 612.0s | 64.2s | **-89.5%** |
| 상권분석 avg | 46.5s | 11.2s | **-75.9%** |

### 품질 등급 (최적화 후 100건)

| 에이전트 | 승인률 | Grade A |
|----------|--------|---------|
| 행정 (admin) | 100% | 84% |
| 대화 (chat) | 100% | 100% |
| 재무 (finance) | 100% | 100% |
| 상권 (location) | 96% | 92% |

---

## 배포 환경

| 구성 요소 | 서비스 |
|-----------|--------|
| 백엔드 | Azure Container Apps |
| 프론트엔드 | Azure Static Web Apps |
| 도메인 | sohobi.net (Azure DNS) |
| CI/CD | GitHub Actions (main push 시 자동 배포) |
| 인증 | Google OAuth + Azure Entra ID (개발자) |

---

## 설계 원칙

- MVP 범위: **서울 기반 F&B 업종** → 이후 전국 및 타 업종으로 확장 예정
- 에이전트 간 정보 공유는 Semantic Kernel 기반 구조적 처리
- 의존성 버전은 `==`으로 고정하여 재현성 보장 (Python 3.12)
- `.env` 파일에 Azure API 키 포함 — 절대 커밋 금지
