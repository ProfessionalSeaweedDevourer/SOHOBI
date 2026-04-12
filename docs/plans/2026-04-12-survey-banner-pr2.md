# SurveyBanner 전역 통합 — PR #2 (A/B 분할)

## Context

PR #278에서 `useDismissible` 훅 선행 추출은 완료. 이어지는 PR은 ① 루트의 임시 `SurveyBanner.jsx`를 디자인시스템 준수 컴포넌트로 전면 리팩터하여 `frontend/src/components/`로 이동하고 ② Landing·UserChat·ChatPanel 3곳에 전역 노출하는 것.

전체 작업을 한 세션에서 수행하면 (refactor + 3개 페이지 통합 + 빌드/lint/TC 3회 + ChatPanel 오버랩 해결) 턴이 과밀해질 위험이 있음. 특히 **ChatPanel 통합은 입력 영역과의 `position: fixed` 겹침 리스크**가 있어 CSS 오프셋 튜닝에 turn이 몰린다. 따라서 아래와 같이 분할한다.

- **세션 A (본 플랜)** — 리팩터 + Landing/UserChat 2곳 통합, PR 생성·TC·머지까지
- **세션 B (다음 인수인계)** — ChatPanel 통합 + 오프셋 검증 단독 PR

탐색 과정에서 확인된 **핵심 수정 포인트**:

- 루트 `SurveyBanner.jsx`의 `SURVEY_URL`은 `"https://forms.office.com/YOUR_FORM_ID"` placeholder → 실제 응답자용 URL로 교체 필요
- `CURRENT=129 / TARGET=100`은 임의값 — `CURRENT=79 / TARGET=100`으로 반영 (사용자 확인 완료)
- `UserChat.jsx:18`의 `motion` import는 **이미 사용 중** (이전 handoff의 "미사용 lint 에러" 메모는 stale → 무시)
- `trackEvent` 는 [frontend/src/utils/trackEvent.js](../../frontend/src/utils/trackEvent.js) 에서 `trackEvent(name, payload)` 시그니처. Landing/UserChat에서 이미 사용 중이라 import 경로 재사용
- `useDismissible(key, { storage: "session" })` → `[visible, dismiss]` 튜플
- `glass`, `shadow-elevated`, `var(--brand-*)` 는 [frontend/src/styles/animations.css](../../frontend/src/styles/animations.css), [frontend/src/styles/theme.css](../../frontend/src/styles/theme.css) 에 정의되어 즉시 사용 가능

## 세션 A — 리팩터 + Landing/UserChat 통합

### 브랜치

```
feat/park-survey-banner
```

`origin/main` 기반 생성.

### 1. SurveyBanner 리팩터 이동

**대상**: 루트 `SurveyBanner.jsx` → [frontend/src/components/SurveyBanner.jsx](../../frontend/src/components/SurveyBanner.jsx) (신규)

**재사용 자산**:
- `useDismissible` — [frontend/src/hooks/useDismissible.js](../../frontend/src/hooks/useDismissible.js)
- `trackEvent` — [frontend/src/utils/trackEvent.js](../../frontend/src/utils/trackEvent.js)
- `glass` / `shadow-elevated` 유틸, `var(--brand-blue|teal|orange)` CSS 토큰
- `motion` + `AnimatePresence` — `motion/react`
- `X`, `ArrowRight`, `Gift` — `lucide-react`

**주요 변경**:

| 항목 | Before (루트) | After (리팩터) |
| --- | --- | --- |
| 스타일 | 인라인 `<style>` 블록 + `@import Pretendard` | Tailwind + `glass` + `shadow-elevated` |
| 테마 | `#0f0f11` 하드코딩 | `glass` + `var(--brand-*)` → 라이트/다크 자동 |
| 애니메이션 | CSS keyframes | `motion.div` + `AnimatePresence` |
| 아이콘 | 이모지 ✕ 🎁 | `lucide-react` 아이콘 |
| Dismiss | `sessionStorage` 직접 접근 | `useDismissible("sohobi_survey_closed", { storage: "session" })` |
| 트래킹 | 없음 | `trackEvent("survey_banner", { action: "view"\|"click"\|"dismiss" })` (마운트 시 view, CTA click, X dismiss) |
| z-index | `9999` | `z-40` (체크리스트 드로어 하위) |
| URL | `YOUR_FORM_ID` placeholder | 응답자용 URL 하드코딩: `https://forms.office.com/pages/responsepage.aspx?id=OkauYhKf306FRE9so4NFJBKV4WxfV5tMpfVaLEYVJOJUMUowVTY3SDY0QTBaRUdEMVYwNUIySlY3OC4u&route=shorturl` |
| 노출/목표 수치 | `CURRENT=129 / TARGET=100` | `CURRENT=79 / TARGET=100` |

**컴포넌트 골격**:

```jsx
// frontend/src/components/SurveyBanner.jsx
import { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, ArrowRight, Gift } from "lucide-react";
import { useDismissible } from "../hooks/useDismissible";
import { trackEvent } from "../utils/trackEvent";

const SURVEY_URL = "https://forms.office.com/pages/responsepage.aspx?id=...&route=shorturl";

export default function SurveyBanner() {
  const [visible, dismiss] = useDismissible("sohobi_survey_closed", { storage: "session" });

  useEffect(() => { if (visible) trackEvent("survey_banner", { action: "view" }); }, [visible]);

  const handleClick = () => trackEvent("survey_banner", { action: "click" });
  const handleDismiss = () => { trackEvent("survey_banner", { action: "dismiss" }); dismiss(); };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
          className="fixed bottom-6 right-6 z-40 glass shadow-elevated rounded-2xl p-4 max-w-sm"
        >
          {/* Gift 아이콘 + 제목 + 수치(79/100) + CTA(ArrowRight) + X 버튼 */}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

### 2. 루트 파일 삭제

루트 `SurveyBanner.jsx` 는 `git rm` 이 아니라 **원래 untracked**이므로 그냥 `rm SurveyBanner.jsx`.

### 3. Landing 통합

[frontend/src/pages/Landing.jsx](../../frontend/src/pages/Landing.jsx) 최외곽 `<div className="min-h-screen relative">` 하위, `<AnimatedBackground />` 다음에 `<SurveyBanner />` 삽입.

### 4. UserChat 통합

[frontend/src/pages/UserChat.jsx](../../frontend/src/pages/UserChat.jsx) 최외곽 `<div className="min-h-screen flex flex-col bg-background">` 하위 끝단에 `<SurveyBanner />` 삽입 (footer 입력 영역과 `position: fixed` 특성상 시각 겹침 없음 — right-6 고정).

### 5. 빌드·lint

```bash
cd frontend && npm run build
npx prettier --write src/components/SurveyBanner.jsx src/pages/Landing.jsx src/pages/UserChat.jsx
npx eslint --fix src/components/SurveyBanner.jsx src/pages/Landing.jsx src/pages/UserChat.jsx
```

### 6. PR 생성

Test Plan:

- [ ] TC1: `npm run build` 통과
- [ ] TC2: `/` 경로 라이트/다크 토글 시 배너 대비 정상
- [ ] TC3: `/user` 경로 배너 노출, X 클릭 후 새로고침 시 비표시
- [ ] TC4: CTA 클릭 → 새 탭 MS Forms 로드 + `trackEvent` 로그 확인 (`/api/v1/logs?type=events`)
- [ ] TC5: 탭 완전 재시작 시 재노출 (session scope)

### 7. 세션 B 인수인계

PR A 머지 후 `docs/session-reports/YYYY-MM-DD-survey-banner-chatpanel-handoff.md` 생성. 내용:

- 다음 브랜치: `feat/park-survey-banner-chatpanel`
- 작업: [frontend/src/components/map/ChatPanel.jsx](../../frontend/src/components/map/ChatPanel.jsx) 최외곽에 `<SurveyBanner />` 추가 + 입력창(`.mv-chat-input-area`, [frontend/src/components/map/ChatPanel.css](../../frontend/src/components/map/ChatPanel.css))과의 `bottom` 오프셋 튜닝
- 접근: `SurveyBanner` 에 `bottomOffset` prop 선택지 도입 또는 ChatPanel 렌더 시 `style={{ bottom: '96px' }}` wrapper로 override. 디자인시스템 일관성 고려하여 **CSS 변수 `--survey-banner-bottom`** 도입 후 ChatPanel 전용 클래스에서 재정의 권장
- TC: `/map` 에서 ChatPanel 열기 + 닫기 상태 모두에서 배너와 입력창 겹침 없음, 새 탭 세션 리셋 동작 확인

## 검증

```bash
source integrated_PARK/.env
curl -s "$BACKEND_HOST/api/v1/logs?type=events&limit=20" | python3 -m json.tool
```
→ `survey_banner` 이벤트(view/click/dismiss) 기록 확인.

Playwright MCP 로 `/`, `/user` 라우트 snapshot 촬영 후 배너 노출 검증.
