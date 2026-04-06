# 세션 6 작업 계획 — 스펙 미구현 완료 + 보안 수정

## Context

PR #149(report 누락 필드), #150(SWA config)이 main에 MERGED. PARK 브랜치는 origin/main 대비 diverge 상태.
이번 세션은 (1) 브랜치 리베이스, (2) 스펙 미구현 3개 완료, (3) IDOR·PII·입력값 검증 보안 수정.

---

## 선행 작업: PARK 브랜치 리베이스

```bash
git rebase origin/main
git push --force-with-lease origin PARK
```

---

## 작업 A: 스펙 미구현 3개

### A-1. `most_used_agent` 필드 추가

**파일**: `integrated_PARK/report_router.py`

`_aggregate_events()` 반환값에 추가:
```python
most_used = max(counts, key=counts.get) if counts else None
return {
    "total": total,
    "by_agent": dict(counts),
    "last_active": ...,
    "first_active": ...,
    "most_used_agent": {"type": most_used, "count": counts[most_used]} if most_used else None,
}
```
GET `/api/report/{session_id}` 엔드포인트 응답(라인 189~222)에 `most_used_agent` 전달.

### A-2. ReportSummary.jsx 2번 카드 교체

**파일**: `frontend/src/components/report/ReportSummary.jsx`

현재 2번 카드(👍 긍정 피드백 %)를 `most_used_agent`로 교체:
- prop `mostUsedAgent` 추가 (현재 props: `totalQueries`, `feedback`, `checklist`, `firstActive`, `lastActive`)
- 에이전트 타입 → 한국어 매핑 (admin→관리, finance→재무, legal→법률·세무, location→상권, chat→일반)
- 표시: "재무 에이전트" + "N회"
- null이면 "-" 표시

**파일**: `frontend/src/pages/MyReport.jsx`

`<ReportSummary>` 호출 시 `mostUsedAgent={report.most_used_agent}` prop 추가.

### A-3. `report_view` 이벤트 삽입

**파일**: `frontend/src/pages/MyReport.jsx`

useEffect 내 fetchReport 성공 시 (라인 34-43):
```javascript
import { trackEvent } from '../utils/trackEvent';
// ...
fetchReport(sessionId)
  .then((data) => {
    setReport(data);
    trackEvent('report_view', { session_id: sessionId });
  })
```

### A-4. `report_recommendation_click` 이벤트 삽입

**파일**: `frontend/src/components/report/Recommendations.jsx`

현재 props: `incompleteItems`. `sessionId` prop 추가 필요.

`<a>` 태그에 onClick 추가:
```javascript
import { trackEvent } from '../../utils/trackEvent';
// ...
<a
  href={rec.path}
  onClick={() => trackEvent('report_recommendation_click', {
    session_id: sessionId,
    item_id: rec.id,
    agent: rec.path,
  })}
  ...
>
```

**파일**: `frontend/src/pages/MyReport.jsx`

`<Recommendations>` 호출 시 `sessionId={sessionId}` prop 추가.

---

## 작업 B: 보안 수정 (별도 PR)

### B-1. IDOR 수정 — CRITICAL

**파일**: `integrated_PARK/checklist_router.py`, `integrated_PARK/report_router.py`

`session_store.session_exists()` (session_store.py:151-160) 패턴 적용:
```python
from session_store import session_exists

# 각 엔드포인트 시작 부분에 추가
if not await session_exists(session_id):
    raise HTTPException(status_code=403, detail="접근 권한 없음")
```
적용 대상:
- `checklist_router.py` GET `/api/checklist/{session_id}`
- `checklist_router.py` PATCH `/api/checklist/{session_id}`
- `report_router.py` GET `/api/report/{session_id}`

### B-2. PII 저장 비활성화 — HIGH

**파일**: `integrated_PARK/feedback_router.py`

저장 document 생성 시 null 처리:
```python
"conversation_context": None,  # PII 저장 비활성화
```

### B-3. 입력값 검증 강화 — MEDIUM

**파일**: `integrated_PARK/feedback_router.py`

FeedbackRequest 모델 수정:
```python
from pydantic import Field
from typing import Literal

class FeedbackRequest(BaseModel):
    session_id: str = Field(..., max_length=255)
    agent_type: Literal["admin", "finance", "legal", "location", "chat"]
    message_id: str = Field(..., max_length=255)
    feedback_type: Literal["positive", "negative"]
    tags: list[str] = Field(default=[], max_length=10)
    conversation_context: str | None = Field(None, max_length=2000)
    timestamp: str = Field(..., max_length=50)
```

### B-4. API_SECRET_KEY 배포 설정 확인 — HIGH

**파일**: `.github/workflows/deploy-backend.yml`

`API_SECRET_KEY` 환경변수가 설정되어 있는지 확인. 없으면 사용자에게 보고 (키 값은 GitHub Secrets 설정 필요).

---

## PR 전략

| PR | 내용 | 커밋 형식 |
|----|------|----------|
| 신규 (PARK→main) | A-1~A-4 스펙 완성 | `feat: 리포트 스펙 완성 (most_used_agent + 이벤트 트래킹)` |
| 신규 (PARK→main) | B-1~B-4 보안 수정 | `fix: 보안 취약점 수정 (IDOR·PII·입력검증)` |

---

## TC 검증 계획

| TC | 도구 | 검증 내용 |
|----|------|----------|
| TC-M1 | curl | GET /api/report → `most_used_agent` 필드 포함 |
| TC-M2 | Playwright network | /my-report 방문 시 `report_view` 이벤트 POST /api/events |
| TC-M3 | Playwright network | 추천 클릭 시 `report_recommendation_click` 이벤트 |
| TC-R1 | Playwright snapshot | /my-report 전체 렌더링 확인 |
| TC-S1 | curl | 존재하지 않는 session_id → 403 |
| TC-S2 | curl | POST /api/feedback → conversation_context null 저장 확인 |
| TC-S3 | curl | tags 11개 → 422 Validation Error |

---

## 수정 대상 파일

```
integrated_PARK/report_router.py
integrated_PARK/checklist_router.py
integrated_PARK/feedback_router.py
frontend/src/components/report/ReportSummary.jsx
frontend/src/components/report/Recommendations.jsx
frontend/src/pages/MyReport.jsx
.github/workflows/deploy-backend.yml  (확인만)
```
