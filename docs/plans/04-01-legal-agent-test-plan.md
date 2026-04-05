# 법령 에이전트 테스트 계획

## Context
`legal_agent.py`와 `legal_search_plugin.py`는 Azure AI Search 기반 법령 RAG 검색을 수행하는 핵심 에이전트입니다.
코드 탐색 결과 단위/통합 테스트가 전혀 없으며, 다음 문제들이 발견됨:
- async/sync 혼재
- 파라미터 검증 부재
- 예외 처리 불충분
- LLM 도구 호출 강제 불가
- 초기화 실패 처리 없음

목표: 각 문제를 드러낼 수 있는 테스트 목록 작성 및 구현

테스트 구현 위치:
- `integrated_PARK/tests/test_legal_search_plugin.py` — T-01~T-08
- `integrated_PARK/tests/test_legal_agent.py` — T-09~T-16
- `integrated_PARK/tests/test_signoff_legal.py` — T-17~T-19
- `integrated_PARK/tests/test_legal_e2e.py` — T-20~T-24

---

## 발견된 주요 버그 및 문제점

### 🔴 Critical
1. **top_k 파라미터 미검증** (`legal_search_plugin.py:56,73`) — 음수/0 입력 시 Azure API 오류
2. **AzureOpenAI 초기화 예외 처리 없음** (`legal_search_plugin.py:35-39`) — `__init__` 실패 시 플러그인 등록 전체 실패
3. **`get_service("sign_off")` 실패 처리 없음** (`legal_agent.py:73`) — 서비스 미등록 시 AttributeError
4. **prior_history dict 접근 KeyError 위험** (`legal_agent.py:83-86`) — `msg["role"]`, `msg["content"]` 에 `.get()` 미사용

### 🟠 High
5. **async/sync 혼재** — `generate_draft`(async)가 `search_legal_docs`(sync)를 FunctionChoiceBehavior로 호출 → eventloop 블로킹 가능
6. **LLM 도구 미호출 위험** — `FunctionChoiceBehavior.Auto()` 사용 시 LLM이 RAG 도구를 무시하고 일반 지식으로 답변 가능
7. **예외 정보 노출** — `return f"법령 검색 오류: {e}"` 에서 내부 에러 상세 정보 사용자에게 노출

### 🟡 Medium
8. **search_text=None 의도 불명확** (`legal_search_plugin.py:69`) — 순수 벡터 검색 의도이나 주석 없음
9. **프롬프트 순서 문제** (`legal_agent.py:74-77`) — RETRY_PREFIX가 SYSTEM_PROMPT 앞에 위치, 재시도 효과 저하 가능
10. **SearchDocument 필드 처리** (`legal_search_plugin.py:81-82`) — 검색 결과 개수 표시 없음

---

## 테스트 목록 (T-01 ~ T-24)

### [플러그인 단위 테스트] T-01~T-08

| ID | 제목 | 분류 | 현재 상태 |
|----|------|------|----------|
| T-01 | 환경변수 미설정 시 _available=False, 안전 메시지 반환 | 정상 동작 확인 | 정상 |
| T-02 | top_k=0 입력 시 Azure API 오류 재현 | **버그 재현** | 버그 |
| T-03 | top_k 음수 입력 시 Azure API 오류 재현 | **버그 재현** | 버그 |
| T-04 | 검색 결과 0건일 때 "관련 법령 없음" 반환 | 정상 동작 확인 | 정상 |
| T-05 | 일반 법령 키워드 검색 Happy Path | 정상 동작 확인 | 정상 |
| T-06 | 빈 쿼리 문자열 입력 시 동작 | 엣지 케이스 | 미검증 |
| T-07 | 잘못된 엔드포인트로 초기화 실패 시 처리 | **버그 재현** | 버그 |
| T-08 | SearchDocument 필드 누락 시 안전 처리 | 정상 동작 확인 | 정상 |

### [에이전트 단위 테스트] T-09~T-16

| ID | 제목 | 분류 | 현재 상태 |
|----|------|------|----------|
| T-09 | prior_history=None 전달 시 정상 처리 | 정상 동작 확인 | 정상 |
| T-10 | prior_history content 키 누락 시 KeyError | **버그 재현** | 버그 |
| T-11 | prior_history 알 수 없는 role은 무시됨 | 정상 동작 확인 | 정상 |
| T-12 | retry_prompt+profile 동시 사용 시 프롬프트 순서 | 품질 검증 | 개선 가능 |
| T-13 | "sign_off" 서비스 미등록 시 AttributeError | **버그 재현** | 버그 |
| T-14 | 동일 kernel에 플러그인 중복 등록 방지 | 정상 동작 확인 | 정상 |
| T-15 | FunctionChoiceBehavior.Auto() — 도구 실제 호출 여부 | **핵심 검증** | 미검증 |
| T-16 | 단순 인사말 입력 시 응답 | 엣지 케이스 | 미검증 |

### [Sign-off 연계] T-17~T-19

| ID | 제목 | 분류 | 기대 결과 |
|----|------|------|----------|
| T-17 | 법령명 미인용 시 G4 → issues | Sign-off 검증 | approved=false |
| T-18 | 면책조항 미포함 시 G1 → issues | Sign-off 검증 | approved=false |
| T-19 | 완전한 응답에서 G1~G4 모두 통과 | Happy Path | approved=true |

### [통합/E2E] T-20~T-24

| ID | 제목 | 분류 |
|----|------|------|
| T-20 | /api/v1/query legal 도메인 E2E | 통합 |
| T-21 | 재시도 루프 — retry_prompt 반영 확인 | 통합 |
| T-22 | prior_history 포함 시 맥락 반영 | 통합 |
| T-23 | 프롬프트 인젝션 시도 거부 | 보안 |
| T-24 | 에러 메시지 내 민감 정보 노출 없음 | 보안 |

---

## 우선순위 실행 순서

1. **T-02, T-03** — top_k 검증 (재현 쉬움, 즉시 수정 가능)
2. **T-07, T-13** — 초기화/서비스 미등록 (Critical)
3. **T-10** — prior_history KeyError (재현 가능)
4. **T-15** — 도구 호출 여부 (가장 중요한 기능)
5. **T-17~T-19** — Sign-off 연계 품질 확인
6. **T-20** — 전체 파이프라인 E2E
