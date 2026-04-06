# 계층 3-B: 창업 준비 체크리스트 구현

## Context

소상공인 창업 지원 챗봇 SOHOBI에서 사용자의 창업 준비 진행률을 시각화하는 체크리스트 기능을 추가한다.
에이전트 응답 draft에서 키워드를 감지하여 관련 항목을 자동으로 체크하고, 사용자가 직접 수동으로도 토글할 수 있다.
계층 3-A(사용 이벤트 추적)는 이미 완료되었으며, 이번은 계층 3-B이다.

---

## 신규/수정 파일 목록

### 신규 (백엔드)
- `integrated_PARK/checklist_store.py` — Cosmos DB 접근 모듈, orchestrator가 직접 import
- `integrated_PARK/checklist_router.py` — `GET/PATCH /api/checklist/{session_id}` FastAPI 라우터

### 수정 (백엔드)
- `integrated_PARK/api_server.py` — checklist_router 등록, CORS PATCH 허용
- `integrated_PARK/orchestrator.py` — approved/escalated 분기 양쪽에 auto_check_items 삽입

### 신규 (프론트엔드)
- `frontend/src/constants/checklistItems.js` — 8개 항목 + autoCheckKeywords
- `frontend/src/components/checklist/useChecklistState.js` — 상태 관리 훅
- `frontend/src/components/checklist/ChecklistItem.jsx`
- `frontend/src/components/checklist/ChecklistProgress.jsx`
- `frontend/src/components/checklist/StartupChecklist.jsx`

### 수정 (프론트엔드)
- `frontend/src/pages/UserChat.jsx` — 레이아웃 변경 + 훅 연결

---

## 1. checklist_store.py (신규)

`feedback_router.py` / `event_router.py` 패턴을 동일하게 따른다.

```
Container : "checklist"
Partition : /session_id
TTL       : COSMOS_SESSION_TTL (기본값 86400)
```

**Cosmos DB 문서 스키마:**
```json
{
  "id": "<session_id>",
  "session_id": "<session_id>",
  "items": {
    "biz_type":    {"checked": false, "source": null, "checked_at": null},
    "location":    {"checked": false, "source": null, "checked_at": null},
    "capital":     {"checked": false, "source": null, "checked_at": null},
    "biz_reg":     {"checked": false, "source": null, "checked_at": null},
    "permit":      {"checked": false, "source": null, "checked_at": null},
    "labor":       {"checked": false, "source": null, "checked_at": null},
    "finance_sim": {"checked": false, "source": null, "checked_at": null},
    "lease":       {"checked": false, "source": null, "checked_at": null}
  },
  "ttl": 86400
}
```

**키워드 상수 (모듈 내 정의):**
```python
CHECKLIST_KEYWORDS: dict[str, list[str]] = {
    "biz_type":    ["업종", "업태", "일반음식점", "휴게음식점", "제과제빵", "소매업"],
    "location":    ["상권", "입지", "유동인구", "상가", "동네", "매장 위치"],
    "capital":     ["초기 자금", "창업 비용", "자본금", "투자금", "대출", "손익분기"],
    "biz_reg":     ["사업자등록", "사업자 등록", "세무서", "개인사업자", "법인"],
    "permit":      ["영업신고", "영업 신고", "위생교육", "허가", "인허가", "식품위생"],
    "labor":       ["직원", "아르바이트", "알바", "4대보험", "근로계약", "인건비"],
    "finance_sim": ["수익성", "손익", "매출", "순이익", "재료비", "시뮬레이션", "BEP"],
    "lease":       ["임대차", "임대 계약", "권리금", "보증금", "월세", "임차인"],
}
```

**공개 함수:**
```python
async def get_checklist(session_id: str) -> dict
    # 반환: {"session_id": str, "items": dict}
    # 없으면 기본값 반환 (저장하지 않음)

async def upsert_checklist(session_id: str, items: dict) -> None
    # items: {item_id: {checked, source, checked_at}}

async def auto_check_items(session_id: str, draft: str) -> list[str]
    # draft에서 CHECKLIST_KEYWORDS 매칭 → 미체크 항목만 "auto" 체크
    # 반환: 새로 체크된 item_id 목록
    # 인메모리 폴백 포함 (COSMOS_ENDPOINT 미설정 시)
```

**매칭 로직:** Python `in` 연산자, 단순 문자열 포함 검사 (형태소 분석기 불필요)

---

## 2. checklist_router.py (신규)

```python
router = APIRouter()

class ChecklistToggleRequest(BaseModel):
    item_id: str
    checked: bool
    source: str = "manual"

@router.get("/api/checklist/{session_id}")
async def get_checklist_state(session_id: str):
    # 반환: {"session_id", "items", "progress": int(0-8)}

@router.patch("/api/checklist/{session_id}")
async def toggle_checklist_item(session_id: str, body: ChecklistToggleRequest):
    # 반환: {"session_id", "item_id", "checked", "items"}
```

---

## 3. api_server.py 수정 (2곳)

**라우터 등록 (line 63 이후):**
```python
from checklist_router import router as checklist_router
# ...
app.include_router(checklist_router, dependencies=[Depends(verify_api_key)])
```

**CORS allow_methods (line 79):**
```python
allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
```

---

## 4. orchestrator.py 수정 (4곳)

**import 추가 (상단):**
```python
from checklist_store import auto_check_items as _auto_check
```

**수정 위치 A — run() approved 반환 (line 136):**
```python
if verdict["approved"]:
    checked_ids: list[str] = []
    if session_id and draft:
        try:
            checked_ids = await _auto_check(session_id, draft)
        except Exception:
            pass
    return {"status": "approved", ..., "checked_items": checked_ids}
```

**수정 위치 B — run() escalated 반환 (line 170):**
```python
checked_ids: list[str] = []
if session_id and draft:
    try:
        checked_ids = await _auto_check(session_id, draft)
    except Exception:
        pass
return {"status": "escalated", ..., "checked_items": checked_ids}
```

**수정 위치 C — run_stream() approved yield (line 326~347):**
```python
if verdict["approved"]:
    checked_ids: list[str] = []
    if session_id and draft:
        try:
            checked_ids = await _auto_check(session_id, draft)
        except Exception:
            pass
    yield {"event": "complete", "status": "approved", ..., "checked_items": checked_ids}
    return
```

**수정 위치 D — run_stream() escalated yield (line 361~380):**
```python
checked_ids: list[str] = []
if session_id and draft:
    try:
        checked_ids = await _auto_check(session_id, draft)
    except Exception:
        pass
yield {"event": "complete", "status": "escalated", ..., "checked_items": checked_ids}
```

---

## 5. checklistItems.js (신규)

8개 항목 (id, label, description, icon, autoCheckKeywords):

| id | label | icon |
|---|---|---|
| `biz_type` | 업종 결정 | 🏪 |
| `location` | 입지 선정 | 📍 |
| `capital` | 초기 자금 계획 | 💰 |
| `biz_reg` | 사업자 등록 | 📄 |
| `permit` | 영업 허가·신고 | ✅ |
| `labor` | 인력 채용 계획 | 👤 |
| `finance_sim` | 수익성 검토 | 📊 |
| `lease` | 임대차 계약 | 🤝 |

---

## 6. useChecklistState.js (신규)

```javascript
export function useChecklistState(sessionId) {
  // sessionId 생기면 GET /api/checklist/{session_id} 로 로드
  // toggleItem(itemId): PATCH 호출 + 낙관적 업데이트 (실패 시 롤백)
  // syncFromDraft(checkedIds): complete 이벤트 payload의 checked_items 반영 (API 미호출)
  return { items, progress, toggleItem, syncFromDraft, loading };
}
```

API 헤더: `X-API-Key: import.meta.env.VITE_API_KEY` (api.js 패턴 동일)
`sessionId === null`이면 로컬 상태만 유지.

---

## 7. ChecklistItem.jsx / ChecklistProgress.jsx / StartupChecklist.jsx

- **ChecklistItem**: 체크 아이콘 + 라벨 + "자동" 배지 (`source === "auto"`)
- **ChecklistProgress**: 진행률 바 + "N/8" 숫자 표시, 8/8 완료 시 "창업 준비 완료!" 메시지
- **StartupChecklist**: 헤더(접기/펼치기 토글) + ChecklistProgress + ChecklistItem 목록

---

## 8. UserChat.jsx 수정

현재 레이아웃:
```
<div flex-col>
  <header>
  <main max-w-3xl>   ← 대화 영역
  <footer>           ← 입력창
</div>
```

변경 후:
```
<div flex-col>
  <header>
  <div flex-row max-w-5xl>
    <main flex-1>           ← 대화 영역 (기존 내용 그대로)
    <aside hidden lg:block w-64>   ← 체크리스트 사이드패널
  </div>
  <footer max-w-5xl>        ← max-w 확장
</div>
```

**모바일 처리:** footer 최상단에 `lg:hidden` 진행률 바만 표시.

**훅 연결 (handleSubmit 내 complete 이벤트 처리):**
```javascript
if (eventName === "complete") {
  finalResult = data;
  if (data.checked_items?.length) {
    syncFromDraft(data.checked_items);
  }
}
```

---

## 구현 순서

1. `checklist_store.py` 작성
2. `checklist_router.py` 작성
3. `api_server.py` 수정 (라우터 등록 + CORS PATCH)
4. `orchestrator.py` 수정 (4곳)
5. `checklistItems.js` 작성
6. `checklist/` 컴포넌트 4개 작성
7. `UserChat.jsx` 레이아웃 + 훅 연결

---

## 검증 계획

### TC1 — 백엔드 GET (빈 상태)
```bash
source integrated_PARK/.env
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/checklist/test-session-123" | python3 -m json.tool
# 기대: items 8개 all false, progress: 0
```

### TC2 — 백엔드 PATCH (수동 체크)
```bash
curl -s -X PATCH -H "X-API-Key: $API_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"item_id":"biz_type","checked":true,"source":"manual"}' \
  "$BACKEND_HOST/api/checklist/test-session-123" | python3 -m json.tool
# 기대: biz_type.checked=true, source="manual"
```

### TC3 — 자동 체크 (orchestrator 통합)
```bash
curl -s -X POST -H "X-API-Key: $API_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"카페 영업신고 절차 알려줘"}' \
  "$BACKEND_HOST/api/v1/query" | python3 -m json.tool
# 기대: checked_items 배열에 "permit" 포함
```

### TC4 — 프론트엔드 UI (playwright)
```
browser_navigate → /user → 질문 전송 → 응답 완료 후 사이드패널에 체크리스트 표시 확인
```
