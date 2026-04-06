# 로그 뷰어: 사용자 피드백 표시 + 서버 부하 검토

## Context

인라인 피드백 위젯(계층 2)이 구현되어 Cosmos DB에 피드백 데이터가 쌓이고 있으나,
개발자 모드 로그 뷰어에서는 해당 피드백을 볼 수 없는 상태다.
각 쿼리 로그 상세 항목에 사용자 피드백(👍/👎, 태그)을 함께 표시해 운영 인사이트를 높인다.

별개로, 로그 뷰어 요청이 Azure Blob Storage를 매번 풀 다운로드하는 구조임을 확인했다.
백엔드 레벨에서 TTL 캐시를 추가해 불필요한 Blob 요청을 줄인다.

---

## 발견된 문제점

### 1. 서버 부하 (Blob Storage 과도 호출)
- `_load_jsonl()` (`log_formatter.py:54-78`) — 매 요청마다 Azure Blob Storage blob 전체를 동기 HTTP로 다운로드 후 파싱·정렬
- 프론트엔드 기본 limit = **500** (`api.js:97`) — 탭 전환, 새로고침, 전체 다운로드 시 각각 Blob 호출 발생
- 캐시 없음 → 동시 다중 탭/빠른 탭 전환 시 Blob 호출 폭증 가능
- 동기 I/O가 async FastAPI 이벤트 루프를 블로킹

### 2. 피드백 데이터 미표시
- 피드백은 Cosmos DB `feedback` 컨테이너에 저장 (`feedback_router.py:75-97`)
- 조인 키: `feedback.message_id == log.request_id`
- GET 엔드포인트 없음 → 로그 뷰어에서 피드백 조회 불가

---

## 구현 계획

### Step 1 — 백엔드: 로그 TTL 캐시 (log_formatter.py)

`load_entries_json()` 결과를 타입별로 60초 TTL 인메모리 캐시에 저장.
외부 라이브러리 없이 `dict + time.time()` 패턴 사용.

```python
_CACHE: dict[str, tuple[float, list]] = {}   # {log_type: (expires_at, entries)}
_CACHE_TTL = 60  # seconds

def load_entries_json(log_type, limit=50):
    now = time.time()
    if log_type in _CACHE and _CACHE[log_type][0] > now:
        entries = _CACHE[log_type][1]
    else:
        entries = _load_jsonl(...)  # 기존 로직
        entries.sort(...)
        _CACHE[log_type] = (now + _CACHE_TTL, entries)
    return entries[:limit] if limit > 0 else entries
```

- 수정 파일: `integrated_PARK/log_formatter.py`
- limit=0 (전체 다운로드) 포함 모두 캐시 활용

### Step 2 — 백엔드: 피드백 GET 엔드포인트 (feedback_router.py)

`GET /api/feedback?limit=500` 추가. Cosmos DB에서 최근 N건 조회, 폴백은 인메모리 리스트에서 반환.

```python
@router.get("/api/feedback")
async def get_feedback(limit: int = 500):
    container = await _get_feedback_container()
    if container is not None:
        items = container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True,
            max_item_count=limit
        )
        results = [item async for item in items.by_page().__aiter__().__anext__()]
    else:
        results = _feedback_fallback[-limit:]
    return {"count": len(results), "items": results}
```

- 인증: 기존 `app.include_router(feedback_router, dependencies=[Depends(verify_api_key)])` 그대로 적용됨
- 수정 파일: `integrated_PARK/feedback_router.py`

### Step 3 — 프론트엔드: API 함수 추가 (api.js)

```js
export async function fetchFeedback(limit = 500) {
  const res = await fetch(`${BASE_URL}/api/feedback?limit=${limit}`, { headers: _AUTH_HEADERS });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

- 수정 파일: `frontend/src/api.js`

### Step 4 — 프론트엔드: LogViewer에서 피드백 로드 (LogViewer.jsx)

로그 로드 시 피드백도 함께 fetch → `Map<message_id, feedback>` 생성 → LogTable에 prop으로 전달.

```js
const [feedbackMap, setFeedbackMap] = useState(new Map());

async function load(type) {
  // 기존 로그 fetch ...
  try {
    const fb = await fetchFeedback();
    const map = new Map(fb.items.map(f => [f.message_id, f]));
    setFeedbackMap(map);
  } catch { /* 피드백 실패는 조용히 무시 */ }
}

// LogTable에 feedbackMap 전달
<LogTable entries={entries} loading={loading} feedbackMap={feedbackMap} />
```

- 수정 파일: `frontend/src/pages/LogViewer.jsx`

### Step 5 — 프론트엔드: EntryDetail에 피드백 섹션 (LogTable.jsx)

`EntryDetail` 컴포넌트(`LogTable.jsx:123`)에 피드백 표시 섹션 추가.
`feedbackMap.get(entry.request_id)` 로 조회.

표시 형태 (최종 draft 바로 위):
```
사용자 피드백
  👍 긍정 / 👎 부정 — <timestamp>
  태그: 정확하지 않음, 정보가 부족함   ← 부정일 때만
```

피드백 없는 경우 섹션 자체를 렌더링하지 않음.

- 수정 파일: `frontend/src/components/LogTable.jsx`

---

## 수정 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/log_formatter.py` | 60초 TTL 캐시 추가 |
| `integrated_PARK/feedback_router.py` | GET /api/feedback 엔드포인트 추가 |
| `frontend/src/api.js` | `fetchFeedback()` 함수 추가 |
| `frontend/src/pages/LogViewer.jsx` | 피드백 fetch + feedbackMap 상태 추가 |
| `frontend/src/components/LogTable.jsx` | feedbackMap prop + EntryDetail 피드백 섹션 |

---

## 검증 방법

1. **캐시 동작 확인**
   ```bash
   # 연속 2회 호출 → 두 번째는 캐시 히트 (응답 시간 현저히 짧아야 함)
   time curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" -H "X-API-Key: $API_KEY" > /dev/null
   time curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" -H "X-API-Key: $API_KEY" > /dev/null
   ```

2. **피드백 GET 엔드포인트 확인**
   ```bash
   curl -s "$BACKEND_HOST/api/feedback?limit=10" -H "X-API-Key: $API_KEY" | python3 -m json.tool
   ```

3. **UI 확인** — playwright MCP
   - 개발자 모드 → 로그 뷰어 → 전체 요청 탭
   - 피드백이 있는 쿼리 항목 클릭 → 상세에 피드백 섹션 표시 확인
   - 피드백 없는 항목 → 피드백 섹션 미표시 확인
