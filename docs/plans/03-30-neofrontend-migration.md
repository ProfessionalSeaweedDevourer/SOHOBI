# NeoFrontend 마이그레이션 계획

## Context

현재 `frontend/`는 실제 API 연동(SSE 스트리밍, 지도, 로그)이 모두 동작하지만 디자인이 단순하다.
`NeoFrontend_Mar30/`는 glassmorphism·motion 애니메이션·Radix UI 기반의 고품질 디자인 시스템을 가지지만 API 연동이 없는 mock 상태이다.
**목표:** NeoFrontend의 디자인·인터랙션 레이어를 기존 frontend의 기능 로직 위에 이식한다.

---

## 핵심 제약

- 기존 모든 라우트(`/`, `/user`, `/map`, `/dev/login`, `/dev`, `/dev/logs`) 및 API 연동 로직 100% 보존
- OpenLayers 지도 훅·레이어 로직(`hooks/map/*.js`) 절대 수정 금지
- `.env` 커밋 금지, `commercial.db` 재업로드 불필요

---

## 기술 전환 포인트

| 항목 | 현재 | 이후 |
|------|------|------|
| Tailwind | v3 (JS config) | v4 (`@tailwindcss/vite` 플러그인) |
| 애니메이션 | CSS keyframe, Tailwind animate | `motion` v12 (`motion/react`) |
| 컴포넌트 기반 | 순수 Tailwind + 커스텀 CSS | Radix UI 프리미티브 + CVA |
| 다크모드 | 미지원 | CSS variables + localStorage toggle |
| 폰트 | Pretendard (index.css) | Pretendard CDN (fonts.css) |
| 토스트 | 미지원 | `sonner` |

---

## Phase 1 — 의존성 & 디자인 시스템 부트스트랩 (파괴적 변경 없음)

### 1-1. Tailwind v3 → v4 업그레이드
- `package.json`: `tailwindcss` → `^4.1.12`, `@tailwindcss/vite: ^4.1.12` 추가, `autoprefixer` 제거
- `vite.config.js`: `import tailwindcss from '@tailwindcss/vite'` → `plugins` 배열에 추가
- `tailwind.config.js`, `postcss.config.js` 삭제
- `src/index.css` Tailwind 지시자 교체:
  ```css
  @import 'tailwindcss' source(none);
  @source '../**/*.{js,ts,jsx,tsx}';
  ```
  > v3 표준 유틸리티 클래스는 v4에서 100% 호환됨

### 1-2. 신규 패키지 설치
```
motion, lucide-react, sonner, clsx, tailwind-merge,
class-variance-authority, tw-animate-css,
@radix-ui/react-slot, @radix-ui/react-separator,
@radix-ui/react-tooltip, @radix-ui/react-tabs,
@radix-ui/react-collapsible, @radix-ui/react-label,
@radix-ui/react-switch, @radix-ui/react-select
```

### 1-3. 스타일 파일 복사 → `frontend/src/styles/`
- `NeoFrontend_Mar30/src/styles/fonts.css` → 그대로 복사
- `NeoFrontend_Mar30/src/styles/theme.css` → 그대로 복사 (CSS variables, glow, glass)
- `NeoFrontend_Mar30/src/styles/animations.css` → 그대로 복사 (blob, shimmer, slideUp 등)

`src/index.css` import 추가:
```css
@import 'tw-animate-css';
@import './styles/fonts.css';
@import './styles/theme.css';
@import './styles/animations.css';
```

### 1-4. `cn` 유틸리티 생성
- **신규** `frontend/src/lib/utils.js`
  ```js
  import { clsx } from 'clsx';
  import { twMerge } from 'tailwind-merge';
  export const cn = (...inputs) => twMerge(clsx(inputs));
  ```

### 1-5. Radix UI 프리미티브 복사
- `NeoFrontend_Mar30/src/app/components/ui/` 전체 → `frontend/src/components/ui/`
- `.tsx` → `.jsx` 로 확장자 변경, TypeScript 타입 어노테이션 제거

**검증:** `npm run dev` 후 모든 라우트 정상 동작, 기존 UI 동일하게 표시

---

## Phase 2 — 디자인 토큰 적용 (색상 클래스 교체)

기존 컴포넌트의 hardcoded Tailwind 색상 → CSS variable 기반으로 교체.

| 기존 클래스 | 교체 |
|------------|------|
| `bg-white` / `bg-slate-50` | `bg-card` / `bg-background` |
| `border-slate-200` | `border-[var(--border)]` |
| `text-slate-800` | `text-foreground` |
| `text-slate-400` | `text-muted-foreground` |
| `bg-white border border-slate-200 rounded-2xl` | `glass rounded-2xl border border-white/20 shadow-elevated` |
| Grade A: `bg-green-100 text-green-700` | `bg-[var(--grade-a)]/20 text-[var(--grade-a)]` |
| Grade B: `bg-amber-100 text-amber-700` | `bg-[var(--grade-b)]/20 text-[var(--grade-b)]` |
| Grade C: `bg-red-100 text-red-600` | `bg-[var(--grade-c)]/20 text-[var(--grade-c)]` |
| 사용자 말풍선 `bg-slate-800` | `bg-gradient-to-br from-[var(--brand-blue)] to-[var(--brand-teal)]` |

**수정 대상 파일:**
- `src/pages/Home.jsx`, `UserChat.jsx`, `DevChat.jsx`, `DevLogin.jsx`, `LogViewer.jsx`
- `src/components/ResponseCard.jsx`, `ChatInput.jsx`

---

## Phase 3 — 컴포넌트 교체

### 신규 컴포넌트 (NeoFrontend에서 이식, JS로 변환)
- `src/components/GradeBadge.jsx` ← `NeoFrontend/GradeBadge.tsx`
  - `motion/react` 애니메이션 + glow shadow 포함
  - 사용처: `SignoffPanel.jsx`, `ResponseCard.jsx`
- `src/components/MessageBubble.jsx` ← `NeoFrontend/MessageBubble.tsx`
  - user: gradient bubble / assistant: glass bubble
  - `ResponseCard.jsx` 내부에서 어댑터 패턴으로 사용
- `src/components/LoadingSpinner.jsx` ← `NeoFrontend/LoadingSpinner.tsx`
  - `LoadingSpinner`, `LoadingDots`, `LoadingPulse` 세 가지 변형
  - `UserChat.jsx`, `DevChat.jsx`의 인라인 spinner 교체

### 기존 컴포넌트 리스킨 (로직 보존, 비주얼만 교체)
- `src/components/SignoffPanel.jsx`
  - 기존 API 데이터 매핑(rejectionHistory, agentMs, signoffMs) 유지
  - `motion.div` + `glass` + `GradeBadge` 적용
- `src/components/ProgressPanel.jsx`
  - staggered `motion.div` (delay: idx * 0.05)
  - `lucide-react`의 `CheckCircle2`, `XCircle` 아이콘으로 교체
  - `LoadingDots` 스피너 적용
- `src/components/ChatInput.jsx`
  - `forwardRef`, `useImperativeHandle`, 자동 높이 조절 로직 보존
  - `glass-card` + `motion.div whileHover/whileTap` 적용

---

## Phase 4 — 동적 인터랙션 추가

모두 NeoFrontend에서 이식, JS 변환. API 연동 없음.

### 신규 컴포넌트
| 파일 | 원본 | 추가 위치 |
|------|------|-----------|
| `AnimatedBackground.jsx` | `AnimatedBackground.tsx` | `Home.jsx`, `UserChat.jsx`, `DevLogin.jsx` 배경 |
| `CursorGlow.jsx` | `CursorGlow.tsx` | `App.jsx` 전역 렌더 (spring physics 마우스 추적) |
| `PageTransition.jsx` | `PageTransition.tsx` | `App.jsx`의 `<Routes>` 래핑 (`AnimatePresence`) |
| `ScrollReveal.jsx` | `ScrollReveal.tsx` | `Home.jsx` 카드 등장 연출 |
| `KeyboardShortcuts.jsx` | `KeyboardShortcuts.tsx` | `App.jsx` 전역 (경로 매핑: `/user`, `/map`, `/dev`, `/dev/logs`) |
| `ToastProvider.jsx` | `ToastProvider.tsx` 단순화 | `App.jsx` 전역 (`next-themes` 제거, classList 감지로 대체) |

### `App.jsx` 최종 구조
```jsx
// BrowserRouter 내부에 배치 (useNavigate 사용 가능)
function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* 기존 라우트 100% 유지 */}
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <CursorGlow />
      <ToastProvider />
      <KeyboardShortcuts />
      <AnimatedRoutes />
    </BrowserRouter>
  );
}
```

---

## Phase 5 — 지도 UI 업그레이드 (CSS만, 로직 불변)

**절대 수정 금지:** `hooks/map/*.js`, `MapView.jsx` OpenLayers 로직 부분

### CSS 파일 수정
- `MapView.css`: 컨트롤 바, 패널 → glass + CSS variable 색상
- `ChatPanel.css`:
  - 패널 배경 → `var(--glass-bg)` + `backdrop-filter: blur(24px)`
  - 헤더 → `linear-gradient(135deg, var(--brand-blue), var(--brand-teal))`
  - 사용자 말풍선 → gradient, 어시스턴트 말풍선 → glass

### 패널 컴포넌트 Tailwind 클래스 교체
- `panel/Layerpanel.jsx`, `panel/DongPanel.jsx`, `panel/CategoryPanel.jsx`
  - `bg-white` → `bg-[var(--card)]`, `border-slate-200` → `border-[var(--border)]`
  - `shadow-elevated` 추가
- `controls/MapControls.jsx`
  - 버튼 `glass hover-glow-teal transition-glow` 적용

---

## Phase 6 — 마무리 폴리시

- `ThemeToggle.jsx` ← `NeoFrontend/ThemeToggle.tsx`
  - localStorage + `document.documentElement.classList.toggle('dark')`
  - 모든 페이지 헤더 우측 상단에 추가
- `EnhancedTooltip.jsx` ← `NeoFrontend/EnhancedTooltip.tsx`
  - 지도 컨트롤 버튼, 루브릭 코드 배지, GradeBadge에 적용
- `Home.jsx` 카드 → AgentCard 스타일 `motion.div` 애니메이션 적용
  - 기존 onClick 로직(dev 인증 체크 포함) 100% 보존
- `UserChat.jsx` 빈 상태 → 추천 질문 `ScrollReveal` 연출
- `LogViewer.jsx` / `LogTable.jsx` → `ui/table.jsx`, `ui/card.jsx`, `GradeBadge` 적용
- `DevLogin.jsx` → `AnimatedBackground` + `motion.div` 등장 애니메이션

---

## 리스크 & 완화

| 리스크 | 수준 | 완화 방법 |
|--------|------|-----------|
| Tailwind v4 기존 유틸리티 클래스 호환성 | 낮음 | v4는 표준 유틸리티 100% 하위호환 |
| `motion/react` 패키지명 | 낮음 | `motion` npm 패키지 설치 시 `motion/react` import 가능 |
| `next-themes` 의존성 | 중간 | ToastProvider에서 제거, classList 감지로 대체 |
| React 19 + Radix UI | 낮음 | 사용 Radix 패키지 모두 React 19 호환 |
| `AnimatePresence` + 중첩 Routes | 중간 | `AnimatedRoutes` 래퍼 패턴으로 해결 (location key 필요) |
| MapView.jsx 800줄 로직 훼손 | 높음 | Phase 5는 CSS 파일과 panel 래퍼만 수정, OL 로직 불변 |

---

## 검증 방법

각 Phase 완료 후:
```bash
# 로컬 실행
cd frontend && npm run dev

# API 연동 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남역 근처 카페 분석"}'

# SSE 스트리밍 테스트
curl -s -N http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "상권 분석해줘"}'
```
- 브라우저에서 `/`, `/user`, `/map`, `/dev/login`, `/dev`, `/dev/logs` 모두 정상 확인
- 다크모드 토글 후 각 페이지 색상 정상 전환 확인

---

## 수정 대상 파일 요약

### 신규 생성
`src/lib/utils.js`, `src/styles/{fonts,theme,animations}.css`,
`src/components/{GradeBadge,MessageBubble,LoadingSpinner,AnimatedBackground,CursorGlow,PageTransition,ScrollReveal,KeyboardShortcuts,ToastProvider,ThemeToggle,EnhancedTooltip}.jsx`,
`src/components/ui/*.jsx` (Radix 프리미티브 15종)

### 주요 수정
`src/App.jsx`, `src/index.css`, `vite.config.js`, `package.json`,
`src/pages/{Home,UserChat,DevChat,DevLogin,LogViewer}.jsx`,
`src/components/{ResponseCard,ChatInput,SignoffPanel,ProgressPanel}.jsx`,
`src/components/map/{MapView.css,ChatPanel.css}`,
`src/components/map/panel/{Layerpanel,DongPanel,CategoryPanel}.jsx`,
`src/components/map/controls/MapControls.jsx`,
`src/components/LogTable.jsx`

### 삭제
`tailwind.config.js`, `postcss.config.js`

---

## 부록 — `package.json` 및 `README.md` 업데이트

### package.json (frontend/package.json)
Phase 1 완료 후 `dependencies`/`devDependencies` 변경 사항을 반영:

**추가 devDependencies:**
```json
"@tailwindcss/vite": "^4.1.12",
"tailwindcss": "^4.1.12"
```

**추가 dependencies:**
```json
"motion": "^12.23.24",
"lucide-react": "^0.487.0",
"sonner": "^2.0.3",
"clsx": "^2.1.1",
"tailwind-merge": "^3.2.0",
"class-variance-authority": "^0.7.1",
"tw-animate-css": "^1.3.8",
"@radix-ui/react-slot": "^1.1.2",
"@radix-ui/react-separator": "^1.1.2",
"@radix-ui/react-tooltip": "^1.1.8",
"@radix-ui/react-tabs": "^1.1.3",
"@radix-ui/react-collapsible": "^1.1.3",
"@radix-ui/react-label": "^2.1.2",
"@radix-ui/react-switch": "^1.1.3",
"@radix-ui/react-select": "^2.1.6"
```

**제거:**
- `"autoprefixer"` (devDependencies) — Tailwind v4에서 불필요

> `npm install` 후 `package-lock.json` 자동 갱신됨.

---

### README.md (frontend/README.md 또는 루트 README)

기존 README에 아래 내용을 추가/갱신:

**프론트엔드 기술 스택 섹션 업데이트:**

```markdown
## 프론트엔드 기술 스택

| 항목 | 패키지 | 버전 |
|------|--------|------|
| 빌드 | Vite + @tailwindcss/vite | 7.x / 4.x |
| 스타일 | Tailwind CSS v4 | ^4.1 |
| 애니메이션 | motion (Framer Motion v12) | ^12.x |
| UI 프리미티브 | Radix UI | 다수 |
| 아이콘 | lucide-react | ^0.487 |
| 토스트 | sonner | ^2.x |
| 지도 | OpenLayers | ^10.x |

## 디자인 시스템

NeoFrontend_Mar30 기반으로 마이그레이션된 디자인 시스템:

- `src/styles/theme.css` — CSS 변수 (라이트/다크 모드, 브랜드 색상, glow 효과)
- `src/styles/animations.css` — 커스텀 keyframe (blob, shimmer, slideUp 등)
- `src/styles/fonts.css` — Pretendard CDN 폰트
- `src/components/ui/` — Radix UI 기반 프리미티브 컴포넌트 (15종)
- `src/lib/utils.js` — `cn()` 유틸리티 (`clsx` + `tailwind-merge`)

## 다크 모드

헤더 우측 상단의 ThemeToggle 버튼으로 전환.
설정은 `localStorage`에 저장됨.
```

**환경변수 섹션에 추가 항목 없음** (기존 `VITE_*` 변수 그대로 유지).

> README 파일이 존재하지 않을 경우 `frontend/README.md`로 신규 생성.
