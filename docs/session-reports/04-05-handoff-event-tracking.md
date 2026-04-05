# 세션 인수인계 — 2026-04-05 (계층 3-A 완료)

## 브랜치 및 PR

- **작업 브랜치**: `PARK`
- **열린 PR**: [#138](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/138) — 사용 이벤트 추적 구현 (계층 3-A)

---

## 이번 세션 완료 내용 — 계층 3-A: 사용 이벤트 추적

### 신규 파일
| 파일 | 설명 |
|------|------|
| `frontend/src/utils/trackEvent.js` | `trackEvent(eventName, payload)` — fetch 기반, 실패 무시 |
| `integrated_PARK/event_router.py` | `POST /api/events` — Cosmos DB `usage_events` 컨테이너 저장 |

### 수정 파일
- `integrated_PARK/api_server.py` — event_router 등록
- `frontend/src/pages/UserChat.jsx` — `agent_query` (handleSubmit) + `feature_discovery` (마운트)
- `frontend/src/components/ResponseCard.jsx` — `agent_response_view` (useEffect 마운트, 에러 제외)
- `frontend/src/pages/Landing.jsx` — `feature_discovery`
- `frontend/src/pages/Home.jsx` — `feature_discovery`
- `frontend/src/pages/Features.jsx` — `feature_discovery`
- `frontend/src/pages/MapPage.jsx` — `feature_discovery`
- `frontend/src/components/map/MapView.jsx` — 지도 API fetch에 `X-API-Key` 헤더 추가

### 동작 방식
- 이벤트 전송 실패 시 try/catch 무시 — UX 영향 없음
- `session_id` null 허용 (질문 전송 시점에는 null일 수 있음), 백엔드에서 `"anonymous"` 폴백
- Cosmos DB 미설정 시 인메모리 폴백 (`_events_fallback: list`)

---

## 다음 세션 — 계층 3-B: 창업 준비 체크리스트

### 목표
사용자의 창업 준비 항목 8개를 체크리스트로 시각화. 에이전트 응답 키워드를 분석해 자동 체크, 수동 체크도 지원.

### 구현 대상

#### 1. 프론트엔드 상수 (`frontend/src/constants/checklistItems.js`)

```javascript
export const STARTUP_CHECKLIST = [
  { id: 'biz_registration',  label: '사업자등록 안내 확인',      agent: 'admin',    autoCheckKeywords: ['사업자등록', '사업자 등록', '통신판매업'] },
  { id: 'location_analysis', label: '희망 입지 상권 분석',        agent: 'location', autoCheckKeywords: ['상권', '입지', '유동인구', '임대료'] },
  { id: 'cost_simulation',   label: '초기 투자 비용 시뮬레이션',  agent: 'finance',  autoCheckKeywords: ['초기 비용', '투자 비용', '인테리어 비용', '보증금'] },
  { id: 'revenue_forecast',  label: '예상 매출/손익 시뮬레이션',  agent: 'finance',  autoCheckKeywords: ['매출', '손익', '수익', '손익분기'] },
  { id: 'hygiene_education', label: '위생교육 이수 안내 확인',    agent: 'admin',    autoCheckKeywords: ['위생교육', '식품위생', '위생 교육'] },
  { id: 'business_permit',   label: '영업신고 절차 확인',         agent: 'admin',    autoCheckKeywords: ['영업신고', '영업 신고', '영업허가'] },
  { id: 'legal_review',      label: '관련 법규 검토',             agent: 'legal',    autoCheckKeywords: ['법률', '법규', '규정', '식품위생법', '조례'] },
  { id: 'final_validation',  label: '최종 검증 리포트 생성',      agent: 'admin',    autoCheckKeywords: ['최종 검증', '검증 리포트', '종합 검증'] },
];
```

#### 2. 프론트엔드 컴포넌트 (`frontend/src/components/checklist/`)

| 파일 | 역할 |
|------|------|
| `StartupChecklist.jsx` | 체크리스트 메인 — `GET /api/checklist/{session_id}` 조회 후 렌더링 |
| `ChecklistItem.jsx` | 개별 항목 (체크박스 + 라벨 + 설명 + [바로가기 →]) |
| `ChecklistProgress.jsx` | 상단 프로그레스 바 (n/8 완료, %) |
| `useChecklistState.js` | 상태 관리 훅 — GET 조회 + PATCH 수동 체크 |

**배치 위치**: `UserChat.jsx` 사이드패널 또는 별도 `/checklist` 페이지.
기존 페이지 레이아웃을 읽고 자연스러운 위치 선택.

**수동 체크 흐름**: 사용자가 항목 클릭 → `PATCH /api/checklist/{session_id}?item_id=...&checked=true` → `source: "manual"`

#### 3. 백엔드 라우터 (`integrated_PARK/checklist_router.py`)

`feedback_router.py`와 동일한 싱글턴 + 인메모리 폴백 패턴.
- 컨테이너: `checklist`
- 파티션 키: `/session_id`
- 문서 ID: `checklist_{session_id}`

```python
# 스키마
GET  /api/checklist/{session_id}         → checklist 문서 조회 (없으면 빈 상태 반환)
PATCH /api/checklist/{session_id}        → body: { item_id, checked } → source: "manual"
POST /api/checklist/{session_id}/auto    → body: { item_id } → source: "auto"  (백엔드 내부 호출용)
```

Cosmos DB 문서 구조:
```json
{
  "id": "checklist_{session_id}",
  "session_id": "...",
  "items": {
    "biz_registration": { "checked": true, "source": "auto", "checked_at": "..." }
  },
  "updated_at": "..."
}
```

#### 4. 자동 체크 로직 (`integrated_PARK/orchestrator.py`)

응답 생성 완료 후 후처리 단계에 삽입. 질문 텍스트에서 `autoCheckKeywords` 매칭.

삽입 위치: `orchestrator.py`에서 `complete` 이벤트를 yield하기 직전.
`STARTUP_CHECKLIST`의 키워드 목록은 파이썬으로 별도 상수 파일 또는 `checklist_router.py` 내부에 정의.

```python
# 후처리 예시 (orchestrator.py 내)
async def _auto_check_checklist(session_id: str, question: str):
    """질문 텍스트에서 키워드 매칭 → 해당 항목 자동 체크"""
    # checklist_router의 auto-check 엔드포인트 호출
    # 또는 직접 Cosmos DB 업데이트
```

#### 5. `api_server.py` 등록

```python
from checklist_router import router as checklist_router
app.include_router(checklist_router)
```

---

## 다음 세션 이후 남은 계층

| 세션 | 계층 | 내용 |
|------|------|------|
| 세션 4 | 3-C | `/my-report` 페이지 — usage_events/feedback/checklist 집계 |
| 세션 5 | 3-D | 로드맵 투표 위젯 (우선순위 최하위) |

---

## 아키텍처 메모

- **agent_type 실제 키**: `admin`, `finance`, `legal`, `location`, `chat`
  (spec 문서의 `commercial`/`financial`/`validator`와 다름 — 코드베이스 기준 사용)
- **Cosmos DB 패턴**: `feedback_router.py` 기준 — `azure.cosmos.aio`, `DefaultAzureCredential`, `create_container_if_not_exists`
- **HTTP 클라이언트**: 네이티브 `fetch`, `VITE_API_URL`, `VITE_API_KEY` → `X-API-Key` 헤더
- **sessionId 흐름**: `UserChat.useState` → SSE `domain_classified` 이벤트 → `setSessionId()` → messages 저장 → ResponseCard props
- **trackEvent import**: `import { trackEvent } from '../utils/trackEvent'` (상대 경로 주의)

## 다음 세션 시작 시 필독 사항

1. **PR #138** 머지 여부 확인 후 세션 3 진행
2. `integrated_PARK/orchestrator.py`에서 `complete` 이벤트 yield 위치 파악 필요 (자동 체크 삽입 지점)
3. `UserChat.jsx`의 레이아웃 구조 확인 후 체크리스트 배치 위치 결정
4. 원본 지시문: `docs/plans/spec-피드백시스템-지시문.md` (계층 3-B 섹션)
