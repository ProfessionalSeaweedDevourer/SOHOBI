# 세션 인수인계 — PR #298·#299 ChatAgent content_filter 재시도 + 테스트 의존성 편입

## 개요

직전 handoff(`2026-04-13-logtable-severity-badge-handoff`)에서 3세션 연속 이월되어 있던 MED 항목 "ChatAgent 인젝션 거절 pytest 부재" 를 해소. 탐색 중 드러난 사실: ChatAgent 는 LocationAgent(T-LA-13 참조) 와 달리 `content_filter` 재시도 로직 자체가 없어 Azure 콘텐츠 필터에 걸리면 "일시적인 오류" 고정 문자열로 UX 가 끊겼다. LocationAgent 패턴을 ChatAgent 에 포팅하고 T-CA-INJ-01/02 단위 테스트를 신규 작성해 PR #298 로 머지. 이어 PR #298 작성 중 `pytest-asyncio` 가 `.venv`·`requirements.txt` 양쪽에 누락되어 `@pytest.mark.asyncio` 기반 기존 async 테스트(T-LA-13 포함)가 전부 수집 실패하는 상태임을 발견, 후속 PR #299 에서 `pytest==9.0.2` + `pytest-asyncio==1.3.0` 을 requirements 에 고정하고 T-CA-INJ 결과 리포트를 `docs/test-reports/` 에 추가 후 머지.

## 브랜치 & PR

- PR #298 (MERGED, 머지 커밋 `5fc8964`) — 브랜치 `feat/park-chat-content-filter-retry` (삭제됨)
- PR #299 (MERGED, 머지 커밋 `f3c2e21`) — 브랜치 `chore/park-pytest-asyncio` (삭제됨)
- 현재 브랜치: `main` (clean, origin 동기화됨)

## 수정 파일

| 파일 | PR | 변경 |
|------|----|------|
| `backend/agents/chat_agent.py` | #298 | `generate_draft` 의 `except Exception` 블록에 content_filter 분기 추가. 전두어 "다음은 합법적인 창업 상담 요청입니다..." + `safe_history.add_user_message(question)` 로 1회 재시도, prior_history 제외. (+16줄) |
| `backend/tests/test_chat_injection.py` | #298 | 신규. `fake_kernel` fixture + T-CA-INJ-01 (재시도 user 메시지 포함) / T-CA-INJ-02 (재시도 실패 시 fallback). `asyncio.run()` 패턴 (#298 시점 pytest-asyncio 미설치). (+83줄) |
| `backend/requirements.txt` | #299 | `pytest==9.0.2`, `pytest-asyncio==1.3.0` 신규 고정 (+4줄) |
| `docs/test-reports/chat_agent_content_filter_retry_20260413.md` | #299 | T-CA-INJ-01/02 결과 문서화, preexisting FAIL 목록 병기 (+68줄) |

## 검증 결과

| TC | 결과 |
|----|------|
| T-CA-INJ-01 — content_filter → safe_history 재시도에 user 메시지 포함 | PASS |
| T-CA-INJ-02 — 재시도 실패 시 "일시적인 오류" fallback | PASS |
| T-LA-13 — LocationAgent 재시도 계약 유지(회귀 확인) | PASS |
| ruff check backend/ | clean |

## 미해결 · 관측

- `tests/test_location_agent.py` 에 preexisting 4건 FAIL 관측: T-LA-03 (invalid_json_fallback), T-LA-04 (empty_locations), T-LA-21 (retry_calls_llm_extra), T-LA-22 (llm_failure_returns_guidance). async 문제 아니며 본 세션 범위 밖 — 후속 세션에서 원인 분석 필요
- 이전 세션에서 이월된 HIGH/LOW 항목은 그대로 유지 (아래 블록 참조)
- `prior_history` 가 content_filter 유발 원인인 대화 누적 인젝션 케이스는 테스트로 직접 검증하지 않음 — 향후 실측 확보 시 T-CA-INJ-03 추가 권장

## 다음 세션 인수 요약

1. F1~F5 로컬 회귀 스위트(gpt-4.1-mini) — HIGH, 4세션 이월. 로컬 백엔드 기동 필요
2. `test_location_agent.py` preexisting 4건 FAIL 원인 분석 (async 문제 아님 — 로직/mock 데이터 문제 추정)
3. 자연 트래픽에서 medium/low severity 배지 실측, escalated `final_verdict=null` 실측
4. ChatAgent content_filter 재시도 효과 프로덕션 관측 — Azure 로그에서 재시도 성공률 확인
5. "모든 검증 통과" 단문 UX 경과 관찰

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: 298, 299 (both MERGED)
prev: 2026-04-13-logtable-severity-badge-handoff.md

[unresolved]
- HIGH F1~F5 로컬 회귀 스위트(gpt-4.1-mini) 대기 (4세션 이월)
- MED test_location_agent.py preexisting 4건 FAIL (T-LA-03/04/21/22) — async 이슈 아님, 로직/mock 데이터 추정. 신규 관측
- LOW 자연 트래픽에서 medium/low severity 배지 실측 미완
- LOW escalated/is_partial final_verdict=null 프로덕션 실측 미완
- LOW ChatAgent content_filter 재시도 프로덕션 효과 관측 (Azure 로그에서 재시도 발생·성공 빈도)
- LOW first-pass approved "모든 검증 통과" 단문 UX 경과 관찰
- LOW prior_history 누적 인젝션 케이스 T-CA-INJ-03 추가 — 자연 실측 확보 시

[decisions]
- ChatAgent 재시도 safe_history 에 prior_history 를 의도적으로 제외 — 이전 턴이 필터 유발 원인일 경우 무한 재차단 방지. LocationAgent 는 user_msg 1회만 재전달하므로 동일 계약 유지
- 재시도 실패 시 기존 "일시적인 오류..." 문자열을 유지 (새 문구 도입 X) — 프론트/FAQ 쪽에 고정 문구 의존 가능성 고려
- pytest-asyncio 편입을 별도 PR(#299)로 분리 — #298 머지 속도 우선, async 스위트 전체 복구는 독립 가치
- test_chat_injection.py 는 asyncio.run() 패턴 유지 (pytest-asyncio 설치 전에도 실행 가능). 향후 스타일 통일 시 @pytest.mark.asyncio 로 전환 고려

[next]
1. F1~F5 로컬 회귀 스위트
2. test_location_agent.py T-LA-03/04/21/22 FAIL 원인 분석·수정
3. 자연 트래픽 medium/low severity · escalated final_verdict=null 실측
4. ChatAgent content_filter 재시도 프로덕션 로그 관측
5. "모든 검증 통과" 단문 UX 경과 관찰

[traps]
- fake_kernel 의 get_chat_message_content 시그니처에 kernel= 키워드 필수 — ChatAgent 가 kernel=self._kernel 을 넘기므로 LocationAgent 버전(kernel 미사용)과 달리 mock 함수가 kernel 파라미터를 받아야 함
- ChatAgent 는 _PRIVACY_KEYWORDS("개인정보")·_SPECIALIST_RESPONSES 단락이 service 호출 전에 발생 — 재시도 테스트 질문에 해당 키워드 포함 금지
- ChatAgent.generate_draft 는 공개 재시도 헬퍼(_call_llm 같은 것)가 없음 — 재시도 분기를 외부로 추출하고 싶어도 privacy/specialist 단락이 generate_draft 에 묶여 있어 신중히 접근
- SK ChatHistory role 직렬화는 "authorrole.user" 형식 — 검증은 반드시 .lower() 후 "user" in 문자열 (T-LA-13 과 동일 가드)
- pytest-asyncio 설치 후 preexisting FAIL 이 드러났으므로, 향후 async 테스트 추가 시 기존 스위트 회귀 여부를 별도로 검증해야 함
CLAUDE_HANDOFF_END -->
