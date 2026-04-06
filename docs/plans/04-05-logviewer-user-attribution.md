# 계획: 개발자 로그에 사용자 귀속 + 어드민 필터 뷰

## Context

현재 `/api/v1/logs`(queries.jsonl 등)에는 `session_id`만 기록되고 `user_id`는 없다.
회원 시스템이 도입된 지금, 어드민이 "어떤 사용자가 어떤 질의를 했는지"를 로그에서 직접 확인하고
사용자별로 필터링할 수 있어야 관리가 쉬워진다.

---

## 현재 상태

| 항목 | 현황 |
|------|------|
| 로그 저장 위치 | Azure Blob Storage (`queries.jsonl`, `rejections.jsonl`, `errors.jsonl`) |
| 로그 항목 식별자 | `session_id`, `request_id` — `user_id` **없음** |
| 세션↔유저 연결 | Cosmos `sessions` 컨테이너의 `user_id` 필드 (이번 세션에서 추가) |
| 프론트 API 호출 | JWT 헤더 미전송 (API Key만 전송) |
| LogViewer 필터 | 로그 타입(쿼리/거부/오류)만 존재, 사용자 필터 없음 |

---

## 구현 계획

### Phase 1 — 로그 쓰기 시 user_id 기록 (백엔드)

#### 1-1. `logger.py`
`log_query()`, `log_error()` 함수 시그니처에 `user_id: str = ""` 파라미터 추가.
JSONL 항목에 `"user_id"` 필드 포함:
```json
{
  "ts": "...",
  "session_id": "...",
  "user_id": "google:1234567890",   ← 신규
  "request_id": "...",
  ...
}
```

#### 1-2. `api_server.py` (stream / query 엔드포인트)
`get_optional_user()` 의존성(이미 `auth_router.py`에 구현됨) 추가.
```python
@app.post("/api/v1/stream", dependencies=[Depends(verify_api_key)])
async def stream(req: QueryRequest, user: dict | None = Depends(get_optional_user)):
    user_id = user["sub"] if user else ""
    ...
    await log_query(..., user_id=user_id)
```
비회원은 `user_id=""`로 기록 — 기존 동작 유지.

#### 1-3. `frontend/src/api.js`
`streamQuery()` / `sendQuery()` 함수에서 localStorage의 JWT를 읽어
`Authorization: Bearer <token>` 헤더를 선택적으로 추가:
```js
const jwt = localStorage.getItem("sohobi_jwt");
if (jwt) headers["Authorization"] = `Bearer ${jwt}`;
```
비로그인 시에는 헤더 없음 → 서버에서 `user_id=""` 처리.

---

### Phase 2 — 로그 조회 시 사용자 정보 enrichment (백엔드)

#### 2-1. `api_server.py` — `/api/v1/logs` 확장
쿼리 파라미터 추가:
- `user_id: str | None` — 특정 사용자 로그만 필터

응답 항목 enrichment 로직:
1. 항목에 `user_id` 있으면 → `users` 컨테이너에서 `email`, `name` 조회
2. `user_id` 없지만 `session_id` 있으면 → `sessions` 컨테이너에서 `user_id` 조회 후 위 반복 (레거시 데이터 소급 적용)
3. 어느 쪽도 없으면 → `user_email: "비회원"`

반환 항목에 추가되는 필드:
```json
{
  "user_id": "google:xxx",
  "user_email": "user@example.com",
  "user_name": "홍길동"
}
```

성능 고려: session_id → user_id 매핑을 요청당 한 번만 조회 (중복 session_id 캐싱).

#### 2-2. 새 엔드포인트 `GET /api/admin/users`
어드민 전용 (API Key 필요). `users` 컨테이너 전체 목록 반환:
```json
[{"user_id": "google:xxx", "email": "...", "name": "...", "created_at": "..."}]
```
LogViewer 필터 드롭다운 데이터 소스로 사용.

---

### Phase 3 — LogViewer UI 확장 (프론트엔드)

#### 3-1. `LogViewer.jsx`
- 상단에 사용자 필터 드롭다운 추가: `/api/admin/users` 로 목록 로드
- 선택 시 `user_id` 쿼리 파라미터와 함께 `/api/v1/logs` 재요청
- "전체 사용자" 옵션 포함 (기본값)

#### 3-2. `LogTable.jsx`
"사용자" 컬럼 추가 (그레이드 배지 옆):
- 로그인 사용자: `user_name` (또는 `user_email` truncated)
- 비회원: 회색 "비회원" 뱃지

---

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `integrated_PARK/logger.py` | `log_query()`, `log_error()`에 `user_id` 파라미터 추가 |
| `integrated_PARK/api_server.py` | stream/query에 `get_optional_user` 의존성, `/api/v1/logs` 필터+enrichment, `/api/admin/users` 신규 |
| `frontend/src/api.js` | JWT 헤더 조건부 전송 |
| `frontend/src/pages/LogViewer.jsx` | 사용자 필터 드롭다운 |
| `frontend/src/components/LogTable.jsx` | "사용자" 컬럼 추가 |

---

## 비회원 접근성 영향 없음

- 로그인 없이 사용 시 `user_id=""` — 기존 동작 그대로
- `/api/v1/query`, `/api/v1/stream` 인증 요건 변경 없음 (API Key만 필요)

---

## 검증 방법

| TC | 방법 |
|----|------|
| user_id 기록 | 로그인 후 질의 → Blob Storage `queries.jsonl`에 `user_id` 필드 확인 |
| 비회원 기록 | 비로그인 질의 → `user_id: ""` 기록 확인 |
| 로그 enrichment | `/api/v1/logs` 응답에 `user_email` 필드 포함 확인 |
| 사용자 필터 | LogViewer → 드롭다운에서 사용자 선택 → 해당 사용자 로그만 표시 |
| 레거시 소급 | 기존 세션(user_id 없는 로그) → session_id로 user_id 조회 후 표시 |
