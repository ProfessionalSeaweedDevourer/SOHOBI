# SOHOBI-EJP: AI 에이전트 응답 품질보증 시스템

소호비즈니스(SOHO) 도메인 — 행정·재무·법률 — 에서 AI 에이전트가 생성한 답변을 자동으로 평가하고 재시도하는 **Sign-off(결재) 파이프라인**입니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [디렉터리 구조](#2-디렉터리-구조)
3. [핵심 기능](#3-핵심-기능)
4. [동원된 기술](#4-동원된-기술)
5. [파일별 역할 요약](#5-파일별-역할-요약)
6. [평가 루브릭 (Sign-off 코드)](#6-평가-루브릭-sign-off-코드)
7. [환경 설정 및 실행 방법](#7-환경-설정-및-실행-방법)
8. [한계 및 발전 방향](#8-한계-및-발전-방향)
9. [수정 기록](#9-수정-기록)

---

## 1. 프로젝트 개요

```
[사용자 질문]
      │
      ▼
[Orchestrator]  ─── 도메인 라우팅 (admin / finance / legal)
      │
      ▼
[Sub-Agent]     ─── 초안(draft) 생성 (Azure OpenAI gpt-4o-mini)
      │
      ▼
[Sign-off Agent] ── 도메인별 루브릭으로 초안 평가 (Azure OpenAI gpt-4o-mini)
      │
   approved?
   ┌──┴──┐
  YES    NO  ──► retry_prompt → Sub-Agent 재생성 (최대 3회)
   │              └─ 3회 초과 → ESCALATED (인간 검토 요청)
   ▼
[최종 응답 반환]
```

목표: 소상공인 대상 AI 챗봇의 응답 품질을 **법령 인용·절차 기술·리스크 경고·면책 고지** 등 도메인별 기준으로 자동 검증하고, 기준 미달 응답은 자동 재생성합니다.

---

## 2. 디렉터리 구조

```
SOHOBI-EJP/
├── README.md                          ← 이 파일
└── Code_EJP/
    ├── .env                           ← 자격증명 (Git 제외)
    ├── .env.example                   ← 환경변수 템플릿
    ├── .gitignore
    │
    ├── kernel_setup.py                ← Azure OpenAI Semantic Kernel 초기화
    ├── orchestrator.py                ← 전체 워크플로 조율
    │
    ├── agents/
    │   ├── __init__.py
    │   ├── admin_agent.py             ← 행정·인허가 답변 생성
    │   ├── finance_agent.py           ← 재무 시뮬레이션 답변 생성
    │   └── legal_agent.py             ← 법률 정보 답변 생성
    │
    ├── prompts/
    │   ├── signoff_admin/evaluate/
    │   │   ├── skprompt.txt           ← 행정 도메인 평가 프롬프트
    │   │   └── config.json
    │   ├── signoff_finance/evaluate/
    │   │   ├── skprompt.txt           ← 재무 도메인 평가 프롬프트
    │   │   └── config.json
    │   └── signoff_legal/evaluate/
    │       ├── skprompt.txt           ← 법률 도메인 평가 프롬프트
    │       └── config.json
    │
    ├── step3_domain_signoff.py        ← Sign-off 엔진 (핵심 모듈)
    ├── step3_domain_signoff_enhanced.py ← PASS/FAIL 이중 테스트 스위트
    │
    ├── step2a_connect_modeltest.py    ← Azure OpenAI 연결 스모크 테스트
    ├── step2b_signoff_test.py         ← Sign-off 로직 단독 테스트
    ├── integration_test.py            ← 오케스트레이터 전체 통합 테스트
    └── OUTDATED_demo_step3.py         ← 폐기된 초기 데모 (비활성)
```

---

## 3. 핵심 기능

### 3-1. 도메인별 서브-에이전트 (초안 생성)

| 에이전트 | 대상 도메인 | 핵심 생성 요건 |
|---|---|---|
| `AdminAgent` | 행정·인허가 절차 | 법령 조문 번호, 서류명, 처리기관, 처리기간 |
| `FinanceAgent` | 재무 분석·시뮬레이션 | 수치·단위(원/%), 가정 명시, 낙관/기준/비관 시나리오, 리스크 경고 |
| `LegalAgent` | 법률 정보 제공 | 면책 고지, 법령 시점 기준 명시, 전문가 상담 권고, 법령 조문 |

- 모든 에이전트는 **`retry_prompt`** 파라미터를 수신해 Sign-off 거절 시 지적 사항을 반영한 재생성이 가능합니다.
- 생성 온도: **0.3** (사실 일관성 우선)

### 3-2. Sign-off 에이전트 (자동 품질 평가)

- 도메인별 루브릭(`C1–C5` 공통 + `A1–A5` / `F1–F5` / `G1–G4` 도메인별)을 적용해 초안을 평가합니다.
- 평가 결과를 **JSON 형식**으로 반환합니다.

```json
{
  "passed": ["C1", "C2", "C4", "A1", "A3"],
  "issues": ["C3", "A2", "A5"],
  "approved": false,
  "retry_prompt": "처리기관명과 처리기간이 누락되었습니다. 해당 정보를 추가하여 재작성하십시오."
}
```

- 평가 코드가 누락되거나 `passed`/`issues` 중복 분류 시 내부 재시도를 수행합니다.
- 평가 온도: **0.0** (결정론적 판정)

### 3-3. Orchestrator (워크플로 관리)

- 질문 도메인을 자동으로 라우팅합니다.
- 최대 **3회** 재시도 후 `ESCALATED` 상태로 상위 처리자에게 에스컬레이션합니다.
- 전체 거절 이력(`rejection_history`)과 재시도 횟수(`retry_count`)를 포함한 감사 로그를 반환합니다.

```python
result = {
    "status": "APPROVED" | "ESCALATED",
    "retry_count": int,
    "request_id": str,
    "draft": str,
    "rejection_history": [{"attempt": int, "issues": [...], "retry_prompt": str}]
}
```

### 3-4. 테스트 체계

| 파일 | 목적 |
|---|---|
| `step2a_connect_modeltest.py` | Azure OpenAI 엔드포인트 연결 스모크 테스트 |
| `step2b_signoff_test.py` | Sign-off 평가 로직 단독 검증 |
| `step3_domain_signoff_enhanced.py` | PASS 기대 케이스 / FAIL 기대 케이스 이중 실행 |
| `integration_test.py` | 정상 질문(3종) + 의도적 부실 질문(3종) 전체 통합 테스트 |

---

## 4. 동원된 기술

### 언어 및 런타임
- **Python 3.x** — 전체 구현
- `asyncio` / `async-await` — 비동기 LLM 호출 패턴

### AI·LLM 인프라
| 기술 | 용도 |
|---|---|
| **Azure OpenAI Service** | LLM 백엔드 (gpt-4o-mini / gpt-4o) |
| **Microsoft Semantic Kernel (Python SDK)** | 커널 초기화, 프롬프트 함수 등록, ChatHistory 관리 |
| `AzureChatCompletion` | Semantic Kernel ↔ Azure OpenAI 연결 서비스 |
| `@kernel_function` 데코레이터 | 에이전트 메서드를 SK 플러그인 함수로 등록 |

### 프롬프트 엔지니어링
- **Semantic Kernel Prompt Template** (`skprompt.txt` + `config.json`) — 도메인별 평가 루브릭을 외부 파일로 분리 관리
- **JSON 응답 형식 강제** (`response_format: json_object`) — 구조화된 평가 결과 보장
- **XML 스타일 메시지 태그** (`<system>`, `<user>`, `<assistant>`) — 프롬프트 파일 내 ChatHistory 직렬화

### 환경 관리
- **python-dotenv** — `.env` 파일 기반 자격증명 주입
- **Git + .gitignore** — 자격증명 파일 버전 관리 제외

---

## 5. 파일별 역할 요약

| 파일 | 역할 | 주요 함수/클래스 |
|---|---|---|
| `kernel_setup.py` | SK 커널 생성 및 Azure OpenAI 등록 | `get_kernel()` |
| `orchestrator.py` | 도메인 라우팅 + 재시도 루프 | `run(domain, question)` |
| `agents/admin_agent.py` | 행정 초안 생성 | `AdminAgent.generate_draft()` |
| `agents/finance_agent.py` | 재무 초안 생성 | `FinanceAgent.generate_draft()` |
| `agents/legal_agent.py` | 법률 초안 생성 | `LegalAgent.generate_draft()` |
| `step3_domain_signoff.py` | Sign-off 평가 엔진 (핵심) | `run_signoff()`, `validate_verdict()` |
| `step3_domain_signoff_enhanced.py` | PASS/FAIL 이중 테스트 스위트 | `run_suite()`, `main()` |
| `step2a_connect_modeltest.py` | 연결 스모크 테스트 | `main()` |
| `step2b_signoff_test.py` | Sign-off 단독 테스트 | `run_signoff()`, `validate_verdict()` |
| `integration_test.py` | 전체 통합 테스트 | `run_tests(mode)` |
| `prompts/signoff_*/evaluate/skprompt.txt` | 도메인별 평가 루브릭 정의 | — |
| `prompts/signoff_*/evaluate/config.json` | 평가 모델 파라미터 (temp=0.0) | — |

---

## 6. 평가 루브릭 (Sign-off 코드)

### L1 공통 코드 (전 도메인)
| 코드 | 평가 항목 |
|---|---|
| C1 | 질문에 대한 직접적 응답 여부 |
| C2 | 응답 완결성 (중간 절단 없음) |
| C3 | 내부 일관성 (직접적 모순 부재) |
| C4 | 전문적 어조 유지 |
| C5 | 할루시네이션 징후 부재 (단정적 허위 진술 한정) |

### L2 행정 도메인 (A1–A5)
| 코드 | 평가 항목 |
|---|---|
| A1 | 관련 법령/조항 번호 인용 |
| A2 | 필요 서류·양식명 언급 |
| A3 | 절차의 단계별 기술 |
| A4 | 담당 기관명 명시 (구청, 시청 등) |
| A5 | 처리 기한/소요 기간 정보 포함 |

### L2 재무 도메인 (F1–F5)
| 코드 | 평가 항목 |
|---|---|
| F1 | 수치 데이터 제시 (금액, 비율 등) |
| F2 | 단위·통화 명시 (원, %, USD 등) |
| F3 | 계산 가정 명시 (금리, 자본 구조 등) |
| F4 | 불확실성 인정 (시나리오, 신뢰구간 등) |
| F5 | 리스크 경고 포함 (원금 손실 가능성 등) |

### L2 법률 도메인 (G1–G4)
| 코드 | 평가 항목 |
|---|---|
| G1 | 면책 고지 포함 ("법적 조언이 아닌 일반 정보") |
| G2 | 법령 시점 기준 명시 (변경 가능성 고지) |
| G3 | 전문가·법률구조공단 상담 권고 |
| G4 | 법령/조문 번호 인용 |

---

## 7. 환경 설정 및 실행 방법

### 사전 요건
- Python 3.10+
- Azure OpenAI 리소스 (배포 완료된 `gpt-4o-mini`, 선택적으로 `gpt-4o`)

### 설치

```bash
pip install semantic-kernel python-dotenv
```

### 환경변수 설정

```bash
cp Code_EJP/.env.example Code_EJP/.env
# .env 파일에 실제 자격증명 입력
```

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_DEPLOYMENT_NAME=gpt-4o-mini

# Enhanced 스크립트 전용 (선택)
AZURE_ENHANCED_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_ENHANCED_DEPLOYMENT_NAME=gpt-4o
```

### 실행

```bash
cd Code_EJP

# 1. 연결 테스트
python step2a_connect_modeltest.py

# 2. Sign-off 단독 테스트
python step2b_signoff_test.py

# 3. 도메인별 Sign-off (PASS/FAIL 이중)
python step3_domain_signoff_enhanced.py both

# 4. 전체 통합 테스트
python integration_test.py all
```

---

## 8. 한계 및 발전 방향

### 현재 한계

| 구분 | 내용 |
|---|---|
| **도메인 라우팅** | 도메인 분류를 외부에서 수동으로 지정해야 함. 자동 도메인 감지 로직 미구현. |
| **루브릭 정적 운영** | 법령 개정·서비스 정책 변경 시 프롬프트 파일을 수동으로 수정해야 함. |
| **단일 평가 모델** | Sign-off 에이전트가 단일 LLM에 의존. 모델 오류·편향에 취약. |
| **재시도 한계** | 최대 3회 재시도 후 에스컬레이션만 가능. 자동 수정 범위가 제한적. |
| **비용 추적 없음** | 토큰 사용량·API 비용 모니터링 기능 미구현. |
| **한국어 특화** | 현재 한국어 소상공인 도메인에만 최적화되어 있으며 다국어 확장 미지원. |
| **응답 캐싱 없음** | 동일 질문에 대해 매번 LLM 호출 발생. |
| **비동기 병렬화 제한** | 오케스트레이터 내 에이전트 호출이 순차적. |

### 발전 방향

#### 단기 개선 (기능 보강)
- **자동 도메인 분류기** 추가: 사용자 질문 텍스트로부터 `admin`/`finance`/`legal` 자동 판별
- **토큰 사용량 로깅**: 비용 모니터링 및 최적화 기반 마련
- **응답 캐시 레이어**: 유사 질문에 대한 결과 재사용 (semantic similarity 기반)
- **루브릭 버전 관리**: `config.json`에 루브릭 버전 필드 추가, 변경 이력 추적

#### 중기 개선 (아키텍처 확장)
- **멀티-에이전트 병렬 초안 생성**: 복수 초안 생성 후 최적 초안 선택
- **이중 Sign-off 검증**: 두 개의 독립적 평가 모델 동의 시 승인 (ensemble evaluation)
- **웹훅·API 서버화**: FastAPI/Flask 기반 HTTP 엔드포인트로 서비스화
- **데이터베이스 연동**: 요청·평가 이력 영속화 (PostgreSQL, MongoDB 등)
- **능동적 루브릭 학습**: 인간 검토자 피드백을 루브릭 자동 개선에 반영

#### 장기 개선 (서비스 고도화)
- **도메인 확장**: 세무, 노무, 보험 도메인 추가
- **RAG(Retrieval-Augmented Generation) 연동**: 최신 법령·판례 DB 실시간 참조
- **사용자 피드백 루프**: 최종 사용자 만족도를 Sign-off 루브릭 가중치에 반영
- **설명 가능성(XAI)**: 평가 코드별 근거 텍스트(evidence snippet) 추출 및 제공
- **다국어 지원**: 영어·중국어 등 다국어 소상공인 서비스 대응

---

## 9. 수정 기록

| 날짜 | 버전 | 변경 내용 | 관련 파일 |
|---|---|---|---|
| 2026-03-10 | v0.1.0 | 초기 업로드: 3개 서브-에이전트, Sign-off 엔진, Orchestrator, 통합 테스트 일괄 등록 | 전체 |
| 2026-03-09 | v0.1.0 | `OUTDATED_demo_step3.py` 폐기 표시 (파일 유지, 비활성) | `OUTDATED_demo_step3.py` |
| 2026-03-09 | v0.1.0 | `step3_domain_signoff_enhanced.py` 추가: PASS/FAIL 이중 테스트 케이스 및 Enhanced 모델 지원 | `step3_domain_signoff_enhanced.py`, `.env.example` |
| 2026-03-09 | — | Orchestrator 내 `approved=false`이나 `issues` 없는 엣지케이스 강제 승인 처리 추가 | `orchestrator.py` |
| 2026-03-09 | — | Sign-off 평가 루브릭 C3(내부 일관성) 기준 명확화: 직접 모순에 한정, 입장 차이 제외 | `prompts/signoff_*/evaluate/skprompt.txt` |
| 2026-03-09 | — | Sign-off 평가 루브릭 C5(할루시네이션) 기준 명확화: 단정적 허위 진술에 한정 | `prompts/signoff_*/evaluate/skprompt.txt` |
| 2026-03-10 | — | Sign-off 루브릭 C2: 짧은 완결 응답 통과 예시 추가 (false positive 억제) | `prompts/signoff_*/evaluate/skprompt.txt` |
| 2026-03-10 | — | Sign-off 루브릭 C3: "의심만으로 issues 금지" 명시 추가 (내부 재시도 반복 억제) | `prompts/signoff_*/evaluate/skprompt.txt` |
| 2026-03-10 | — | Sign-off 루브릭 F5: 리스크 부정·축소 표현 경고 불인정 조건 추가 (`'원금 손실 없이'` false pass 차단) | `prompts/signoff_finance/evaluate/skprompt.txt` |
| 2026-03-10 | — | Sign-off 루브릭 G1·G2: 부재 판별 예시 추가 (미발동 방지) | `prompts/signoff_legal/evaluate/skprompt.txt` |
| 2026-03-10 | — | Sign-off 루브릭 G4: 통과 예시 추가 (false negative 방지) | `prompts/signoff_legal/evaluate/skprompt.txt` |
| 2026-03-10 | — | `MOCK_DRAFTS['finance']` 수정: `'원금 손실 없이'` → `'반드시 안정적인 수익'` (C5 트리거, F5 명백 부재) | `step3_domain_signoff.py` |
| 2026-03-10 | — | `integration_test.py` 에스컬레이션 경로 재설계: 서브-에이전트 대신 고정 실패 draft를 Sign-off에 직접 반복 투입 | `integration_test.py` |

---

*최종 업데이트: 2026-03-10*
