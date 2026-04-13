# 세션 인수인계 — SurveyBanner 전역 통합 (2026-04-12)

## 세션 요약

MS Forms 사용자 설문 배너(`SurveyBanner`)를 Landing·UserChat·ChatPanel 3곳에 통합하는 작업을 시작했다. 사용자와 협의하여 **리팩터 우선 → 통합** 2-PR 전략으로 분리했고, 이 세션에서는 선행 리팩터(PR #1)를 완료했다. 후속 PR #2가 미완 상태.

## 완료 — PR #278 (머지됨)

`refactor: dismiss 로직 useDismissible 훅으로 통합`

- `frontend/src/hooks/useDismissible.js` 신규 추출 (local/session 저장소 선택 가능)
- UserChat tip 배너, 로그인 넛지, StartupChecklist 인트로 3곳의 중복 dismiss 로직 훅 호출로 치환
- storage key 불변 → 외부 동작 bit-identical
- 빌드 통과, TC1~3(UI 수동 검증)은 미실행 — 구조 변경만이므로 회귀 가능성 낮음

## 미완 — PR #2 예정

`feat/park-survey-banner` 브랜치에서 아래 작업이 남아 있음:

### 작업 내용

1. 레포 루트의 `SurveyBanner.jsx`를 `frontend/src/components/SurveyBanner.jsx`로 이동하면서 전면 리팩터링:
   - 인라인 `<style>` 블록 + `@import url(Pretendard)` 제거 → Tailwind + `glass`/`shadow-elevated` + `var(--brand-*)` CSS 토큰
   - 다크톤 하드코딩(`#0f0f11`) 제거 → light/dark 테마 자동 대응 (`glass` 유틸 사용)
   - CSS keyframes → `motion/react`의 `motion.div` + `AnimatePresence`
   - 이모지 아이콘(✕) → `lucide-react`의 `X`/`ArrowRight`/`Gift`
   - `sessionStorage` 직접 접근 → `useDismissible("sohobi_survey_closed", { storage: "session" })` (PR #278에서 도입한 훅)
   - 노출/CTA 클릭/닫기에 `trackEvent("survey_banner", { action: "view"|"click"|"dismiss" })` 추가
   - `z-index`를 `9999` → `z-40`으로 낮춤
   - `SURVEY_URL` 상수에 **응답자용** URL 직접 하드코딩:
     `https://forms.office.com/pages/responsepage.aspx?id=OkauYhKf306FRE9so4NFJBKV4WxfV5tMpfVaLEYVJOJUMUowVTY3SDY0QTBaRUdEMVYwNUIySlY3OC4u&route=shorturl`
2. 레포 루트 `SurveyBanner.jsx` 삭제
3. `frontend/src/pages/Landing.jsx`, `frontend/src/pages/UserChat.jsx`, `frontend/src/components/map/ChatPanel.jsx` 최외곽에 `<SurveyBanner />` 삽입
4. ChatPanel 입력 영역과의 겹침 완화: 배너 `bottom` 오프셋을 `96px`로 조정 (필요 시 CSS 변수화)

### 검증 절차

- `cd frontend && npm run dev`
- `/`, `/user`, `/map` 각 경로에서 배너 노출 — 라이트/다크 테마 토글 시 대비 확인
- ✕ 클릭 → 새로고침 비표시, 탭 재열기 시 재노출 (session scope)
- CTA 클릭 → 새 탭에서 설문 폼 정상 로드 + `trackEvent` 호출 (backend logs 또는 devtools)
- `npm run build` 통과
- `cd frontend && npx prettier --write src/ && npx eslint --fix src/`

### 참고 문서

- 전체 플랜: [`/Users/eric.j.park/.claude/plans/immutable-puzzling-mango.md`](file:///Users/eric.j.park/.claude/plans/immutable-puzzling-mango.md)
- 기존 dismiss 훅 사용 예시: `frontend/src/pages/UserChat.jsx:117`, `frontend/src/components/checklist/StartupChecklist.jsx:18`

## 작업 디렉토리 상태

- 현재 브랜치: `main` (PR #278 pull 완료, merged branch 로컬 삭제 완료)
- 루트의 `SurveyBanner.jsx`는 여전히 untracked — PR #2에서 이동/삭제할 대상
- 기타 untracked: 이 세션과 무관한 타 세션의 session-report 2개 (`rubric-overhaul`, `sec1-leak-rootcause`)

---
<!-- CLAUDE_HANDOFF_START
branch: main (PR #2 시작 시 feat/park-survey-banner 신규 생성)
pr: 278 merged; next PR 미생성
prev: none

[unresolved]
- MED frontend/src/pages/UserChat.jsx:17 motion import 미사용 lint 에러(main 선행 이슈, 이 작업 무관)
- LOW ChatPanel 열린 상태에서 SurveyBanner가 입력 영역과 시각적으로 겹칠 수 있음 — bottom 오프셋 96px로 회피 예정

[decisions]
- 응답자용 MS Forms URL을 환경변수 분리 없이 SurveyBanner.jsx 상수에 직접 하드코딩 (사용자 결정)
- ChatPanel 포함 3곳 모두 노출 (LoginNudge 유사 UX와 일관)
- z-index는 9999 → z-40으로 낮춰 체크리스트 드로어 등 모달 아래 위치
- useDismissible 훅의 storage 옵션으로 session/local 선택 — SurveyBanner는 session scope

[next]
1. feat/park-survey-banner 브랜치를 origin/main 기반으로 생성
2. 루트 SurveyBanner.jsx → frontend/src/components/SurveyBanner.jsx 이동하면서 디자인시스템 준수 리팩터(Tailwind+motion/react+lucide+useDismissible+trackEvent, z-40)
3. SURVEY_URL을 응답자용 URL로 하드코딩
4. Landing/UserChat/ChatPanel 3곳 최외곽에 import+렌더 추가
5. 빌드·prettier·eslint 통과 확인 후 PR 생성, TC 수행

[traps]
- 루트 SurveyBanner.jsx의 CURRENT=129/TARGET=100은 임의 값 — 실제 수치 반영 여부 확인 필요
- SurveyBanner가 `position: fixed` 하드코딩이라 ChatPanel 입력창과 겹침. bottom 오프셋 조정 없이 그대로 쓰면 UX 저하
- `@import url(Pretendard)` 잔존 시 CSP·CLS 문제 가능성 — 반드시 제거
CLAUDE_HANDOFF_END -->
