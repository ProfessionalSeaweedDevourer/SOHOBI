# LogViewer 응답자 계정명 표시 및 사용자별 필터링 개편

## Context

관리자용 LogViewer(`/logs`)에서 각 로그 항목의 응답자(세션 소유자)가 누구인지 알 수 없고, 특정 사용자의 기록만 골라볼 방법이 없다. MyLogs/MyReport(개인용)와 대칭되는 관리자 뷰를 완성하는 작업이다.

**현황 Gap:**
- JSONL 로그(`queries.jsonl` 등)에 `user_id`/`email` 미포함 — `session_id`만 있음
- `/api/v1/logs` 엔드포인트에 사용자 필터 파라미터 없음
- LogTable 컴포넌트에 응답자 컬럼 없음
- 단, `session_store.py`의 세션 item에는 `user_id` 필드가 있음 (link_session_to_user로 귀속)

---

## 구현 계획

### Phase 1 — 백엔드: 로그에 user_id 기록

#### 1-1. `integrated_PARK/logger.py`
`log_query()` 시그니처에 `user_id: str = ""` 추가, record dict에 포함

```python
def log_query(*, request_id, session_id="", user_id="", question, ...):
    record = {
        "ts": ..., "session_id": session_id, "user_id": user_id, ...
    }
```

#### 1-2. `integrated_PARK/session_store.py`
`get_query_session()` 반환 dict에 `user_id` 필드 추가:
```python
return {
    ...,
    "user_id": item.get("user_id", ""),  # 추가
}
```

신규 함수 추가 (기존 로그의 session_id → user_id 역조회용):
```python
async def get_user_id_by_session(session_id: str) -> str:
    # Cosmos 또는 인메모리에서 user_id 반환, 없으면 ""
```

#### 1-3. `integrated_PARK/api_server.py`
`log_query()` 호출부 2곳(~L278, ~L408)에 `user_id` 전달:
```python
log_query(..., user_id=session.get("user_id", ""), ...)
```

### Phase 2 — 백엔드: 사용자 정보 조회 및 API 확장

#### 2-1. `integrated_PARK/auth_router.py`
공용 함수 추가 (캐시 포함):
```python
_USER_INFO_CACHE: dict[str, tuple[float, dict]] = {}

async def get_user_info(user_id: str) -> dict:
    # 5분 TTL 캐시 → Cosmos users 컨테이너 조회
    # 반환: {"email": ..., "name": ...}
```

#### 2-2. `integrated_PARK/api_server.py` — `/api/v1/logs` 확장

`user_id: str = ""` 쿼리 파라미터 추가 + enrichment 로직:

```
entries = load_entries_json(type, limit=0)  # 전체 로드 후 필터
↓
session_ids 중 user_id 없는 것 → get_user_id_by_session() 일괄 조회
↓
unique user_ids → get_user_info() 일괄 조회 (dedup)
↓
entries에 user_id, user_email, user_name 병합
↓
user_id 필터 적용 → limit 적용 → 반환
```

#### 2-3. `integrated_PARK/api_server.py` — `/api/v1/logs/users` 신규 엔드포인트

```python
@app.get("/api/v1/logs/users", dependencies=[Depends(verify_api_key)])
async def get_log_users():
    # queries.jsonl 전체에서 unique user_id 추출 후 user_info 조회
    # 반환: {"count": N, "users": [{"user_id", "email", "name"}, ...]}
```

결과는 300초 TTL 인메모리 캐시 적용.

### Phase 3 — 프론트엔드

#### 3-1. `frontend/src/api.js`
```javascript
export async function fetchLogs(type = "queries", limit = 500, userId = "") {
  const params = new URLSearchParams({ type, limit });
  if (userId) params.append("user_id", userId);
  // ...
}

export async function fetchLogUsers() {
  // GET /api/v1/logs/users
}
```

#### 3-2. `frontend/src/pages/LogViewer.jsx`

추가할 state:
```javascript
const [users, setUsers] = useState([]);
const [selectedUser, setSelectedUser] = useState("");
```

- 마운트 시 `fetchLogUsers()` 호출 → `users` 세팅
- `useEffect([tab, selectedUser])` — 탭 또는 필터 변경 시 로그 재조회
- 탭 바 하단에 필터 UI 삽입:
  ```
  [응답자 필터: ▼ 전체 응답자] [초기화]
  ```

#### 3-3. `frontend/src/components/LogTable.jsx`

목록 항목 메타 행(~L80 `div`)에 응답자 표시 추가:
```jsx
{(entry.user_name || entry.user_email) && (
  <span className="text-xs text-muted-foreground truncate max-w-[120px]"
        title={entry.user_email}>
    👤 {entry.user_name || entry.user_email}
  </span>
)}
```

상세 패널(`EntryDetail`)에도 동일하게 추가.

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|---------|
| `integrated_PARK/logger.py` | `log_query()`에 `user_id` 파라미터 추가 |
| `integrated_PARK/session_store.py` | `get_query_session()` 반환에 `user_id` 추가, `get_user_id_by_session()` 신규 |
| `integrated_PARK/auth_router.py` | `get_user_info()` 공용 함수 + 5분 캐시 추가 |
| `integrated_PARK/api_server.py` | `log_query()` 호출 2곳 수정, `/api/v1/logs` 확장, `/api/v1/logs/users` 신규 |
| `frontend/src/api.js` | `fetchLogs(userId)` 수정, `fetchLogUsers()` 추가 |
| `frontend/src/pages/LogViewer.jsx` | 사용자 목록 로드, `selectedUser` state, 필터 드롭다운 UI |
| `frontend/src/components/LogTable.jsx` | 목록·상세 패널에 응답자 표시 컬럼 추가 |

---

## 주의사항

- **기존 로그 커버**: JSONL에 `user_id` 없는 기존 항목은 `session_id → user_id` 역조회로 보완. 단 세션 TTL(24h) 만료 시 조회 불가 → Phase 1 적용 후 신규 로그부터는 완전 커버
- **Cosmos 비용**: user_id dedup + 인메모리 캐시로 과도한 RU 방지
- **`load_entries_json` 캐시**: 60초 TTL 기존 캐시 유지. user_id 필터는 캐시 키에 포함하지 않고 핸들러 레벨에서 적용
- **동기/비동기 혼재**: `log_formatter.py`는 동기 함수로 유지, enrichment는 async FastAPI 핸들러에서만 수행

---

## 검증 방법

1. **백엔드 API 확인**:
   ```bash
   source integrated_PARK/.env
   curl -H "X-API-Key: $API_KEY" "$BACKEND_HOST/api/v1/logs/users"
   curl -H "X-API-Key: $API_KEY" "$BACKEND_HOST/api/v1/logs?type=queries&user_id=google:12345"
   ```

2. **로그 enrichment 확인**: 새 쿼리 실행 후 `/api/v1/logs` 응답에 `user_email`, `user_name` 필드 포함 여부 확인

3. **프론트엔드 UI**: playwright로 `/logs` 접속 → 드롭다운에 사용자 목록 표시 → 선택 시 해당 사용자 로그만 표시 확인
