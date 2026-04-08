# 세션 인수인계 — 2026-04-09 체크리스트 403 수정 + 히스토리 복원 기획

## 브랜치

- `PARK-fix-checklist-403` — 체크리스트 403 수정 (PR #247, 테스트 완료, 머지 대기)
- 히스토리 복원은 **별도 브랜치 `PARK-session-restore`를 `origin/main` 기반으로 생성**하여 진행

---

## 완료된 작업: 체크리스트 403 수정

### 문제

`GET /api/checklist/{sessionId}` 요청이 프로덕션(Cosmos DB)에서 403 반환. 콘솔에 반복 에러 발생.

### 원인

SSE 스트리밍 플로우에서 타이밍 불일치:

1. `domain_classified` 이벤트 시점에 `sessionId`를 프론트에 전달
2. 프론트 `useChecklistState`의 `useEffect([sessionId])`가 즉시 `GET /api/checklist/{sid}` 호출
3. 그러나 백엔드 `save_query_session()`은 `complete` 이벤트 시점에 발생
4. `session_exists()` → Cosmos DB에 미존재 → 403

인메모리 모드(로컬)에서는 `get_query_session()`이 `_memory`에 넣어주므로 발생하지 않음.

### 수정 내용 (PR #247)

| 파일 | 변경 |
|------|------|
| `frontend/src/components/checklist/useChecklistState.js` | `enabled` 파라미터 추가 — `false`이면 fetch 스킵 |
| `frontend/src/pages/UserChat.jsx` | `useChecklistState(sessionId, messages.length > 0)` — 첫 응답 완료 후에만 fetch |

### 테스트 결과

| TC | 항목 | 결과 |
|----|------|------|
| TC1 | 새 세션 진입 시 403 에러 없음 | PASS |
| TC2 | 첫 응답 후 체크리스트 정상 로드 (2/8) | PASS |
| TC3 | 수동 토글 PATCH 정상 (3/8) | PASS |
| TC4 | 새로고침 후 복원 | N/A — 메시지 복원 미구현 (아래 기획으로 이어짐) |

---

## 미완료 작업: 세션 히스토리 복원 구현

### 배경

PR #247의 `messages.length > 0` 가드로 인해, 새로고침 시 messages가 빈 배열로 초기화되어 체크리스트도 로드되지 않음. 근본 해결을 위해 메시지 복원 로직이 필요.

### 기존 인프라 (이미 구현되어 있음)

| 인프라 | 위치 | 비고 |
|--------|------|------|
| Cosmos DB 세션 저장 (history, context) | `session_store.py` | TTL 24h(익명), 30d(로그인) |
| 로그인 사용자 세션 귀속 | `auth_router.py` `/auth/link-session` | AuthContext에서 자동 호출 |
| user_id → 세션 목록 조회 | `session_store.get_sessions_by_user()` | Cosmos 쿼리 구현 완료 |
| ChatHistory 직렬화 | `_serialize_history` / `_deserialize_history` | role + content 쌍 |

### 미저장 데이터 (현재 Cosmos에 없음)

`chart`, `charts`, `suggested_actions`, `grade`, `domain`, `confidence_note` — orchestrator SSE 스트림에서 생성 후 프론트로 전달되면 소멸.

### 구현 방식: 2-레이어 복원

#### Layer 1: sessionStorage (같은 탭, chart 포함 완전 복원)

- `useChatMessages.js`에서 messages 변경 시 `sessionStorage`에 persist
- 페이지 로드 시 sessionStorage에서 즉시 복원
- 세션 ID 변경 시 이전 캐시 정리

#### Layer 2: 백엔드 API (로그인 사용자, 탭 닫고 재접속/다른 기기)

- 세션 저장 시 렌더링용 메타데이터 추가: `messages` 배열 (question, domain, grade, draft)
  - `api_server.py` stream_query의 complete 핸들러에서 저장
  - `session_store.py` save_query_session — schemaless이므로 필드 추가만
- 새 엔드포인트: `GET /api/session/{sid}/history` → messages 배열 반환
- 프론트: sessionStorage 비어있고 + 로그인 상태 + sessionId 있으면 → API 호출

#### 복원 우선순위

```
1. sessionStorage (즉시, chart 포함 완전 복원)
2. 백엔드 API (로그인 사용자, 텍스트+도메인+등급만)
3. 빈 상태 (비로그인 + 새 탭)
```

### 수정 대상 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/hooks/chat/useChatMessages.js` | sessionStorage persist/restore, API 복원 호출 |
| `frontend/src/pages/UserChat.jsx` | 로그인 사용자 복원 트리거, sessionId 초기화 로직 |
| `integrated_PARK/api_server.py` | `GET /api/session/{sid}/history` + complete에서 messages 메타 저장 |
| `integrated_PARK/session_store.py` | save_query_session에 messages 필드 포함 |

### 성능 영향

- Cosmos DB RU: 읽기 +1 point read/페이지 로드 (~5 RU) — 기존 패턴 범위 내
- 문서 크기: ~2-5KB → ~15-30KB (chart 미포함) — TTL 내에서 누적 제한적
- 프론트 로드: 1회 fetch ~50-200ms — 대화 영역 skeleton 표시 후 채움
- **결론: 성능 영향 미미**

### 라이브 서비스 영향

- Cosmos DB schemaless → **무중단 배포**
- 기존 세션에 `messages` 필드 없음 → 빈 배열 fallback (하위 호환)
- 새 API 엔드포인트 → 기존 트래픽 무영향

### 검증 TC

| TC | 시나리오 | 확인 |
|----|---------|------|
| TC1 | 대화 후 F5 새로고침 (비로그인) | sessionStorage에서 메시지+차트+체크리스트 복원 |
| TC2 | 대화 후 F5 새로고침 (로그인) | 동일 |
| TC3 | 탭 닫고 재접속 (로그인) | 백엔드에서 텍스트 대화+체크리스트 복원 |
| TC4 | 탭 닫고 재접속 (비로그인) | 빈 상태, 403 에러 없음 |
| TC5 | 새 질문 추가 후 새로고침 | 이전+신규 모두 복원 |

### 스코프 밖 (별도 이슈)

- chart/charts 데이터 Cosmos DB 저장 (문서 크기 trade-off 별도 검토)
- 멀티 세션 전환 UI
- 세션 삭제/아카이브

---

## 다음 세션 인수 요약

1. **PR #247 머지** — 체크리스트 403 수정, 테스트 완료 상태
2. **`PARK-session-restore` 브랜치 생성** (`origin/main` 기반, PR #247 머지 후)
3. **Layer 1 먼저 구현** — sessionStorage persist (프론트만, 즉시 효과)
4. **Layer 2 구현** — 백엔드 API + 프론트 복원 (로그인 사용자 대상)
5. chart 저장은 Layer 2 완료 후 별도 판단
