# SOHOBI 프론트엔드

SOHOBI 통합 에이전트(`integrated_PARK/`)와 연동하는 React 기반 웹 UI입니다.

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

| 경로 | 설명 |
| ---- | ---- |
| `/` | 홈 — 사용자 / 지도 / 개발자 모드 선택 |
| `/user` | 사용자 모드 — 질문 입력 및 응답 확인 |
| `/map` | 지도 모드 — 서울 행정동 상권 탐색 및 AI 채팅 |
| `/dev/login` | 개발자 로그인 |
| `/dev` | 개발자 모드 — Sign-off 판정 내역 및 루브릭 포함 |
| `/dev/logs` | 로그 뷰어 — 요청 이력 및 거부 이력 확인 |

---

## 로컬 개발 실행

### 필수 조건

- Node.js 18 이상
- `integrated_PARK/` 백엔드 서버가 **포트 8000**에서 실행 중이어야 합니다.

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

## Vercel 배포

| 항목 | 값 |
| ---- | -- |
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |

환경변수 `VITE_API_URL`에 배포된 백엔드 URL을 설정해야 합니다.

---

## 폴더 구조

```
frontend/
├── src/
│   ├── api.js                  백엔드 fetch 래퍼
│   ├── App.jsx                 라우터 정의
│   ├── lib/utils.js            cn() 유틸리티
│   ├── styles/                 테마·폰트·애니메이션 CSS
│   ├── pages/
│   │   ├── Home.jsx            모드 선택 랜딩
│   │   ├── UserChat.jsx        사용자 채팅
│   │   ├── DevChat.jsx         개발자 채팅 + Sign-off 패널
│   │   ├── DevLogin.jsx        개발자 인증
│   │   ├── LogViewer.jsx       로그 뷰어
│   │   └── MapPage.jsx         지도 모드
│   └── components/
│       ├── ui/                 Radix UI 프리미티브 컴포넌트
│       ├── map/                OpenLayers 지도 컴포넌트
│       ├── ChatInput.jsx       입력창
│       ├── ResponseCard.jsx    응답 카드 (마크다운)
│       ├── SignoffPanel.jsx    루브릭 Sign-off 패널
│       ├── LogTable.jsx        로그 목록 및 상세 패널
│       ├── GradeBadge.jsx      A/B/C 등급 배지
│       ├── ThemeToggle.jsx     라이트/다크 모드 토글
│       └── AnimatedBackground.jsx  배경 애니메이션
├── vite.config.js
└── package.json
```
