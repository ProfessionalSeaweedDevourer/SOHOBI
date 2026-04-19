# 세션 인수인계 — PR #315 OAuth 쿠키/로그 하드닝

## 개요

2026-04-18~19 세션. 직전 handoff `[next] #1` — PR #312 non-blocking 3건 봉인 트랙을 PR #315 로 단일 처리·머지.

1. **부팅** — `docs/session-reports/2026-04-18-pr312-merge-backend-logs-auth-handoff.md` 블록 로드 → [next] #1 착수
2. **플랜 수립** — `/plan` 으로 설계 확정 (공용 헬퍼 `backend/client_ip.py` 신설, 501 → JSONResponse 전환, 5 이벤트 client_ip 추가)
3. **PR #315 생성** → pytest 10/10 PASS (기존 7 + 신규 3)
4. **리뷰·머지** (사용자 수행) → main `285bb44`
5. **머지 후 TC** → pytest 10/10 PASS + prod `set-cookie` 4속성 확인

## 작업 내역

### 1. PR #315 구성

- 브랜치: `security/park-oauth-cookie-and-log-hardening` (origin/main 기반)
- 커밋: `998ca1d security: OAuth delete_cookie 대칭 + 501 쿠키 정리 + 보안 로그 client IP`
- 머지 커밋: `285bb44`
- PR 링크: [#315](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/315)

### 2. 변경 파일

| 파일 | 변경 |
| ---- | ---- |
| `backend/client_ip.py` | 신규 — `get_client_ip(request)` 공용 헬퍼 (X-Forwarded-For 마지막 hop 파싱) |
| `backend/api_server.py` | inline `_get_client_ip` 제거 → `from client_ip import get_client_ip as _get_client_ip`. `INJECTION_SUSPECT`/`DOMAIN_OVERRIDE` 로그에 `client_ip=` 추가 |
| `backend/auth_router.py` | `delete_cookie` 4곳(`220`/`244`/`261`/`276`) 에 `secure=True, samesite="lax", httponly=True` 명시. `/auth/google/callback` 501 early return 을 `JSONResponse + delete_cookie` 로 전환. `OAUTH_STATE_MISMATCH`/`OAUTH_TOKEN_EXCHANGE_FAILED`/`OAUTH_USERINFO_FAILED` 3 로그에 `client_ip=` 추가 |
| `backend/tests/test_oauth_state.py` | 신규 테스트 3건 (`test_delete_cookie_has_security_attrs`, `test_callback_501_clears_state_cookie`, `test_state_mismatch_log_includes_client_ip`) |

### 3. TC 결과

| TC | PR 생성 직후 | 머지 후 main |
| -- | ---- | ---- |
| 1. pytest 10/10 PASS | ✅ 0.58s | ✅ 0.53s |
| 2. state mismatch → `set-cookie` 4속성 | ⏸ pre-merge (Secure/HttpOnly 부재) | ✅ `HttpOnly; Max-Age=0; Path=/auth; SameSite=lax; Secure` |
| 3. `sohobi.security` stderr `client_ip=` | n/a (범위 재확인) | ⏸ Azure Container Apps Log Stream 운영 관측 대상 |
| 4. 무효 state → 400 + 삭제 헤더 | ✅ 400 | ✅ 400 |

결과 코멘트: [PR #315 #issuecomment-4275061395](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/315#issuecomment-4275061395) (머지 전), [#issuecomment-4275550377](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/315#issuecomment-4275550377) (머지 후).

## 설계 결정

- **`_get_client_ip` 공용화** — `api_server.py` 단독 정의 시 `auth_router.py` 가 필요해 순환 import 발생. `backend/client_ip.py` 신규 모듈로 추출(3줄 함수), 양쪽 import. `security_logging.py` 편입도 후보였으나 로깅 모듈 책임 확대 방지.
- **501 early return 전환** — `raise HTTPException(501, ...)` 시점에 state 쿠키가 request 에 이미 존재(이전 `/google` 호출에서 세팅)할 수 있음. 다른 에러 분기(400)와 동일한 `JSONResponse + delete_cookie` 패턴으로 일치.
- **`sohobi.security` 로거 `propagate=False`** — pytest `caplog` 는 root handler 기반이라 capture 불가. `test_state_mismatch_log_includes_client_ip` 는 `security_logger.addHandler(caplog.handler)` / `removeHandler` 로 명시적 연결 후 사용. 다른 테스트에 영향 없음.
- **TC3 범위 재정의** — `/api/v1/logs` 는 `logger.py` JSONL 파일 기반(query/error/rejection) 이미 `client_ip` 포함. 본 PR 의 `sohobi.security` 는 stderr StreamHandler 별도 스트림. `/api/v1/logs` 로는 확인 불가, 운영 관측은 Azure Container Apps Log Stream 대상.

## 직전 handoff `[next]` 재판정

| 원 항목 | 판정 | 근거 |
| ------- | ---- | ---- |
| 1. `security/park-oauth-cookie-and-log-hardening` 단일 PR 로 3건 봉인 | **done** | PR #315 머지(`285bb44`), pytest 10/10 PASS, prod `set-cookie` 4속성 확인 |
| 2. App Insights / 튜닝 가이드 / INVALIDATED 배너 | **carried** | 이벤트 발생 시점 대응 |
| 3. `docs/plans/2026-04-17-backend-load-*.json` 6건 담당 세션 확인 | **carried** | 본 세션 작업물 아님 |

직전 handoff `[traps]` 는 본 PR 에서 모두 정상 봉인:
- `delete_cookie` 4 분기 전체 수정 (3/4 만 고치는 비대칭 재도입 없음)
- `request.client is None` 방어는 `client_ip.py` 에서 `"unknown"` 폴백으로 처리 (기존 `api_server.py:73` 관습 유지; handoff 의 `"-"` 대비 일관성 우선)
- 501 early return 테스트는 `monkeypatch.setattr(auth_router, "_GOOGLE_CLIENT_ID", "")` 로 모듈 속성만 조작 (env 오염 없음)

## 다음 세션 인수 요약

1. **TC3 상시 관측** — `sohobi.security` stderr 출력이 Azure Container Apps Log Stream 에서 `OAUTH_STATE_MISMATCH client_ip=<ip> ...` / `INJECTION_SUSPECT client_ip=<ip> ...` 포맷으로 올라오는지 운영 중 1회 육안 확인. 발견 시 본 PR 에 코멘트 추가
2. **App Insights / 튜닝 가이드 / INVALIDATED 배너** — 이벤트 발생 시점 대응 (carry)
3. **`docs/plans/2026-04-17-backend-load-*.json` 6건** — 본 세션 범위 밖 untracked. 담당 세션 확인 전까지 별건

## 권장 다음 작업

- 즉시 착수해야 할 보안/기능 트랙은 없음. `/api/v1/logs` 인증 게이트(#313) · OAuth CSRF 방어(#310/#311/#312/#315) 모두 봉인.
- 이벤트 발생 전까지 carry 항목 대기. 새 트랙(예: `backend-load-*` 플랜 일부) 착수 시 새 handoff 에서 시작.

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-18-pr312-merge-backend-logs-auth-handoff.md

[decisions]
- _get_client_ip 는 backend/client_ip.py 공용 모듈로 분리 — api_server/auth_router 순환 import 회피, security_logging.py 책임 확대 방지
- /auth/google/callback 501 early return 은 JSONResponse + delete_cookie 패턴으로 전환 — 다른 에러 분기와 일치, state 쿠키 잔존 방지
- sohobi.security 로거 propagate=False 환경에서 caplog 사용 시 security_logger.addHandler(caplog.handler) 명시 필요 — pytest 기본 root handler 경로로는 capture 불가
- TC3 범위 재정의: /api/v1/logs (JSONL 파일) vs sohobi.security (stderr) 는 별도 스트림. 후자의 client_ip 포맷 관측은 Azure Container Apps Log Stream 대상
- request.client is None 폴백은 "unknown" (기존 api_server.py:73 관습 유지). handoff 의 "-" 예시 대비 코드 일관성 우선

[next]
1. (carried) sohobi.security stderr client_ip 포맷 Azure Log Stream 에서 1회 육안 확인 — 이벤트 발생 시
2. (carried) App Insights 도입 재평가 · 튜닝 가이드 실사용 피드백 · INVALIDATED 배너 — 이벤트 시점 대응
3. (carried) docs/plans/2026-04-17-backend-load-*.json 6건 담당 세션 확인

[traps]
- client_ip.py get_client_ip 는 X-Forwarded-For 마지막 hop 사용 (Azure Container Apps proxy 체인 전제). 다른 환경에서 신뢰 체인 바뀌면 첫 hop 으로 교체 필요
- sohobi.security propagate=False 는 의도된 격리 — pytest caplog 사용 테스트를 추가할 때마다 addHandler/removeHandler 블록 필요
- delete_cookie 속성 일치는 set_cookie 와 반드시 동일해야 브라우저가 삭제 인정. 향후 set_cookie 옵션 바뀌면 4개 delete_cookie 도 동시 조정
CLAUDE_HANDOFF_END -->
