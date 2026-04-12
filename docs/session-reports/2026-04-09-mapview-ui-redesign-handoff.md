# MapView UI 전면 개편 — 세션 인수인계

**날짜**: 2026-04-09
**브랜치**: `PARK-stats-period-extend` (현재), 작업 시 `PARK-mapview-ui-redesign` 신규 생성 권장
**상태**: 플랜 완성, 구현 미착수

---

## 목표

MapView (지도 페이지) 및 하위 컴포넌트의 UI/색상/디자인을 전면 개편하여 Landing.jsx, Features.jsx와 동일한 톤&매너(glass morphism, CSS 변수, gradient, elevated shadow, glow)로 통일한다.

## 플랜 파일

**`.claude/plans/frolicking-shimmying-glacier.md`** — 7 Phase 상세 플랜 포함

## 탐색 완료 내용

### 현재 문제점
- **MapView.css** (737줄): 50+ 하드코딩 색상(`#fff`, `#2563eb`, `#059669` 등), 기본 box-shadow, glass morphism 미적용
- **ChatPanel.css** (398줄): 이미 하단(287-361줄)에 디자인 시스템 오버라이드가 존재하나 상단 원본(1-239줄)과 **중복/충돌** 상태. 다크모드 블록(240-285줄)도 CSS 변수 사용 시 불필요
- 다크모드: `.dark .mv-*` 오버라이드가 ~30줄 중복 — CSS 변수 치환 시 대부분 삭제 가능
- 네비게이션: `<a href>` 사용 (SPA인데 full reload) → `<Link>` + `<Button>` 필요

### 사용 가능한 디자인 시스템 (theme.css + animations.css)
- 브랜드 색상: `--brand-blue`, `--brand-teal`, `--brand-orange`
- Glass: `.glass` (blur-20px), `var(--glass-bg)`, `var(--glass-border)`
- Shadow: `.shadow-elevated`, `.shadow-elevated-lg`
- Glow: `--glow-blue`, `--glow-teal`, `.hover-glow-blue`
- 애니메이션: `animate-blob`, `animate-float`, `animate-shimmer`

### 구조 참고
- ChatPanel은 MapView.jsx 안에서 조건부 렌더링됨 (지도 위 오버레이)
- DongPanel 헤더에 인라인 `style={{ background: '#0891B2' }}` 하드코딩 존재 (DongPanel.jsx 확인 필요)
- StorePopup, WmsPopup에도 인라인 색상 있을 수 있음 (확인 필요)

## 수정 대상 파일

| 파일 | 변경 | Phase |
|------|------|-------|
| `frontend/src/components/map/MapView.css` | CSS 변수 치환 + glass + shadow + glow + 다크모드 중복 삭제 | 1-5 |
| `frontend/src/components/map/MapView.jsx` | 네비 `<a>` → `<Link>`+`<Button>`, 레이어 버튼 아이콘 교체 | 4 |
| `frontend/src/components/map/ChatPanel.css` | 원본 하드코딩 → CSS 변수, 하단 오버라이드+다크 블록 삭제 | 6 |
| `frontend/src/components/map/ChatPanel.jsx` | 토글 버튼 Tailwind 하드코딩 정리 (선택) | 6 |
| `frontend/src/components/map/panel/DongPanel.jsx` | 인라인 배경색 제거 → CSS gradient | 5 |
| `frontend/src/components/map/popup/WmsPopup.jsx` | 인라인 색상 확인 후 수정 | 확인 필요 |
| `frontend/src/components/map/popup/StorePopup.jsx` | 인라인 색상 확인 후 수정 | 확인 필요 |

## 실행 순서

1. `origin/main` 기반 `PARK-mapview-ui-redesign` 브랜치 생성
2. **Phase 1+2+3** — MapView.css만 수정 (CSS 변수 + glass + shadow)
3. **Phase 4** — MapView.jsx 네비 버튼 JSX
4. **Phase 5** — DongPanel 헤더
5. **Phase 6** — ChatPanel.css 정리
6. 라이트/다크 모드 + 모바일 검증
7. PR 생성

## 주의사항

- MapView는 전체 화면 지도 도구 — AnimatedBackground 같은 페이지 레벨 장식은 부적합
- OpenLayers 기본 컨트롤(.ol-zoom 등) 스타일은 다크모드 외 건드리지 않음
- ChatPanel.css 하단 오버라이드(287-361줄)는 이미 올바른 값이므로 상단 원본에 통합 후 삭제
