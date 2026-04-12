# CategoryPanel·Layerpanel Glass Morphism 리디자인 — 세션 인수인계

**날짜**: 2026-04-09
**브랜치**: `PARK-mapview-ui-redesign`
**PR**: #255 (OPEN, 머지 대기)
**상태**: CategoryPanel + Layerpanel 리디자인 완료, Phase D(Framer Motion 애니메이션) 미착수

---

## 완료된 작업

### 커밋: `style: CategoryPanel·Layerpanel glass morphism 리디자인` (`7a50f51`)

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/components/map/panel/CategoryPanel.css` | **신규 생성** — `const S = {}` 인라인 165줄 → `cp-` prefix CSS 클래스 추출. glass-bg + backdrop-filter(16px), gradient 헤더(brand-blue→brand-teal), gradient Show all 버튼, 검색 focus glow, hover-lift, 하드코딩(#2563EB, #ccc, #ddd) → CSS 변수 |
| `frontend/src/components/map/panel/CategoryPanel.jsx` | `import "./CategoryPanel.css"` 추가, `const S = {}` 전체 삭제, `style={S.xxx}` → `className="cp-xxx"` 전환. 동적 cat.color 인라인만 유지 |
| `frontend/src/components/map/panel/Layerpanel.css` | 하드코딩 10색(#fff, #ddd, #f9f9f9, #111, #aaa 등) → CSS 변수, `.dark .lp-*` 오버라이드 6개 삭제, glass morphism + hover-lift 적용, 타이틀 gradient-text |
| `frontend/src/components/map/panel/Layerpanel.jsx` | 토글 ON 상태 subtle glow 추가 (`boxShadow: "0 0 12px ${color}40"`) |

### PR #255 전체 커밋 (origin/main 기준)

1. `30a0ba9` — MapView/ChatPanel/DongPanel 디자인 시스템 통일
2. `c54262d` — 인수인계 문서
3. `c6859f5` — Azure SWA 워크플로우 설정
4. `7a50f51` — CategoryPanel·Layerpanel glass morphism 리디자인 (본 세션)

### 검증 결과

- `npm run build` ✅ 성공
- Playwright 라이트모드 CategoryPanel ✅
- Playwright 다크모드 CategoryPanel ✅
- Playwright 라이트모드 Layerpanel ✅
- Playwright 다크모드 Layerpanel ✅
- localhost DOMAIN 회귀 grep 확인 ✅ (환경변수 fallback, 문제 없음)

---

## 미착수 작업

### Phase D: 접기/펼치기 Framer Motion 애니메이션 (보류)

**현재**: CSS `transition: width 0.2s ease`로 동작 중
**계획**: Framer Motion `AnimatePresence` + `motion.div` + `staggerChildren`

구체적 내용:
1. CategoryPanel 사이드바 collapse: `AnimatePresence` + `motion.div` 래핑 (`initial={{ opacity: 0, width: 0 }}` → `animate={{ opacity: 1, width: "auto" }}`)
2. 카테고리 리스트 순차 등장: `staggerChildren` (`delay: index * 0.03`)

**판단 포인트**: CSS transition으로 충분한지, Framer Motion 추가가 UX 개선에 유의미한지 별도 세션에서 결정

### 별도 PR 보류 항목 (이전 세션에서 분리)

- **WmsPopup / StorePopup 인라인 색상** — 별도 PR로 분리 예정
- **StorePopup CAT_STYLE 색상** — 브랜드 3색 기반 리서치 중 (`#0891b2`, `#14b8a6`, `#f97316`)

---

## 다음 세션 인수 요약

1. PR #255 머지 여부 결정 (MapView 전체 디자인 시스템 통일 포함)
2. Phase D (Framer Motion 애니메이션) 진행 여부 판단 — 별도 PR 또는 #255에 추가
3. WmsPopup / StorePopup 인라인 색상 작업은 별도 브랜치에서 진행
4. 확장 브랜드 색상 팔레트는 `theme.css`에 이미 등록 완료 (`--brand-deep-cyan` 외 7개)

---

## 참고: 디자인 시스템 적용 현황

| 컴포넌트 | Glass | CSS 변수 | Gradient | Glow | .dark 자동 |
|----------|-------|---------|----------|------|-----------|
| MapView.css | ✅ | ✅ | — | ✅ | ✅ |
| ChatPanel.css | ✅ | ✅ | — | — | ✅ |
| DongPanel.jsx | ✅ | ✅ | ✅ | — | ✅ |
| CategoryPanel | ✅ | ✅ | ✅ | ✅ | ✅ |
| Layerpanel | ✅ | ✅ | ✅ | ✅ | ✅ |
| WmsPopup | ⬜ | ⬜ | — | — | ⬜ |
| StorePopup | ⬜ | ⬜ | — | — | ⬜ |
