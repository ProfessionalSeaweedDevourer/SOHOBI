# 세션 인수인계 — PR #312 머지 + backend-logs 인증 게이트 갱신(PR #313)

## 개요

2026-04-18 세션. PR #312 (OAuth 실패 경로 쿠키 정리 + `sohobi.security` 로거 명시 설정) 리뷰·머지·검증을 마치고, 직전 handoff [next] #2 (`docs/guides/backend-logs.md` 의 `/api/v1/logs` 인증 게이트 반영)를 PR #313 으로 봉인.

1. **PR #312 리뷰 (시니어 보안 엔지니어 페르소나)** — Approve + non-blocking 3건 식별
2. **PR #312 admin squash merge** → main `3fd1777` 반영, 머지 후 TC는 PR #312 본문에 이미 pytest 7건 PASS 명시
3. **handoff [next] #2 착수** — `/specify` 로 세션 스코프 확정 → `docs/guides/backend-logs.md` 갱신 범위로 결정
4. **PR #313 생성·TC 4/4 PASS·admin squash merge** → main `1fe12c3` 반영
5. **머지 후 main TC 재실행 4/4 PASS** → PR #313 에 결과 코멘트

## 작업 내역

### 1. PR #312 리뷰 → 머지

- 페르소나 라우팅: `backend/auth_router.py` 변경 → 우선순위 1 (시니어 보안 엔지니어)
- 리뷰 결과: Approve. 대칭성 회복 확인(state-mismatch 분기와 동일 패턴), `async with httpx.AsyncClient()` 블록 내부 return 으로 커넥션 풀 정상 cleanup, `secrets.compare_digest` 유지
- 리뷰 코멘트: [PR #312 #issuecomment-4273150515](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/312#issuecomment-4273150515)
- 머지 커밋: `3fd1777`

#### PR #312 non-blocking 후속 3건 (별도 트랙으로 식별, 본 세션에서는 착수 안 함)

| # | 이슈 | 위치 |
| - | ---- | ---- |
| 1 | `delete_cookie` 호출에 `secure`/`samesite` 속성 부재 — `set_cookie`(secure=True, samesite=lax)와 비대칭. 최신 Chrome은 Secure 속성 불일치 시 쿠키 삭제 거부 가능 | [backend/auth_router.py:220](../../backend/auth_router.py#L220), [:244](../../backend/auth_router.py#L244), [:261](../../backend/auth_router.py#L261), [:276](../../backend/auth_router.py#L276) |
| 2 | `/auth/google/callback` 501 early return (`if not _GOOGLE_CLIENT_ID ...`)은 여전히 `HTTPException` raise — state 쿠키 잔존. config fault 경로라 공격면 작음 | [backend/auth_router.py:209-210](../../backend/auth_router.py#L209-L210) |
| 3 | 보안 로그에 client IP 부재 — `OAUTH_STATE_MISMATCH`, `OAUTH_TOKEN_EXCHANGE_FAILED`, `OAUTH_USERINFO_FAILED`, `INJECTION_SUSPECT`, `DOMAIN_OVERRIDE` 모두 `request.client.host` 미포함. `IP_BLOCKED` 만 포함(비대칭) | [backend/auth_router.py:214-217](../../backend/auth_router.py#L214-L217), [backend/api_server.py:315-316](../../backend/api_server.py#L315-L316), [:343-349](../../backend/api_server.py#L343-L349) |

### 2. PR #313 생성 (handoff [next] #2 봉인)

- 브랜치: `docs/park-backend-logs-auth-gate` (origin/main 기반)
- 변경: [docs/guides/backend-logs.md](../guides/backend-logs.md) 1파일
  - 머리말에 `API_SECRET_KEY` 요구사항 1줄
  - **인증 섹션 신설** — Bearer / X-API-Key 두 방식, 로컬 미설정 시 통과(skip) 명시
  - 기본 조회·시간대 필터링 `curl` 예제에 Bearer 헤더 반영, X-API-Key 대체 주석
  - **401 응답 시 섹션 신설** — env 로드 누락·오타·서버 값 불일치 3가지 원인·조치
- 커밋: `66b66ec docs: backend-logs 인증 게이트 반영`
- 머지 커밋: `1fe12c3`

### 3. TC 결과 (prod `$BACKEND_HOST` 실측)

| TC | PR 생성 직후 | 머지 후 main |
| -- | ---- | ---- |
| 1. no auth → 401 | ✅ 401 | ✅ 401 |
| 2. Bearer → 200 + `entries[]` | ✅ 200, count=1 | ✅ 200, count=1 |
| 3. 시간대 필터 Bearer → 200 | ✅ 200 | ✅ 200 |
| 4. X-API-Key 대체 → 200 | ✅ 200 | ✅ 200 |

결과 코멘트: [PR #313 #issuecomment-4273723232](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/313#issuecomment-4273723232), [#issuecomment-4273735884](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/313#issuecomment-4273735884).

## 수정 파일

| 파일 | 변경 |
| ---- | ---- |
| `docs/guides/backend-logs.md` | 인증 섹션·401 조치 섹션 신설, 모든 예제에 Bearer 헤더 반영 (+20 -3 lines) |
| `docs/session-reports/2026-04-18-pr312-merge-backend-logs-auth-handoff.md` | 신규 (본 문서) |

> 워킹트리에 `docs/plans/2026-04-17-backend-load-*.json` 6건 untracked 파일 잔존 (본 세션 작업물 아님, 직전 handoff 에서도 제외 권고).

## 직전 handoff `[next]` 재판정

| 원 항목 | 판정 | 근거 |
| ------- | ---- | ---- |
| 1. `security/park-oauth-followup` 단일 PR로 Issue 1+2 봉인 + pytest 7건 PASS | **done** | PR #312 머지(`3fd1777`), pytest 7/7 PASS, 이미 직전 세션에서 완료 |
| 2. `docs/guides/backend-logs.md` 인증 게이트 변경사항 반영 | **done** | PR #313 머지(`1fe12c3`), TC 4/4 PASS |
| 3. App Insights·튜닝 가이드 실사용 피드백·INVALIDATED 배너 패턴 | **carried** | 발생 시점 대응 |

직전 handoff `[traps]` 는 모두 PR #312 머지 당시 정상 봉인 확인됨 — 커넥션 풀 cleanup(httpx 블록 내부 return), TestClient cookie jar Path 우회, `configure_security_logger()` idempotent, `sohobi.*` 다른 로거 5개 미변경.

## 다음 세션 인수 요약

1. **PR #312 non-blocking 3건 봉인 트랙** — `delete_cookie` 보안 속성 일치 + 501 early return 쿠키 정리 + 보안 로그에 client IP 추가. 단일 `security/` PR로 묶는 것이 자연스러움 (auth_router.py 집중). 회귀 테스트는 기존 `test_oauth_state.py` 스키마 재사용 — set-cookie 헤더에 `Secure; SameSite=lax` 포함 검증 추가 + `caplog` 로 client IP 로그 검증
2. **App Insights / 튜닝 가이드 / INVALIDATED 배너** — 이벤트 발생 시점 대응. 재실측 요구·무효화 케이스 발생 전까지 보류
3. **`docs/plans/2026-04-17-backend-load-*.json` 6건** — 본 세션 범위 밖 untracked 파일. 작성자(다른 세션)가 별도 PR로 정리하거나 본인이 담당 확인 후 처리

## 권장 다음 작업

**다음 세션 1순위**: PR #312 non-blocking 3건 봉인. 단일 security PR로 묶는 것을 권장 — auth_router.py 에 집중되고, 회귀 테스트가 기존 `test_oauth_state.py` 스키마 재사용으로 비용 낮음.

### 브랜치·범위 초안

- 브랜치: `security/park-oauth-cookie-and-log-hardening`
- 변경 파일: `backend/auth_router.py`, `backend/api_server.py`, `backend/tests/test_oauth_state.py`
- Test plan 초안:
  - pytest 기존 7건 + 신규 3건 (secure/samesite 속성 검증 + 501 쿠키 정리 검증 + client IP 로그 검증) PASS
  - stderr 에 `[SECURITY] ... client_ip=<ip>` 포맷 1회 수동 확인

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-18-pr311-merge-and-oauth-followup-plan-handoff.md

[decisions]
- PR #312 non-blocking 3건은 단일 security PR로 번들 — auth_router.py 집중, 회귀 테스트 스키마 재사용으로 비용 낮음
- backend-logs.md 갱신은 Bearer 를 기본 예제로, X-API-Key 를 주석 대체로 — verify_api_key 가 양쪽 모두 수용하지만 Bearer 가 REST 표준에 가까움
- 401 응답 시 조치에 "값 출력 금지" 원칙 명시 — 가이드 따라가다 secret 누설 사고 방지
- docs/plans/2026-04-17-backend-load-*.json 6건 untracked 는 본 세션 작업물 아님, 담당 세션 확인 전까지 git add 대상 제외

[next]
1. security/park-oauth-cookie-and-log-hardening 브랜치 → PR #312 후속 3건(delete_cookie secure/samesite, 501 early return 쿠키 정리, _security_logger 에 client IP) 단일 PR 처리 + pytest 기존 7 + 신규 3 PASS
2. (carried) App Insights 도입 재평가·튜닝 가이드 실사용 피드백·INVALIDATED 배너 — 이벤트 시점 대응
3. docs/plans/2026-04-17-backend-load-*.json 6건 담당 세션 확인 — 본 세션 작업물 아니므로 별건

[traps]
- delete_cookie 속성 일치 수정 시 4개 분기 모두 동일 패턴 적용 — 3개만 고치면 비대칭 재도입
- client IP 로깅 시 request.client 가 None 일 수 있음 (TestClient 일부 케이스) — `getattr(request.client, "host", "-")` 방어 필요
- 501 early return 쿠키 정리 테스트는 _GOOGLE_CLIENT_ID 를 monkeypatch 로 빈 문자열 강제 후 호출 — env 자체를 건드리면 다른 테스트 오염
- 직전 handoff 의 trap "configure_security_logger() 는 반드시 idempotent" 는 PR #312 에서 이미 봉인됨 — 본 트랙에서는 security_logging.py 수정 시에만 주의
CLAUDE_HANDOFF_END -->
