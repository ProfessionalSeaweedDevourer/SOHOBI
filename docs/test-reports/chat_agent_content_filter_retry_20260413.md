# ChatAgent content_filter 재시도 단위 테스트 결과

## 메타데이터

| 항목 | 내용 |
|---|---|
| 문서 버전 | v1 |
| 실행 일시 | 2026-04-13 |
| 실행자 | Claude Code |
| 대상 PR | #298 (MERGED, `5fc8964`) + #(pytest-asyncio 편입 PR) |
| 대상 파일 | `backend/agents/chat_agent.py`, `backend/tests/test_chat_injection.py` |
| 실행 환경 | macOS 14 (darwin 24.6.0), Python 3.12, pytest 9.0.2 + pytest-asyncio 1.3.0, Azure LLM 미호출 (mock) |

---

## 1. 결과 요약

| 판정 | 수 | 케이스 |
|---|---|---|
| PASS | 2 | T-CA-INJ-01, T-CA-INJ-02 |
| FAIL | 0 | — |

회귀 확인: `tests/test_location_agent.py::TestCallLlm::test_13_content_filter_retry_includes_user_msg` PASS (T-LA-13, 기존 LocationAgent 재시도 계약 유지)

---

## 2. 테스트 케이스

### T-CA-INJ-01 — content_filter 예외 시 safe_history 재시도에 user 메시지 포함

| 항목 | 내용 |
|---|---|
| 목적 | Azure content_filter 예외 감지 시 `safe_history` 에 원본 user 질문이 보존되는지 검증 (LocationAgent Bug-2 회귀 방지) |
| 사전 조건 | `fake_kernel.get_service("chat")` 의 `get_chat_message_content` 첫 호출은 `Exception("content_filter policy violation")` raise, 두 번째 호출은 mock 응답 반환 |
| 실행 | `ChatAgent(fake_kernel).generate_draft("홍대 카페 창업 비용이 궁금합니다")` |
| 기대 | (1) 반환값 = "재시도 응답", (2) `get_chat_message_content` 호출 2회, (3) 재시도 `ChatHistory.messages` 의 role 목록에 "user" 포함 |
| 실측 | 모두 일치 |
| 판정 | PASS |

### T-CA-INJ-02 — content_filter 재시도도 실패 시 fallback 문자열 반환

| 항목 | 내용 |
|---|---|
| 목적 | 재시도마저 content_filter 예외로 실패할 때 기존 UX 문자열("일시적인 오류...")이 유지되는지 회귀 방지 |
| 사전 조건 | `get_chat_message_content` 가 호출될 때마다 `content_filter policy violation` 예외 raise |
| 실행 | 동일 질문으로 `generate_draft` 호출 |
| 기대 | (1) 호출 2회 (초기 + 재시도), (2) 반환값에 "일시적인 오류" 포함 |
| 실측 | 일치 |
| 판정 | PASS |

---

## 3. 검증 명령

```bash
cd backend
.venv/bin/python -m pytest tests/test_chat_injection.py -v
.venv/bin/python -m pytest tests/test_location_agent.py::TestCallLlm::test_13_content_filter_retry_includes_user_msg -v
ruff check backend/agents/chat_agent.py backend/tests/test_chat_injection.py
```

---

## 4. 관측 사항

- PR #298 작성 시점에는 `pytest-asyncio` 가 `requirements.txt` 및 `.venv` 에 누락되어 `@pytest.mark.asyncio` 데코레이터가 수집 단계에서 실패했다. 본 PR 에서 `pytest==9.0.2`, `pytest-asyncio==1.3.0` 을 `requirements.txt` 에 고정하여 재현성을 확보했다.
- `tests/test_location_agent.py` 에는 별도 4건의 preexisting FAIL 이 관측된다 (T-LA-03 invalid_json_fallback, T-LA-04 empty_locations, T-LA-21 retry_calls_llm_extra, T-LA-22 llm_failure_returns_guidance). 이들은 async 환경 문제가 아니며, 본 PR 의 범위 밖이다 — 별도 이슈로 이월 권장.
- `ChatAgent.generate_draft` 의 재시도는 `prior_history` 를 의도적으로 제외한다 (이전 턴이 필터 유발 원인일 경우 무한 재차단 방지). 본 계약은 테스트로 직접 검증하지 않으므로, 향후 대화 누적 인젝션 케이스가 확인되면 T-CA-INJ-03 으로 추가 권장.
