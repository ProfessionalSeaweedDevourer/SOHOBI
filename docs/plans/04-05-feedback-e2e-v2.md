# 세션 5 작업 플랜 — 피드백 시스템 E2E 검증 + report_router 보강

## Context

세션 4에서 피드백 시스템(인라인 피드백 / 이벤트 추적 / 체크리스트 / 사용 리포트 / 로드맵 투표) 전체 구현이 완료되고 투표 보안 취약점까지 수정됨. PR #148이 오픈 중이며 머지 대기 상태. 본 세션은 배포 환경에서 E2E 검증 후 PR 머지, 그리고 report_router 누락 필드 보강을 목표로 한다.

---

## 작업 순서

### 작업 1: PR #148 머지 (5분)

1. `gh pr view 148` 로 PR 상태·CI 결과 확인
2. CI PASS → `gh pr merge 148 --squash` (또는 팀 규칙에 따라)
3. `git pull origin main` 후 `git rebase main` 으로 PARK 브랜치 최신화

---

### 작업 2: E2E Playwright 검증 (최우선)

배포 환경 기준. `source integrated_PARK/.env` 로 BACKEND_HOST, FRONTEND_URL 로드.

#### TC-F1: InlineFeedback 👍 클릭

- `browser_navigate` → `$FRONTEND_URL/user`
- 질문 입력 후 응답 생성 대기
- 응답 하단 👍 버튼 클릭
- "감사합니다" 메시지 노출 확인 (완료 상태)
- API: `POST /api/feedback` 200 응답 확인

#### TC-F2: InlineFeedback 👎 클릭 → 태그 선택 → 제출

- 동일 페이지에서 👎 클릭
- 태그 패널 펼침 확인 (`FeedbackTags.jsx`)
- 태그 1개 선택 → 제출
- "감사합니다" 노출 확인

#### TC-C1: 체크리스트 자동 체크

- 체크리스트 트리거 키워드 포함 질문 전송
- `GET $BACKEND_HOST/api/checklist/{session_id}` 응답에서 완료된 항목 증가 확인

#### TC-C2: 체크리스트 수동 토글

- `PATCH $BACKEND_HOST/api/checklist/{session_id}` 직접 호출
- 응답 200 + 변경된 상태 확인

#### TC-R1: /my-report 페이지 렌더링

- `browser_navigate` → `$FRONTEND_URL/my-report`
- ReportSummary, AgentUsageChart, Recommendations 3개 컴포넌트 모두 표시 확인

#### TC-R2: report API 집계 정확성

- `GET $BACKEND_HOST/api/report/{session_id}` 직접 호출
- 응답 필드 확인: `session_id`, `total_queries`, `agent_usage`, `feedback.positive_rate`, `checklist.progress_pct`

FAIL TC → 즉시 수정 후 동일 브랜치 커밋 → 재테스트

---

### 작업 3: report_router 누락 필드 보강 (선택)

**파일**: `integrated_PARK/report_router.py`

#### 3-1. `_aggregate_events()` — `last_active` / `first_active` 추가

현재 반환: `{ total, by_agent }`
목표 반환: `{ total, by_agent, last_active, first_active }`

```python
# Cosmos DB 쿼리에 MAX/MIN _ts 추가
SELECT MAX(c._ts) AS last_ts, MIN(c._ts) AS first_ts
FROM c WHERE c.session_id = @sid
```

반환 시 ISO 8601 문자열로 변환 (`datetime.utcfromtimestamp(ts).isoformat() + "Z"`)

#### 3-2. `_aggregate_feedback()` — `top_negative_tags` 추가

현재 반환: `{ positive, negative, total, positive_rate }`
목표 반환: 위 + `top_negative_tags: [{"tag": str, "count": int}, ...]`

```python
from collections import Counter
tag_counter = Counter()
for doc in negative_docs:
    for tag in doc.get("tags", []):
        tag_counter[tag] += 1
top_negative_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(5)]
```

#### 3-3. 프론트엔드 표시 (선택)

`frontend/src/components/report/ReportSummary.jsx` 에 `last_active` 날짜 표시 추가 (있을 때만)

---

## 검증 방법

1. E2E TC 전체 PASS 확인
2. `GET $BACKEND_HOST/api/report/{session_id}` 응답에 `top_negative_tags`, `last_active`, `first_active` 포함 확인
3. `/my-report` 페이지에서 보강된 데이터 렌더링 확인

---

## 수정 대상 파일

| 파일 | 작업 |
|------|------|
| `integrated_PARK/report_router.py` | `_aggregate_events()`, `_aggregate_feedback()` 보강 |
| `frontend/src/components/report/ReportSummary.jsx` | `last_active` 표시 (선택) |

---

## 커밋 & PR

- 작업 2 FAIL 수정 시: `fix: 피드백 E2E 검증 실패 수정`
- 작업 3 완료 시: `feat: report API top_negative_tags / last_active / first_active 추가`
- 브랜치: `PARK` → PR to `main`
