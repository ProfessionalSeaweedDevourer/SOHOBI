# 세션 인수인계 — PR #296 스트림 rejection_history 이중 포맷 버그 수정

## 개요

직전 핸드오프(`2026-04-13-tc3-smoke-pass-handoff`)의 LOW 이월 항목 "스트림 경로 `log_query`가 포맷된 `rejection_history`를 재-포맷하는 버그" 해결. `/api/v1/stream` 핸들러가 SSE 페이로드용으로 flatten한 데이터를 그대로 `log_query`에 재전달해 logger 내부의 재-포맷 시 `grade`/`passed`/`warnings`/`issues`/`retry_prompt`가 공값으로 queries 로그에 기록되던 구조적 버그를 수정했다.

## 브랜치 & PR

- 브랜치: `fix/park-stream-rejection-history-double-format` (MERGED 후 자동 삭제)
- PR: #296 (MERGED, 머지 후 TC 재실행 4/4 PASS 코멘트 기록)
- 머지 커밋: `ff85339`

## 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/api_server.py` | 스트림 핸들러에 `raw_rejection_history` 변수 분리. SSE 페이로드는 flatten된 값·`log_query` 인자는 raw 전달 (비-스트림 경로와 포맷 계약 통일) |
| `backend/tests/test_logger_rejection_history.py` | 이중 포맷 시 verdict 필드 소실을 보장하는 회귀 테스트 `test_double_format_collapses_verdict_fields` 추가 |

## 검증

| TC | 결과 |
|----|------|
| TC-1 단위 테스트 (`pytest tests/test_logger_rejection_history.py -v`) | 4/4 PASS (신규 회귀 테스트 포함) |
| TC-2 프로덕션 스트림 실측 | 자연 트래픽 대기 — 스키마 채널 자체는 PR #295 TC-3에서 이미 검증 |
| 린트 (`ruff check`) | 통과 |

## 미해결 · 관측

- 이전 세션에서 이월된 HIGH/MED 항목은 그대로 유지 (F1~F5 회귀, ChatAgent 인젝션 pytest)
- frontend severity 배지(세션 C)는 선결조건(로그 스키마)이 PR #295·#296 완료로 완전히 충족됨 — 즉시 착수 가능
- 자연 트래픽에서 `final_verdict.issues[].severity == "low"` 및 escalated/is_partial `final_verdict=null` 실측은 여전히 대기

## 다음 세션 인수 요약

1. frontend severity 배지 — LogTable EntryDetail에 severity 컬러 매핑(high→red, medium→yellow, low→gray) 추가. 단일 파일 UI 작업, playwright 시각 검증
2. ChatAgent 인젝션 pytest (`backend/tests/test_chat_injection.py`, Azure content filter 예외 mock 설계)
3. F1~F5 로컬 회귀 스위트 (gpt-4.1-mini)
4. 자연 트래픽에서 low severity · escalated `final_verdict=null` 재관측

---
<!-- CLAUDE_HANDOFF_START
branch: main (작업 브랜치 머지 후 삭제됨)
pr: 296 (MERGED)
prev: 2026-04-13-tc3-smoke-pass-handoff.md

[unresolved]
- HIGH F1~F5 로컬 회귀 스위트(gpt-4.1-mini) 대기 (2세션 이월)
- MED ChatAgent 인젝션 거절 pytest 부재 — Azure content filter 예외 mock 필요 (2세션 이월)
- LOW frontend severity 배지 (세션 C) 미착수 — 선결조건(로그 스키마) 충족됨, 즉시 착수 가능
- LOW escalated/is_partial 프로덕션 실측 미완 — 자연 유발 대기 (final_verdict=null 경로)
- LOW first-pass approved low severity 포착 실측 미완 — 자연 트래픽 축적 대기

[decisions]
- SSE 페이로드는 flatten·log_query 인자는 raw로 분리. logger 내부가 _format_rejection_history를 항상 호출하는 계약을 유지하되 호출부의 중복 포맷만 제거 (logger 시그니처 변경 없이 호출부만 수정해 비-스트림 경로와 계약 통일)

[next]
1. frontend severity 배지 — LogTable.jsx EntryDetail에 severity 컬러 매핑 추가, playwright 검증 (선결조건 충족, 가장 가벼움)
2. ChatAgent 인젝션 pytest 추가 (backend/tests/test_chat_injection.py)
3. F1~F5 로컬 회귀 스위트
4. 자연 트래픽에서 low severity · escalated final_verdict=null 재관측

[traps]
- logger.log_query는 내부에서 _format_rejection_history를 호출한다. 호출부에서 미리 flatten해 넘기면 두 번째 호출 때 entry.get("verdict", {}) 가 빈 dict가 되어 grade/issues 등 전부 공값으로 기록됨 — 호출부에서 raw를 유지해야 함
- SSE 페이로드는 클라이언트 렌더링 목적으로 flatten된 스키마가 필요하므로 ev["rejection_history"] 자체는 flatten 유지. 로깅용 raw는 별도 변수로 보존
CLAUDE_HANDOFF_END -->
