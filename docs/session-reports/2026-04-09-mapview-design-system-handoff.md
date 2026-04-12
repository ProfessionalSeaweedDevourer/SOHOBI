# MapView 디자인 시스템 통일 + 좌측 컨트롤바 리디자인 — 세션 인수인계

**날짜**: 2026-04-09
**브랜치**: `PARK-mapview-ui-redesign` (커밋 완료, PR 미생성)
**상태**: MapView/ChatPanel/DongPanel 디자인 시스템 통일 완료, 좌측 컨트롤바+레이어 패널 리디자인 미착수

---

## 완료된 작업

### 커밋: `style: MapView 디자인 시스템 통일`

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/styles/theme.css` | 확장 브랜드 색상 7개 등록 (`--brand-deep-cyan`, `--brand-bright-cyan`, `--brand-mint`, `--brand-soft-orange`, `--brand-burnt-orange`, `--brand-slate-light`, `--brand-slate-dark`) |
| `frontend/src/components/map/MapView.css` | 하드코딩 66개 → CSS 변수, glass morphism + elevated shadow 적용, 다크모드 134줄 → 자동 대응으로 삭제 |
| `frontend/src/components/map/MapView.jsx` | `<a href>` → `<Link>`, 🗂️ → `<Layers />` 아이콘, `aria-label` 추가 |
| `frontend/src/components/map/ChatPanel.css` | 원본+오버라이드+다크모드 3중 구조 → 단일 CSS 변수 기반으로 통합 (397줄 → ~270줄) |
| `frontend/src/components/map/ChatPanel.jsx` | 토글 버튼 Tailwind 하드코딩 gradient → `.mv-chat-toggle` CSS 클래스 |
| `frontend/src/components/map/panel/DongPanel.jsx` | 인라인 `style={{ background: panelColor }}` → CSS gradient 클래스 (`--re`, `--store`, `--sales`) |

### 확인 사항
- `npm run build` 성공
- Playwright 라이트/다크 모드 스크린샷 확인 완료
- `panelColor` 변수는 SalesSummary 하위 컴포넌트에서 사용하므로 유지됨

---

## 미착수 작업: 좌측 컨트롤바 + 레이어 패널 전면 리디자인

### 현재 문제점

#### CategoryPanel (`frontend/src/components/map/panel/CategoryPanel.jsx`)
- **전체 인라인 스타일** — CSS 파일 없이 `const S = {}` 객체로 ~100줄 스타일 관리
- Landing 페이지의 glass morphism, gradient, glow 효과 전무
- 카테고리 행: 단순 배경색 토글, 시각적 임팩트 부족
- 헤더: 이모지(`🏪`) 텍스트만, 그래디언트 없음
- 검색 박스: 기본 input 스타일, glass 효과 없음
- ON/OFF 토글: 단색 버튼, glow/transition 미적용
- 통계 뱃지: `#2563EB` 하드코딩 (파란색 고정)
- 모바일 접기/펼치기: 기능은 있으나 애니메이션 미흡

#### Layerpanel (`frontend/src/components/map/panel/Layerpanel.jsx` + `Layerpanel.css`)
- CSS 파일 있으나 하드코딩 색상 투성이 (`#fff`, `#ddd`, `#f9f9f9`, `#111`, `#aaa`, `#e0e0e0` 등)
- 다크모드: `.dark .lp-*` 중복 오버라이드 패턴 (MapView.css 이전 상태와 동일)
- 레이어 행: 평탄한 `#f9f9f9` 배경, glass 효과 없음
- 토글 버튼: 기본 스타일, glow 미적용
- 전체적으로 Landing/Features 톤&매너와 불일치

### 리디자인 방향 (Landing 레퍼런스)

Landing 페이지에서 추출한 핵심 패턴:

| Landing 패턴 | 좌측 컨트롤바 적용 |
|-------------|------------------|
| `.glass` (blur-20px, 반투명 배경) | 사이드바 전체 컨테이너 |
| `.glass-card` (blur-24px + shadow) | 카테고리 행, 레이어 행 |
| `gradient-text` (cyan→teal) | 헤더 타이틀 ("상권 분석") |
| `hover-glow-blue/teal` | ON 토글 버튼 hover |
| `shadow-elevated` | 사이드바 컨테이너 |
| `hover-lift` (translateY -4px) | 카테고리 행 hover |
| Framer Motion `whileHover`, `whileTap` | 버튼 인터랙션 |
| `linear-gradient(135deg, brand-blue, brand-teal)` | 헤더 배경, "Show all" 버튼 |
| `animate-float` | (선택) 로고/아이콘 미세 움직임 |

### 구체적 리디자인 플랜

#### Phase A: CategoryPanel 인라인 → CSS 파일 추출
1. `CategoryPanel.css` 신규 생성
2. `const S = {}` 인라인 스타일을 CSS 클래스로 전환
3. 하드코딩 색상 CSS 변수 치환
4. 다크모드: CSS 변수 자동 대응

#### Phase B: CategoryPanel glass morphism 적용
1. 사이드바 컨테이너: `glass-bg + backdrop-filter: blur(20px)` + `shadow-elevated`
2. 헤더: gradient 배경 (`brand-blue → brand-teal`) + 흰색 텍스트
3. 검색 박스: `glass-border` 테두리, focus 시 `glow-blue`
4. 카테고리 행: `glass-card` 스타일, hover 시 `hover-lift` + `glow-teal`
5. ON 토글: `brand-teal` 배경 + `glow-teal`, OFF: `muted` 배경
6. 통계 뱃지: `rgba(8,145,178,0.1)` 배경 + `brand-blue` 텍스트
7. "Show all" 버튼: gradient (`brand-blue → brand-teal`), glow hover

#### Phase C: Layerpanel CSS 변수 치환 + glass
1. `Layerpanel.css` 하드코딩 색상 → CSS 변수 (MapView.css Phase 1과 동일 패턴)
2. `.lp-panel`: glass morphism 적용
3. `.lp-row`: glass-card 스타일 + hover-lift
4. `.lp-toggle`: ON 시 brand-blue + glow, OFF 시 muted
5. `.lp-notice`: glass-bg 배경
6. 다크모드 `.dark .lp-*` 중복 삭제

#### Phase D: 접기/펼치기 애니메이션 개선
1. Framer Motion `AnimatePresence` + `motion.div` 래핑
2. 사이드바 width 전환: `animate={{ width }}` + `transition={{ type: "spring" }}`
3. 카테고리 리스트: `staggerChildren` 으로 순차 등장

### 수정 대상 파일

| 파일 | 변경 | Phase |
|------|------|-------|
| `frontend/src/components/map/panel/CategoryPanel.css` | **신규 생성** — 인라인 스타일 추출 + glass | A, B |
| `frontend/src/components/map/panel/CategoryPanel.jsx` | `S` 객체 제거 → CSS 클래스 적용, Framer Motion 래핑 | A, B, D |
| `frontend/src/components/map/panel/Layerpanel.css` | 하드코딩 → CSS 변수, glass, 다크모드 삭제 | C |
| `frontend/src/components/map/panel/Layerpanel.jsx` | 필요시 클래스 추가 | C |

### 실행 순서

1. `PARK-mapview-ui-redesign` 브랜치에 이어서 작업 (또는 본 커밋 PR 후 새 브랜치)
2. Phase A → B (CategoryPanel) → Phase C (Layerpanel) → Phase D (애니메이션)
3. Playwright 라이트/다크 + 모바일 검증
4. PR 생성

---

## 보류 항목

- **WmsPopup / StorePopup 인라인 색상**: 별도 PR로 분리 (StorePopup 50개+ 인라인 색상, CAT_STYLE 10색)
- **StorePopup CAT_STYLE 색상**: 사용자가 브랜드 3색 기반 리서치 중 (`#0891b2`, `#14b8a6`, `#f97316`)

## 확장 브랜드 색상 팔레트

| 이름 | CSS 변수 | Hex |
|------|---------|-----|
| Deep Cyan | `--brand-deep-cyan` | `#164E63` |
| Cyan (기존) | `--brand-blue` | `#0891B2` |
| Bright Cyan | `--brand-bright-cyan` | `#06B6D4` |
| Teal (기존) | `--brand-teal` | `#14B8A6` |
| Mint | `--brand-mint` | `#99F6E4` |
| Soft Orange | `--brand-soft-orange` | `#FDBA74` |
| Orange (기존) | `--brand-orange` | `#F97316` |
| Burnt Orange | `--brand-burnt-orange` | `#C2410C` |
| Slate Light | `--brand-slate-light` | `#F1F5F9` |
| Slate Dark | `--brand-slate-dark` | `#1E293B` |
