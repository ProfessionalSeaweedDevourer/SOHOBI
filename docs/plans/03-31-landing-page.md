# Landing 페이지 이식 계획

**작성일:** 2026-03-31
**브랜치:** PARK
**참조:** `NeoFrontend_Mar30/src/app/pages/Landing.tsx`
**대상:** `frontend/` (React + Vite + JSX)

---

## 목표

`NeoFrontend_Mar30`의 `Landing.tsx`를 `frontend/`에 이식하여 `/` 라우트의 진입점으로 설정한다.
기존 `Home.jsx` (모드 선택 카드)는 `/home` 경로로 이동하여 Landing → Home 흐름을 구성한다.

---

## 현황 분석

### 현재 frontend 라우트 구조

| 경로 | 컴포넌트 | 역할 |
|------|----------|------|
| `/` | `Home.jsx` | 모드 선택 (사용자/지도/개발자) |
| `/user` | `UserChat.jsx` | 일반 사용자 채팅 |
| `/map` | `MapPage.jsx` | 지도 + 채팅 |
| `/dev/login` | `DevLogin.jsx` | 개발자 로그인 |
| `/dev` | `DevChat.jsx` | 개발자 채팅 (인증 필요) |
| `/dev/logs` | `LogViewer.jsx` | 로그 뷰어 (인증 필요) |

### Landing.tsx의 라우트 참조 → frontend 매핑

| NeoFrontend 참조 | frontend 대응 경로 | 설명 |
|-----------------|-------------------|------|
| `/chat` | `/user` | 일반 사용자 채팅 |
| `/logs` | `/dev/logs` | 로그 뷰어 |

### 컴포넌트 의존성 분석

| 의존성 | NeoFrontend 경로 | frontend 상태 |
|--------|-----------------|---------------|
| `Button` (ui) | `components/ui/button.tsx` | ✅ 존재 (`components/ui/button.jsx`) |
| `AnimatedBackground` | `components/AnimatedBackground.tsx` | ✅ 존재 (`components/AnimatedBackground.jsx`) |
| `ThemeToggle` | `components/ThemeToggle.tsx` | ✅ 존재 (`components/ThemeToggle.jsx`) |
| `ScrollReveal` | `components/ScrollReveal.tsx` | ✅ 존재 (`components/ScrollReveal.jsx`) |
| `AgentCard` | `components/AgentCard.tsx` | ❌ **없음 — 신규 생성 필요** |
| `agentData` | `data/mockData.ts` | ❌ **없음 — 신규 생성 필요** |
| `Link` | `react-router` | ⚠️ frontend는 `react-router-dom` 사용 → 동일 API, import만 변경 |

---

## 구현 단계

### Step 1 — agentData 상수 파일 생성

**파일:** `frontend/src/data/mockData.js`

NeoFrontend의 `mockData.ts`에서 `agentData` 배열만 추출해 JS로 변환한다.

```js
// frontend/src/data/mockData.js
export const agentData = [
  {
    id: 'admin',
    nameKo: '행정/법률 에이전트',
    descriptionKo: '사업자등록, 인허가, 정부지원금, 법률 상담',
    icon: 'FileText',
    color: '#0891b2',
    plugins: [ /* NeoFrontend mockData 동일 */ ]
  },
  // commercial, finance 동일
];
```

---

### Step 2 — AgentCard 컴포넌트 생성

**파일:** `frontend/src/components/AgentCard.jsx`

NeoFrontend의 `AgentCard.tsx`를 JSX로 변환한다. 변경 사항:
- TypeScript 타입 제거 (`AgentInfo`, `AgentCardProps`, `LucideIcon` 타입 annotation)
- `useNavigate` 경로: `/chat` → `/user`
- import: `react-router` → `react-router-dom`

```jsx
// 핵심 로직 (NeoFrontend 동일)
const handleClick = () => {
  toast.success(`${agent.nameKo}와 상담을 시작합니다`);
  navigate('/user', { state: { selectedAgent: agent.id } });  // /chat → /user
};
```

---

### Step 3 — Landing 페이지 생성

**파일:** `frontend/src/pages/Landing.jsx`

NeoFrontend의 `Landing.tsx`를 JSX로 변환한다. 변경 사항:

| 항목 | NeoFrontend | frontend |
|------|------------|----------|
| 파일 확장자 | `.tsx` | `.jsx` |
| import (router) | `react-router` | `react-router-dom` |
| 채팅 링크 | `<Link to="/chat">` | `<Link to="/user">` |
| 로그 링크 | `<Link to="/logs">` | `<Link to="/dev/logs">` |
| AgentCard import | `../components/AgentCard` | `../components/AgentCard` (동일) |
| agentData import | `../data/mockData` | `../data/mockData` (동일) |
| TypeScript 제거 | 있음 | 없음 |

---

### Step 4 — 기존 Home.jsx를 `/home`으로 이동

기존 Home.jsx는 **삭제하지 않는다.** 모드 선택 페이지로서 유용하며, Landing에서 진입한 뒤 돌아볼 수 있는 경로로 유지한다.

App.jsx에서 경로만 `/` → `/home`으로 변경한다.

---

### Step 5 — App.jsx 라우터 업데이트

```jsx
// frontend/src/App.jsx 변경 사항
import Landing from "./pages/Landing";   // 추가

// Routes 변경:
// Before: <Route path="/" element={<Home />} />
// After:
<Route path="/" element={<Landing />} />
<Route path="/home" element={<Home />} />   // 기존 Home 경로 이동
```

---

## 최종 라우트 구조 (변경 후)

| 경로 | 컴포넌트 | 역할 |
|------|----------|------|
| `/` | `Landing.jsx` | **신규** — 랜딩 페이지 (진입점) |
| `/home` | `Home.jsx` | 모드 선택 카드 (기존 `/`에서 이동) |
| `/user` | `UserChat.jsx` | 일반 사용자 채팅 |
| `/map` | `MapPage.jsx` | 지도 + 채팅 |
| `/dev/login` | `DevLogin.jsx` | 개발자 로그인 |
| `/dev` | `DevChat.jsx` | 개발자 채팅 (인증 필요) |
| `/dev/logs` | `LogViewer.jsx` | 로그 뷰어 (인증 필요) |

---

## 사용자 흐름 (변경 후)

```
/ (Landing)
  ├─ "무료로 상담 시작하기" → /user (UserChat)
  ├─ "데모 로그 보기"      → /dev/logs (LogViewer)
  ├─ AgentCard 클릭        → /user (UserChat, selectedAgent state 전달)
  └─ (헤더) "지금 시작하기" → /user (UserChat)
```

---

## 주의 사항

- `AgentCard`의 `navigate('/user', { state: { selectedAgent: agent.id } })`로 전달되는 state는 현재 `UserChat.jsx`에서 미사용. 추후 에이전트 자동 선택 기능 추가 시 활용 가능.
- `sonner` (`toast`) 이미 frontend에 설치되어 있음 (ToastProvider.jsx 존재).
- `lucide-react` 이미 frontend에서 사용 중.
- Landing의 `CheckCircle2` 아이콘은 사용되지 않으므로 import에서 제거 가능.
