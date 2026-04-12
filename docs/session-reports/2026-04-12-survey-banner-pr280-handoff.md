# SurveyBanner 전역 통합 PR #280 인수인계

- **날짜**: 2026-04-12
- **브랜치**: `feat/park-survey-banner` (origin/main 기반, rebase 완료)
- **PR**: #280 — "feat: SurveyBanner 전역 통합 — Landing·UserChat 노출 및 디자인시스템 리팩터"
- **머지 상태**: TC1~4/7 PASS, 머지 가능. TC5/6은 대화형 검증 이월.

## 요약

루트의 임시 `SurveyBanner.jsx`(인라인 `<style>` + Pretendard `@import` + 하드코딩 색상 + `sessionStorage` 직접 조작)를 디자인시스템 준수 컴포넌트로 전면 리팩터하여 `frontend/src/components/`로 이동하고, Landing·UserChat 2곳에 전역 노출했다. ChatPanel 통합은 오버랩 리스크로 세션 B로 분리(기획 문서 [docs/plans/2026-04-12-survey-banner-pr2.md](../plans/2026-04-12-survey-banner-pr2.md)).

재사용 자산: `useDismissible`(#278), `trackEvent`, `glass` / `shadow-elevated` / `var(--brand-*)` 토큰, `motion/react`, `lucide-react` 아이콘(X·ArrowRight·Gift).

## 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/SurveyBanner.jsx` | 신규 — Tailwind + 토큰, `bottomOffset` prop, view/click/dismiss 이벤트 3종 |
| `frontend/src/pages/Landing.jsx` | footer 뒤에 `<SurveyBanner />` 삽입 |
| `frontend/src/pages/UserChat.jsx` | footer 뒤에 `<SurveyBanner />` 삽입 |
| `SurveyBanner.jsx` (루트) | 삭제 |
| `docs/plans/2026-04-12-survey-banner-pr2.md` | 플랜 문서 |

## TC 결과

- ✅ TC1 빌드 성공 (`npm run build`)
- ✅ TC2 Landing `/` 배너 노출 확인 (playwright complementary role)
- ✅ TC3 UserChat `/user` 배너 노출 확인
- ✅ TC4 ✕ 클릭 후 동일 세션 재방문 시 미노출 (sessionStorage 영속성)
- ⏭ TC5 CTA 클릭 → `window.open` + `survey_banner_click` 네트워크 전송 (미실행)
- ⏭ TC6 UserChat 입력영역과 배너 오버랩 시각 검증 (미실행)
- ✅ TC7 `localhost` 하드코딩 없음

## 다음 세션 인수 요약

1. PR #280의 TC5/6을 playwright로 마저 돌리고 PR 코멘트로 결과 보고 → `--admin` 머지
2. 머지 후 main에서 TC1~4 재실행 → PR 코멘트 남김
3. 세션 B 착수: ChatPanel 내부에 `<SurveyBanner bottomOffset="bottom-[N]" />` 삽입 + 입력영역과 겹칠 경우 `--survey-banner-bottom` CSS 변수 도입
4. SURVEY_URL 상수는 현재 소스 하드코딩 — 차후 `VITE_SURVEY_URL` env로 뺄지 팀 합의 필요

## 주의사항

- `CURRENT=79` 는 2026-04-12 시점 수동 반영값. 응답자 수 변동 시 상수 갱신 필요 (자동화 없음)
- `motion` import가 eslint `no-unused-vars`에 걸리는 것은 프로젝트 전반 기존 이슈 — 프로젝트 eslint가 JSX member access를 인식하지 못함. pre-commit은 prettier만 돌아 차단되지 않음. 본 PR에서 해결 대상 아님
- `color-mix(in srgb, ...)` 사용 — 일부 구형 브라우저 미지원 가능성. 타겟이 최신 크롬/사파리면 OK

---
<!-- CLAUDE_HANDOFF_START
branch: feat/park-survey-banner
pr: 280
prev: none

[unresolved]
- MED TC5/6 미실행 — CTA 네트워크 전송 및 ChatPanel 오버랩 시각 검증 남음. playwright로 /user 접속 → 챗토글 열기 → 배너와 입력영역 겹침 여부 확인.
- LOW SURVEY_URL 하드코딩 — env 분리 여부 팀 합의 필요.
- LOW CURRENT 상수 수동 갱신 — 백엔드 응답자 수 API로 치환 검토 가능.

[decisions]
- useDismissible(key, { storage: "session" }) 사용 — 닫기 상태는 탭 세션 한정. 재방문(새 탭/재오픈)마다 노출.
- z-index: z-40 — 드로어/모달(z-50~)보다 낮게. 기존 체크리스트 드로어와 겹치지 않도록 의도적으로 하위 배치.
- 진행 배지/CTA 색상은 `done` 분기로 teal/orange 스위치. CURRENT>=TARGET 시 축하 톤 자동 전환.
- bottomOffset prop 노출 — 세션 B에서 ChatPanel 통합 시 입력영역 높이에 맞춰 override할 예정.

[next]
1. PR #280 TC5/6 playwright 검증 → PR body 체크박스 업데이트 → `gh pr merge --admin --squash`
2. 머지 후 main TC 재실행 → PR 코멘트
3. 세션 B: ChatPanel 내부 배너 삽입 + 오버랩 오프셋 튜닝 (별도 브랜치 `feat/park-survey-banner-chatpanel` 권장)

[traps]
- `/chat` 경로는 존재하지 않음 — UserChat 라우트는 `/user` (App.jsx:36)
- 프로젝트 eslint는 motion JSX member access를 unused로 잘못 감지. 무시 가능.
- playwright snapshot 저장 경로는 프로젝트 루트 하위여야 함 (`/tmp/` 금지). `.playwright-mcp/` 사용.
CLAUDE_HANDOFF_END -->
