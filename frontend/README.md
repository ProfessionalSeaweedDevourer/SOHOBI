# SOHOBI 프론트엔드

SOHOBI 통합 에이전트(`backend/`)와 연동하는 React 기반 웹 UI입니다.

---

## 기술 스택

| 항목 | 패키지 | 버전 |
| ---- | ------ | ---- |
| 빌드 | Vite + @tailwindcss/vite | 7.x / 4.x |
| 스타일 | Tailwind CSS v4 | ^4.1 |
| 애니메이션 | motion (Framer Motion v12) | ^12.x |
| UI 프리미티브 | Radix UI | 다수 |
| 아이콘 | lucide-react | ^0.487 |
| 토스트 | sonner | ^2.x |
| 지도 | OpenLayers | ^10.x |
| React Router | react-router-dom | v6 |
| 마크다운 | react-markdown | - |

---

## 디자인 시스템

NeoFrontend_Mar30 기반으로 마이그레이션된 디자인 시스템:

- `src/styles/theme.css` — CSS 변수 (라이트/다크 모드, 브랜드 색상, glow 효과)
- `src/styles/animations.css` — 커스텀 keyframe (blob, shimmer, slideUp 등)
- `src/styles/fonts.css` — Pretendard CDN 폰트
- `src/components/ui/` — Radix UI 기반 프리미티브 컴포넌트
- `src/lib/utils.js` — `cn()` 유틸리티 (`clsx` + `tailwind-merge`)

---

## 다크 모드

각 페이지 헤더 우측의 ThemeToggle 버튼으로 전환합니다.
설정은 `localStorage`에 저장되며, 시스템 설정도 자동으로 감지합니다.

---

## 페이지 구성

| 경로 | 컴포넌트 | 설명 |
| ---- | -------- | ---- |
| `/` | `Landing.jsx` | 랜딩 페이지 — 서비스 소개 및 CTA |
| `/home` | `Home.jsx` | 모드 선택 — 사용자 / 지도 / 개발자 |
| `/user` | `UserChat.jsx` | 사용자 모드 — 질문 입력 및 응답 확인 |
| `/map` | `MapPage.jsx` | 지도 모드 — 서울 행정동 상권 탐색 및 AI 채팅 |
| `/features` | `Features.jsx` | 기능 소개 |
| `/changelog` | `Changelog.jsx` | 변경 이력 |
| `/my/logs` | `MyLogs.jsx` | 내 질문 이력 |
| `/my/report` | `MyReport.jsx` | 내 분석 리포트 |
| `/stats` | `StatsPage.jsx` | 서비스 통계 |
| `/roadmap` | `Roadmap.jsx` | 제품 로드맵 |
| `/privacy` | `PrivacyPolicy.jsx` | 개인정보처리방침 |
| `/dev/login` | `DevLogin.jsx` | 개발자 로그인 |
| `/dev` | `DevHub.jsx` | 개발자 모드 — Sign-off 판정 내역 및 루브릭 |
| `/dev/logs` | `LogViewer.jsx` | 로그 뷰어 — 요청/거부 이력 확인 |

---

## 환경변수

`.env` 파일에서 설정하며, 빌드 시 `VITE_` 접두사가 있는 변수만 번들에 포함됩니다.

| 변수 | 설명 |
| ---- | ---- |
| `VITE_API_URL` | 백엔드 API URL (로컬: `http://localhost:8000`) |
| `VITE_DEV_PASSWORD_HASH` | 개발자 모드 비밀번호 해시 |
| `VITE_KAKAO_JS_KEY` | 카카오맵 JavaScript 키 |
| `VITE_KAKAO_API_KEY` | 카카오맵 API 키 |
| `VITE_VWORLD_API_KEY` | V-World 지도 API 키 |
| `VITE_MAP_URL` | 지도 타일 서버 URL |
| `VITE_REALESTATE_URL` | 실거래가 API URL |

---

## 로컬 개발 실행

### 필수 조건

- Node.js 18 이상
- `backend/` 백엔드 서버가 **포트 8000**에서 실행 중이어야 합니다.

### 설치 및 실행

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000 에서 접속
```

개발 서버는 `/api/*` 요청을 자동으로 `http://localhost:8000`으로 프록시합니다.

---

## 프로덕션 빌드

```bash
npm run build
# → dist/ 폴더에 정적 파일 생성
```

---

## Azure Static Web Apps 배포

GitHub Actions (`azure-static-web-apps-*.yml`)가 `main` 브랜치 push 시 자동으로 빌드·배포합니다.
환경변수(`VITE_API_URL` 등)는 워크플로우 파일에서 GitHub Secrets로 주입됩니다.

---

## 폴더 구조

```
frontend/
├── src/
│   ├── api.js                  백엔드 fetch 래퍼
│   ├── App.jsx                 라우터 정의
│   ├── lib/utils.js            cn() 유틸리티
│   ├── assets/                 정적 리소스
│   ├── config/                 SEO 등 설정
│   ├── constants/              카테고리, 체크리스트 상수
│   ├── contexts/               React Context (AuthContext)
│   ├── data/                   목업 데이터
│   ├── styles/                 테마·폰트·애니메이션 CSS
│   ├── utils/                  인증, 에러 해석, 이벤트 추적
│   ├── hooks/
│   │   ├── chat/               채팅 훅 (useChatMessages, useStreamQuery)
│   │   └── map/                지도 훅 (useDongLayer, useMap 등)
│   ├── pages/                  페이지 컴포넌트 (15개)
│   └── components/
│       ├── ui/                 Radix UI 프리미티브 컴포넌트
│       ├── map/                OpenLayers 지도 (MapView, ChatPanel, controls, panel, popup)
│       ├── checklist/          창업 체크리스트 컴포넌트
│       ├── feedback/           인라인 피드백 컴포넌트
│       ├── report/             분석 리포트 컴포넌트
│       ├── ChatInput.jsx       입력창
│       ├── ResponseCard.jsx    응답 카드 (마크다운)
│       ├── SimulationChart.jsx 재무 시뮬레이션 차트
│       ├── GradeBadge.jsx      A/B/C 등급 배지
│       ├── ThemeToggle.jsx     라이트/다크 모드 토글
│       └── AnimatedBackground.jsx  배경 애니메이션
├── public/                     정적 파일 (OG 이미지, manifest, sitemap 등)
├── vite.config.js
└── package.json
```
