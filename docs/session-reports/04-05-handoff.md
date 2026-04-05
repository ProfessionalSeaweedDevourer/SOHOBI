# 세션 인수인계 — 2026-04-05

## 브랜치 및 PR

- **작업 브랜치**: `PARK`
- **열린 PR**: [#137](https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/137) — SWA 프록시 복구 + 인라인 피드백 위젯

---

## 이번 세션 완료 내용 — 계층 2: 인라인 피드백 위젯

### 신규 파일
| 파일 | 설명 |
|------|------|
| `frontend/src/components/feedback/feedbackConstants.js` | 태그 목록, UI 문구 상수 |
| `frontend/src/components/feedback/useFeedbackSubmit.js` | fetch 기반 전송 훅 |
| `frontend/src/components/feedback/FeedbackTags.jsx` | 태그 선택 UI |
| `frontend/src/components/feedback/InlineFeedback.jsx` | 메인 피드백 위젯 |
| `integrated_PARK/feedback_router.py` | `POST /api/feedback` FastAPI 라우터 |

### 수정 파일
- `frontend/src/components/ResponseCard.jsx` — InlineFeedback 통합, `sessionId`/`messageId` props 추가
- `frontend/src/pages/UserChat.jsx` — messages에 `requestId`/`sessionId` 저장
- `integrated_PARK/api_server.py` — `feedback_router` 등록

### 동작 방식
- 에이전트 응답 완료 후 응답 하단에 👍/👎 버튼 표시 (에러 응답은 제외)
- 👍: 즉시 전송 → "의견 감사합니다!" → 1.5초 후 "✓ 피드백 완료"
- 👎: 태그 선택 영역 펼침 → 1개 이상 선택 후 제출
- Cosmos DB `feedback` 컨테이너 저장 (파티션: `/agent_type`), 로컬 인메모리 폴백 지원
- 피드백 전송 실패 시 `console.warn`만 — UX 영향 없음

---

## 미완료 작업 — 다음 세션 계획

### 세션 2 — 계층 3-A: 사용 이벤트 추적
**목표**: 사용자 행동 데이터 수집 (질문 전송, 응답 조회, 기능 방문)

구현 대상:
1. `frontend/src/utils/trackEvent.js` 생성
   - `trackEvent(eventName, payload)` — fetch 기반, 실패 무시
2. `integrated_PARK/event_router.py` 생성
   - `POST /api/events` — Cosmos DB `usage_events` 컨테이너 (파티션: `/session_id`)
3. 기존 코드에 이벤트 삽입:
   - `agent_query`: `UserChat.jsx`의 `handleSubmit` 함수 내 질문 전송 시점
   - `agent_response_view`: `ResponseCard.jsx`의 `useEffect` 마운트 시점
   - `feature_discovery`: 각 페이지 컴포넌트 마운트 시 (`useEffect(fn, [])`)

### 세션 3 — 계층 3-B: 창업 준비 체크리스트
**목표**: 사용자의 창업 준비 진행률 시각화

구현 대상:
1. `frontend/src/constants/checklistItems.js` — 8개 항목 정의 (autoCheckKeywords 포함)
2. `frontend/src/components/checklist/` — `StartupChecklist.jsx`, `ChecklistItem.jsx`, `ChecklistProgress.jsx`, `useChecklistState.js`
3. 백엔드: `GET /api/checklist/{session_id}`, `PATCH /api/checklist/{session_id}`
4. 백엔드 후처리: orchestrator.py에서 응답 생성 시 autoCheckKeywords 매칭 → `source: "auto"` 체크

### 세션 4 — 계층 3-C: 사용 리포트
**목표**: `/my-report` 페이지 — 개인 사용 통계 시각화

구현 대상:
1. `GET /api/report/{session_id}` — usage_events/feedback/checklist 집계
2. `frontend/src/components/report/` — `UsageReport.jsx`, `ReportSummary.jsx`, `AgentUsageChart.jsx`, `Recommendations.jsx`
3. React Router에 `/my-report` 경로 추가

### 세션 5 — 계층 3-D: 로드맵 투표 위젯
**목표**: 기능 후보 투표 UI (우선순위 최하위)

---

## 다음 세션 시작 시 필독 사항

1. **플랜 파일 위치**: `~/.claude/plans/tidy-conjuring-hopper.md`
2. **원본 지시문**: `docs/plans/SOHOBI_피드백시스템_ClaudeCode_지시문.md`
3. **PR #137** 머지 여부 확인 후 세션 2 진행
4. 코드베이스 파악 결과는 플랜 파일에 기록되어 있으므로 탐색 에이전트 재실행 불필요

---

## 아키텍처 메모

- **agent_type 실제 키**: `admin`, `finance`, `legal`, `location`, `chat` (플랜 문서의 `financial`/`commercial`/`validator`와 다름)
- **Cosmos DB 패턴**: `session_store.py` 기준 — `azure.cosmos.aio`, `DefaultAzureCredential`, `create_container_if_not_exists`
- **HTTP 클라이언트**: `api.js` 기준 — 네이티브 `fetch`, `VITE_API_URL`, `X-API-Key` 헤더 (axios 미사용)
- **sessionId 흐름**: UserChat `useState` → SSE `domain_classified` 이벤트 수신 → `setSessionId()` → messages 저장 → ResponseCard props
