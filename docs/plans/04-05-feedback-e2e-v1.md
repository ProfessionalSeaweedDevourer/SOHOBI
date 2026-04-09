# 세션 5 작업 플랜 — 피드백 시스템 E2E 검증 + report_router 보강

## Context

세션 4에서 피드백 시스템(InlineFeedback, 이벤트 추적, 체크리스트, 사용 리포트, 로드맵 투표) 전체 구현이 완료됐고, 투표 보안 취약점도 수정됐다. PR #148 머지 대기 중이며, 배포된 피드백 시스템 기능들이 실제 UI에서 정상 작동하는지 E2E 검증이 이번 세션의 핵심 작업이다.

추가로 `report_router.py`에 스펙 정의 필드(`top_negative_tags`, `first_active`, `last_active`)가 누락된 상태라 함께 보강한다.

---

## Phase 1: PR #148 머지 확인

```bash
gh pr view 148 --repo ProfessionalSeaweedDevourer/SOHOBI
```

- MERGED → Phase 2 진행
- OPEN → 현재 브랜치 상태 확인 후 머지 요청 또는 대기
- CLOSED → 재생성 필요

---

## Phase 2: E2E Playwright 검증

배포 환경 기준 (`<BACKEND_HOST>`)

프론트엔드 URL은 `integrated_PARK/.env`의 `FRONTEND_URL` 확인 필요.

### 검증 순서 및 셀렉터

| TC | 기능 | 흐름 |
|----|------|------|
| TC-F1 | InlineFeedback 👍 → 즉시 제출 | `browser_navigate` → `/user` → 질문 입력 → 응답 대기 → `button[aria-label="도움이 됐어요"]` 클릭 → "✓ 피드백 완료" 확인 |
| TC-F2 | InlineFeedback 👎 → 태그 선택 → 제출 | `button[aria-label="아쉬워요"]` → 태그 펼침 확인 → "정확하지 않음" 클릭 → "제출" 클릭 → "✓ 피드백 완료" 확인 |
| TC-C1 | 체크리스트 자동 체크 | "상권 분석해줘" 류 질문 → complete 이벤트 후 → `GET /api/checklist/{sid}` 응답에 `location.checked: true` 확인 |
| TC-C2 | 체크리스트 수동 토글 | `button[aria-label*="업종 결정"]` 클릭 → 낙관적 UI 반영 → PATCH 성공 확인 |
| TC-R1 | /my-report 페이지 렌더링 | `browser_navigate` → `/my-report` → ReportSummary, AgentUsageChart 컴포넌트 표시 확인 |
| TC-R2 | report API 집계 정확성 | `GET /api/report/{sid}` → `total_queries`, `feedback`, `checklist`, `agent_usage` 필드 존재 확인 |

### FAIL 처리 규칙
- FAIL 발견 즉시 원인 파악 → 수정 → 동일 브랜치 커밋 → 재테스트

---

## Phase 3: report_router 보강 (선택 → 권장)

E2E 전체 PASS 후 진행.

### 수정 파일

**`integrated_PARK/report_router.py`**

#### 1. `_aggregate_feedback()` 수정 (top_negative_tags 추가)

```python
from collections import Counter

# 기존 positive/negative 집계 루프 내에 추가
tag_counter = Counter()
for doc in feedback_docs:
    if doc.get("feedback_type") == "negative" and doc.get("tags"):
        tag_counter.update(doc["tags"])

top_negative_tags = [
    {"tag": tag, "count": count}
    for tag, count in tag_counter.most_common(5)
]
# 반환값에 top_negative_tags 추가
```

#### 2. `_aggregate_events()` 수정 (first_active, last_active 추가)

```python
# 이벤트 문서의 타임스탬프 수집
timestamps = [
    doc.get("timestamp") or doc.get("created_at")
    for doc in event_docs
    if doc.get("timestamp") or doc.get("created_at")
]
first_active = min(timestamps) if timestamps else None
last_active = max(timestamps) if timestamps else None
# 반환값에 포함
```

#### 3. 최종 응답에 summary 객체 추가

```python
return {
    "session_id": session_id,
    "summary": {
        "first_active": first_active,
        "last_active": last_active,
    },
    "total_queries": total_queries,
    "agent_usage": agent_usage,
    "feedback": {
        ...,
        "top_negative_tags": top_negative_tags,
    },
    "checklist": checklist,
}
```

---

## Phase 4: 커밋 및 PR

```bash
# 커밋 메시지 형식
feat: report API에 top_negative_tags, first/last_active 필드 추가
```

- PARK 브랜치에 커밋
- `gh pr list --head PARK --state open` 으로 기존 PR 확인
  - 기존 PR 있으면 해당 PR에 반영 보고
  - 없으면 새 PR 생성

---

## 검증 체크리스트

- [ ] PR #148 상태 확인
- [ ] TC-F1: 👍 → "✓ 피드백 완료" ✅
- [ ] TC-F2: 👎 → 태그 → 제출 → "✓ 피드백 완료" ✅
- [ ] TC-C1: 자동 체크 키워드 질문 → 체크리스트 자동 갱신 ✅
- [ ] TC-C2: 수동 토글 → PATCH 성공 ✅
- [ ] TC-R1: /my-report 페이지 정상 렌더링 ✅
- [ ] TC-R2: /api/report/{sid} 필드 검증 ✅
- [ ] report_router 보강 후 TC-R2 재검증 (summary 필드 포함)

---

## 핵심 파일

| 파일 | 작업 |
|------|------|
| `integrated_PARK/report_router.py` | top_negative_tags, first/last_active 추가 |
| `frontend/src/pages/UserChat.jsx` | TC-F1/F2, TC-C1/C2 E2E 검증 대상 |
| `frontend/src/pages/MyReport.jsx` | TC-R1 E2E 검증 대상 |
| `frontend/src/components/feedback/InlineFeedback.jsx` | E2E 셀렉터 기준 |
| `frontend/src/components/checklist/ChecklistItem.jsx` | E2E 셀렉터 기준 |
