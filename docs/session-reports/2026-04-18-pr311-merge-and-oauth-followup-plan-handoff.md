# 세션 인수인계 — PR #311 OAuth state 하드닝 머지 + 후속 2건 플랜

## 개요

2026-04-18 세션. PR #311 (OAuth state 방어 후속 하드닝) 의 리뷰·머지·검증을 완료하고, 리뷰에서 non-blocking 으로 분류된 잔여 2건의 후속 플랜을 별도 트랙으로 기획.

1. **PR #311 admin squash merge** → main `d01ebad` 반영
2. main 동기화 후 Test Plan TC 4종 재실행 → 3 PASS / 1 SKIP (logs 엔드포인트 인증 게이트로 직접 확인 불가, 코드 경로는 pytest 봉인)
3. 후속 2건 (실패 분기 쿠키 정리 비대칭 + `sohobi.security` 로거 명시 설정) 플랜 작성 → `~/.claude/plans/2-stateless-engelbart.md`

## 작업 내역

### 1. PR #311 리뷰 → 머지

- 페르소나: 시니어 보안 엔지니어 (auth_router.py 수정 우선순위 1)
- 리뷰 결과: Approve + non-blocking 2건 ([PR #311 코멘트](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/311#issuecomment-4272748260))
- 머지: `gh pr merge 311 --admin --squash` (mergeable=MERGEABLE, mergeStateStatus=BLOCKED → admin bypass)
- 머지 커밋: `d01ebad`

### 2. 머지 후 TC 검증 (main)

| TC | 결과 | 비고 |
|----|------|------|
| pytest `test_oauth_state.py` 5건 | ✅ PASS | 5/5 (0.50s) |
| `/auth/google` Set-Cookie 헤더 | ✅ PASS | `oauth_state=...; HttpOnly; Max-Age=600; Path=/auth; SameSite=lax; Secure` |
| `/auth/google/callback?code=fake` (state 누락) | ✅ PASS | 400 + `set-cookie: oauth_state=""; Max-Age=0; Path=/auth; SameSite=lax` |
| 백엔드 로그 `OAUTH_STATE_MISMATCH` warning | ⏸ SKIP | `/api/v1/logs` 엔드포인트가 SEC-001 (PR #309) 머지 후 인증 게이트됨. 가이드 [`docs/guides/backend-logs.md`](../guides/backend-logs.md) outdated. 코드 경로는 pytest 로 검증 |

결과는 PR #311 에 코멘트로 기록 ([#issuecomment-4272997585](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/311#issuecomment-4272997585)).

### 3. 후속 2건 플랜 작성

리뷰 코멘트의 non-blocking 2건을 별도 PR 로 분리 기획. 플랜 파일: `~/.claude/plans/2-stateless-engelbart.md` (Claude 로컬 plan).

**Issue 1 — 실패 분기 쿠키 정리 비대칭**
- 위치: `backend/auth_router.py:237-238` (토큰 교환 실패), `:247-248` (userinfo 조회 실패)
- state mismatch 분기는 `JSONResponse + delete_cookie` 패턴이지만 두 실패 분기는 `HTTPException` raise 로 쿠키 잔존
- 처리안: 두 raise 를 동일 패턴 (`JSONResponse + delete_cookie + _security_logger.warning("OAUTH_TOKEN_EXCHANGE_FAILED status=%s")`) 으로 변환. 추상화 없음 (분기 4개 + CLAUDE.md "3줄 반복 < 조기 추상화")
- 회귀 테스트 2건 추가 (`test_callback_token_exchange_failure_clears_cookie`, `test_callback_userinfo_failure_clears_cookie`)

**Issue 2 — `sohobi.security` 로거 명시 설정**
- 사용처 4곳 ([`backend/auth_router.py:32`](../../backend/auth_router.py#L32), [`backend/api_server.py:168`](../../backend/api_server.py#L168), [`:314`](../../backend/api_server.py#L314), [`:342`](../../backend/api_server.py#L342)) 모두 핸들러/포맷 미설정 — 루트 propagation 의존
- 처리안: `backend/security_logging.py` 신설, `configure_security_logger()` idempotent 함수가 stderr StreamHandler + `[SECURITY] ...` 포맷터 + `propagate=False` 부착. `api_server.py` 시작 시 1회 호출
- 범위 결정: 다른 `sohobi.*` 로거 5개 (`api`, `feedback`, `events`, `report`, `roadmap`) 는 손대지 않음 — dictConfig 도입은 출력 포맷 회귀 위험 + PR 범위 초과로 보류 (사용자 확정)

**브랜치**: `security/park-oauth-followup` (origin/main 기반 신규)

## 수정 파일

| 파일 | 변경 |
|------|------|
| (코드) | 본 세션 코드 수정 없음 — PR #311 머지 + 후속 플랜 작성만 |
| `docs/session-reports/2026-04-18-pr311-merge-and-oauth-followup-plan-handoff.md` | 신규 (본 문서) |

> 워킹트리에 `docs/plans/2026-04-17-backend-load-*.json` 6건의 untracked 파일이 존재하나 본 세션 작업물 아님 (4-17 다른 워크플로우 산출물). handoff push 시 add 대상에서 제외.

## 직전 handoff `[unresolved]` 재판정

직전 handoff ([2026-04-16-tuning-guide-and-cf-closure-handoff.md](2026-04-16-tuning-guide-and-cf-closure-handoff.md)) 에는 `[unresolved]` 섹션이 비어 있음 (모든 항목이 `[decisions]` 로 closure 처리됨). 재판정 대상 없음.

## 직전 handoff `[next]` 재판정

| 원 항목 | 판정 | 근거 |
|---------|------|------|
| 1. App Insights 도입 필요성 재평가 | **carried** | 본 세션 범위 외. content_filter 실측 재요구 미발생 |
| 2. 튜닝 가설 PR 초안 작성 시 가이드 적용 | **carried** | 본 세션은 보안 PR 트랙. 튜닝 가설 작성 기회 없음 |
| 3. 플랜 무효화 시 배너/CLOSED-POLICY 선택 | **carried** | 본 세션 범위 외. 무효화 발생 시점 대응 |

## 다음 세션 인수 요약

1. **`security/park-oauth-followup` 브랜치 작업 시작** — `~/.claude/plans/2-stateless-engelbart.md` 의 Issue 1 + Issue 2 를 단일 PR 로 묶어 처리. PR 본문 Test plan 에 7개 pytest (기존 5 + 신규 2) + 수동 stderr 포맷 확인 명시
2. **`docs/guides/backend-logs.md` 갱신 필요** — `/api/v1/logs` 가 SEC-001 이후 인증 게이트되어 가이드의 "인증 없이 조회" 안내가 outdated. 보안 PR 트랙 일단락 후 별건으로 정리
3. **PR #311 lint 통과 확인** — pre-commit 훅이 정상 동작했고 머지된 코드에 ruff 위반 없음. 후속 PR 도 동일 정책 유지

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-16-tuning-guide-and-cf-closure-handoff.md

[decisions]
- 후속 2건 플랜은 단일 PR (security/park-oauth-followup) 로 묶음 — 분기 4개 + 로거 1곳 설정으로 변경 규모 작음. CLAUDE.md memory 의 "user prefers bundled PRs" 원칙 적용
- sohobi.security 로거 설정 범위는 단일 로거만. 전 sohobi.* 로거 dictConfig 통일은 출력 포맷 회귀 위험 + 범위 초과로 보류 (사용자 확정)
- 실패 분기 쿠키 정리는 헬퍼 함수 추상화 없이 인라인 — CLAUDE.md "3줄 반복 < 조기 추상화" 원칙 적용
- TC4 (백엔드 로그 OAUTH_STATE_MISMATCH 확인) 는 logs 엔드포인트 인증 게이트로 SKIP — 코드 경로는 pytest 봉인이므로 PASS 등가 처리

[next]
1. security/park-oauth-followup 브랜치 생성 → 플랜 파일(~/.claude/plans/2-stateless-engelbart.md) 의 Issue 1 + 2 적용 → pytest 7건 PASS → PR 생성
2. docs/guides/backend-logs.md 의 인증 게이트 변경사항 반영 (별건, 후속)
3. (carried from prev) App Insights 도입·튜닝 가이드 실사용 피드백·INVALIDATED 배너 패턴 — 발생 시점 대응

[traps]
- /auth/google/callback 의 두 실패 분기 변환 시 async with httpx.AsyncClient() 블록 내부에서 return 해야 컨텍스트 매니저 __aexit__ 가 정상 호출됨. 블록 외부 return 으로 옮기면 커넥션 풀 cleanup 누락 위험
- TestClient 의 cookie jar 가 Path 속성 매칭을 일관 처리하지 못함 — 신규 실패 분기 테스트도 기존 valid_state 테스트와 동일하게 `client.cookies.set("oauth_state", state)` 명시 우회 필요
- configure_security_logger() 는 반드시 idempotent 해야 함 — pytest 의 importlib.reload 로 모듈 재로드 시 핸들러 중복 부착되면 stderr 출력 N배 증가 회귀 발생
- sohobi.security 외 5개 sohobi.* 로거는 의도적으로 무설정 유지 — 향후 dictConfig 통합 작업 시 본 세션 결정 (범위 분리) 와 충돌하지 않도록 confirm
CLAUDE_HANDOFF_END -->
